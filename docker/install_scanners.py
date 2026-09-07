"""Install checksum-verified scanner release artifacts into an image stage."""

import argparse
import hashlib
import hmac
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

_DOWNLOAD_CHUNK_BYTES = 1024 * 1024


def download(url: str, destination: Path, expected_sha256: str) -> None:
    """Stream a release artifact to disk and verify its SHA-256 digest."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "cybersecurity-analyzer-container-build"},
    )
    digest = hashlib.sha256()
    temporary_path: Path | None = None
    try:
        with (
            urllib.request.urlopen(request, timeout=120) as response,
            tempfile.NamedTemporaryFile(
                dir=destination.parent,
                prefix=f".{destination.name}.",
                delete=False,
            ) as output,
        ):
            temporary_path = Path(output.name)
            while chunk := response.read(_DOWNLOAD_CHUNK_BYTES):
                digest.update(chunk)
                output.write(chunk)

        if not hmac.compare_digest(digest.hexdigest(), expected_sha256):
            raise ValueError(f"Checksum verification failed for {destination.name}")
        temporary_path.replace(destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def install_scanners(
    output: Path,
    opengrep_version: str,
    opengrep_sha256: str,
    trivy_version: str,
    trivy_sha256: str,
) -> None:
    output.mkdir(parents=True, exist_ok=True)

    opengrep_path = output / "opengrep"
    download(
        "https://github.com/opengrep/opengrep/releases/download/"
        f"v{opengrep_version}/opengrep_manylinux_x86",
        opengrep_path,
        opengrep_sha256,
    )
    opengrep_path.chmod(0o555)

    archive_path = output / "trivy.tar.gz"
    try:
        download(
            "https://github.com/aquasecurity/trivy/releases/download/"
            f"v{trivy_version}/trivy_{trivy_version}_Linux-64bit.tar.gz",
            archive_path,
            trivy_sha256,
        )
        _extract_trivy(archive_path, output / "trivy")
    finally:
        archive_path.unlink(missing_ok=True)


def _extract_trivy(archive_path: Path, destination: Path) -> None:
    with tarfile.open(archive_path, mode="r:gz") as archive:
        member = archive.getmember("trivy")
        if not member.isfile() or (source := archive.extractfile(member)) is None:
            raise ValueError("Trivy release archive does not contain its executable")
        with source, destination.open("xb") as output:
            shutil.copyfileobj(source, output)
    destination.chmod(0o555)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--opengrep-version", required=True)
    parser.add_argument("--opengrep-sha256", required=True)
    parser.add_argument("--trivy-version", required=True)
    parser.add_argument("--trivy-sha256", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    install_scanners(
        output=args.output,
        opengrep_version=args.opengrep_version,
        opengrep_sha256=args.opengrep_sha256,
        trivy_version=args.trivy_version,
        trivy_sha256=args.trivy_sha256,
    )


if __name__ == "__main__":
    main()
