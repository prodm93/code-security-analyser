import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from fastapi import UploadFile

from project_archives import (
    ProjectArchiveRejected,
    ProjectExpandedTooLarge,
    ProjectUploadTooLarge,
    extract_project_archive,
)
from resource_limits import ProjectArchiveLimits


def archive_bytes(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


def limits(
    *, upload: int = 1_024, extracted: int = 4_096, members: int = 10
) -> ProjectArchiveLimits:
    return ProjectArchiveLimits(
        max_upload_bytes=upload,
        max_extracted_bytes=extracted,
        max_members=members,
    )


class ProjectArchiveTests(unittest.IsolatedAsyncioTestCase):
    async def test_streams_and_extracts_a_valid_archive(self) -> None:
        upload = UploadFile(
            file=io.BytesIO(archive_bytes({"src/app.py": b"print('ok')"})),
            filename="project.zip",
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = await extract_project_archive(
                upload, Path(temporary_directory), limits()
            )

            self.assertEqual(b"print('ok')", (project / "src/app.py").read_bytes())
            self.assertFalse((Path(temporary_directory) / "upload.zip").exists())

    async def test_rejects_an_invalid_zip(self) -> None:
        upload = UploadFile(file=io.BytesIO(b"not a zip"), filename="project.zip")
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(ProjectArchiveRejected, "Invalid zip file"):
                await extract_project_archive(
                    upload,
                    Path(temporary_directory),
                    limits(),
                )

    async def test_rejects_an_upload_over_the_compressed_size_limit(self) -> None:
        upload = UploadFile(file=io.BytesIO(b"x" * 20), filename="project.zip")
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaises(ProjectUploadTooLarge):
                await extract_project_archive(
                    upload,
                    Path(temporary_directory),
                    limits(upload=10),
                )

    async def test_rejects_an_archive_over_the_extracted_size_limit(self) -> None:
        upload = UploadFile(
            file=io.BytesIO(archive_bytes({"large.py": b"x" * 20})),
            filename="project.zip",
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaises(ProjectExpandedTooLarge):
                await extract_project_archive(
                    upload,
                    Path(temporary_directory),
                    limits(extracted=10),
                )

    async def test_rejects_path_traversal(self) -> None:
        upload = UploadFile(
            file=io.BytesIO(archive_bytes({"../outside.py": b"unsafe"})),
            filename="project.zip",
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with self.assertRaises(ProjectArchiveRejected):
                await extract_project_archive(upload, root, limits())

            self.assertFalse((root.parent / "outside.py").exists())

    async def test_rejects_too_many_archive_members(self) -> None:
        upload = UploadFile(
            file=io.BytesIO(archive_bytes({"a.py": b"a", "b.py": b"b"})),
            filename="project.zip",
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaises(ProjectArchiveRejected):
                await extract_project_archive(
                    upload,
                    Path(temporary_directory),
                    limits(members=1),
                )


if __name__ == "__main__":
    unittest.main()
