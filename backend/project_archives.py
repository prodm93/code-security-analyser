"""Bounded, path-safe extraction for uploaded project archives."""

import asyncio
import stat
import zipfile
from pathlib import Path, PurePosixPath

from fastapi import UploadFile

from resource_limits import ProjectArchiveLimits

_COPY_CHUNK_BYTES = 64 * 1024


class ProjectArchiveRejected(ValueError):
    """Raised when an archive is invalid or unsafe to extract."""


class ProjectUploadTooLarge(ProjectArchiveRejected):
    """Raised when the compressed upload exceeds its configured limit."""


class ProjectExpandedTooLarge(ProjectArchiveRejected):
    """Raised when extracted content exceeds its configured limit."""


async def extract_project_archive(
    upload: UploadFile,
    work_directory: Path,
    limits: ProjectArchiveLimits,
) -> Path:
    """Stream an uploaded ZIP to disk and extract it within configured bounds."""
    archive_path = work_directory / "upload.zip"
    project_path = work_directory / "project"
    try:
        await _save_upload(upload, archive_path, limits.max_upload_bytes)
        await asyncio.to_thread(_extract_archive, archive_path, project_path, limits)
    except ProjectArchiveRejected:
        raise
    except (zipfile.BadZipFile, zipfile.LargeZipFile, NotImplementedError) as exc:
        raise ProjectArchiveRejected("Invalid zip file") from exc
    finally:
        archive_path.unlink(missing_ok=True)
    return project_path


async def _save_upload(upload: UploadFile, destination: Path, maximum: int) -> None:
    written = 0
    with destination.open("xb") as output:
        while chunk := await upload.read(_COPY_CHUNK_BYTES):
            written += len(chunk)
            if written > maximum:
                raise ProjectUploadTooLarge(
                    f"Zip upload exceeds the {maximum}-byte limit"
                )
            output.write(chunk)


def _extract_archive(
    archive_path: Path,
    project_path: Path,
    limits: ProjectArchiveLimits,
) -> None:
    with zipfile.ZipFile(archive_path, "r") as archive:
        members = archive.infolist()
        validated = _validate_members(members, limits)
        project_path.mkdir()

        extracted_bytes = 0
        for member, relative_path in validated:
            destination = project_path.joinpath(*relative_path.parts)
            if member.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue

            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member, "r") as source, destination.open("xb") as output:
                while chunk := source.read(_COPY_CHUNK_BYTES):
                    extracted_bytes += len(chunk)
                    if extracted_bytes > limits.max_extracted_bytes:
                        raise ProjectExpandedTooLarge(
                            "Extracted project exceeds the "
                            f"{limits.max_extracted_bytes}-byte limit"
                        )
                    output.write(chunk)


def _validate_members(
    members: list[zipfile.ZipInfo], limits: ProjectArchiveLimits
) -> list[tuple[zipfile.ZipInfo, PurePosixPath]]:
    if len(members) > limits.max_members:
        raise ProjectArchiveRejected(
            f"Zip archive exceeds the {limits.max_members}-member limit"
        )

    claimed_size = sum(member.file_size for member in members)
    if claimed_size > limits.max_extracted_bytes:
        raise ProjectExpandedTooLarge(
            f"Extracted project exceeds the {limits.max_extracted_bytes}-byte limit"
        )

    validated: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
    seen: set[str] = set()
    file_paths: set[str] = set()
    for member in members:
        relative_path = _safe_member_path(member)
        normalized = "/".join(relative_path.parts).casefold()
        if normalized in seen:
            raise ProjectArchiveRejected("Zip archive contains duplicate paths")
        seen.add(normalized)
        if not member.is_dir():
            file_paths.add(normalized)
        validated.append((member, relative_path))

    if not file_paths:
        raise ProjectArchiveRejected("Zip archive contains no files")

    for path in seen:
        parts = path.split("/")
        prefixes = ("/".join(parts[:index]) for index in range(1, len(parts)))
        if any(prefix in file_paths for prefix in prefixes):
            raise ProjectArchiveRejected("Zip archive contains conflicting paths")

    return validated


def _safe_member_path(member: zipfile.ZipInfo) -> PurePosixPath:
    name = member.filename.replace("\\", "/")
    path = PurePosixPath(name)
    if (
        not path.parts
        or path.is_absolute()
        or ".." in path.parts
        or "\x00" in name
        or path.parts[0].endswith(":")
    ):
        raise ProjectArchiveRejected("Zip archive contains an unsafe path")

    mode = member.external_attr >> 16
    file_type = stat.S_IFMT(mode)
    if member.flag_bits & 0x1:
        raise ProjectArchiveRejected("Encrypted zip archives are not supported")
    if file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
        raise ProjectArchiveRejected("Zip archive contains a special file")
    return path
