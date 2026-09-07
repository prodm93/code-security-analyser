import hashlib
import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "install_scanners.py"
SPEC = importlib.util.spec_from_file_location("install_scanners", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
install_scanners = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(install_scanners)


class ScannerInstallerTests(unittest.TestCase):
    def test_download_accepts_only_the_expected_checksum(self) -> None:
        content = b"scanner binary"
        expected = hashlib.sha256(content).hexdigest()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source"
            destination = root / "destination"
            source.write_bytes(content)

            install_scanners.download(source.as_uri(), destination, expected)

            self.assertEqual(content, destination.read_bytes())

    def test_download_removes_a_checksum_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source"
            destination = root / "destination"
            source.write_bytes(b"unexpected")

            with self.assertRaisesRegex(ValueError, "Checksum verification failed"):
                install_scanners.download(source.as_uri(), destination, "0" * 64)

            self.assertFalse(destination.exists())
            self.assertEqual([source], list(root.iterdir()))

    def test_extracts_only_the_trivy_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive_path = root / "trivy.tar.gz"
            destination = root / "trivy"
            with tarfile.open(archive_path, mode="w:gz") as archive:
                content = b"trivy binary"
                member = tarfile.TarInfo("trivy")
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))

            install_scanners._extract_trivy(archive_path, destination)

            self.assertEqual(content, destination.read_bytes())
            self.assertEqual(0o555, destination.stat().st_mode & 0o777)


if __name__ == "__main__":
    unittest.main()
