import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pystac import Asset, Item
from pystac.extensions.file import ByteOrder, FileExtension

from stactask.task import Task


# Helper functions
def create_test_item(item_id: str = "test-item") -> Item:
    """Create a test STAC Item with required fields."""
    return Item(
        id=item_id,
        geometry={"type": "Point", "coordinates": [0, 0]},
        bbox=[0, 0, 0, 0],
        datetime=datetime.now(timezone.utc),
        properties={},
    )


class SimpleTestTask(Task):
    """Test task implementation for testing purposes."""

    name = "test-task"

    def process(self, **kwargs: Any) -> list[dict[str, Any]]:
        return []


# Fixtures
@pytest.fixture
def test_file_1() -> Path:
    """Path to test fixture file 1."""
    return Path(__file__).parent / "fixtures" / "fileinfo" / "test_file_1.txt"


@pytest.fixture
def test_file_2() -> Path:
    """Path to test fixture file 2."""
    return Path(__file__).parent / "fixtures" / "fileinfo" / "test_file_2.txt"


@pytest.fixture
def simple_task() -> SimpleTestTask:
    """Create a simple test task instance."""
    payload = {
        "type": "FeatureCollection",
        "features": [],
        "process": [
            {
                "upload_options": {
                    "path_template": "s3://test-bucket/${collection}/${year}/${month}/${day}",
                },
                "collection_matchers": [
                    {
                        "type": "catch_all",
                        "collection_name": "test-collection",
                    },
                ],
            },
        ],
    }

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=".*upload_options.collections.*",
            category=DeprecationWarning,
        )
        return SimpleTestTask(payload)


@pytest.mark.parametrize(
    ("href", "expected"),
    [
        ("/usr/bin/python", True),
        ("C:\\Users\\Data", True),
        ("file:///home/user/item.json", True),
        ("data/relative/path.tif", True),
        ("s3://my-bucket/asset.tif", False),
        ("http://example.com/item.json", False),
    ],
)
def test__is_local_href(
    href: str,
    expected: bool,
    simple_task: SimpleTestTask,
) -> None:
    """Test local href detection."""
    assert simple_task._is_local_href(href) == expected


# Tests for compute_multihash
class TestComputeMultihash:
    """Tests for the compute_multihash static method."""

    def test_compute_multihash_sha2_256_default(self, test_file_1: Path) -> None:
        """Test computing sha2-256 hash with default algorithm."""
        result = Task.compute_multihash(test_file_1)

        # Verify it's a hex string
        assert isinstance(result, str)
        assert len(result) > 0
        # Multihash format should be valid hex
        int(result, 16)
        # Should start with 1220 for sha2-256 (0x12 = 18, 0x20 = 32 bytes)
        assert result.startswith("1220")

    def test_compute_multihash_sha2_512(self, test_file_1: Path) -> None:
        """Test computing sha2-512 hash."""
        result = Task.compute_multihash(test_file_1, algorithm="sha2-512")

        assert isinstance(result, str)
        assert len(result) > 0
        # SHA-512 should produce a longer hash than SHA-256
        result_256 = Task.compute_multihash(test_file_1, algorithm="sha2-256")
        assert len(result) > len(result_256)
        # Should start with 1340 for sha2-512 (0x13 = 19, 0x40 = 64 bytes)
        assert result.startswith("1340")

    def test_compute_multihash_consistent(self, test_file_1: Path) -> None:
        """Test that computing hash twice produces same result."""
        hash1 = Task.compute_multihash(test_file_1)
        hash2 = Task.compute_multihash(test_file_1)

        assert hash1 == hash2

    def test_compute_multihash_different_files(
        self,
        test_file_1: Path,
        test_file_2: Path,
    ) -> None:
        """Test that different files produce different hashes."""
        hash1 = Task.compute_multihash(test_file_1)
        hash2 = Task.compute_multihash(test_file_2)

        assert hash1 != hash2

    def test_compute_multihash_invalid_algorithm(self, test_file_1: Path) -> None:
        """Test that invalid algorithm raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported hash function"):
            Task.compute_multihash(test_file_1, algorithm="invalid-algo")

    def test_compute_multihash_nonexistent_file(self) -> None:
        """Test that nonexistent file raises appropriate error."""
        nonexistent = Path("/nonexistent/file.txt")
        with pytest.raises(FileNotFoundError):
            Task.compute_multihash(nonexistent)

    def test_add_fileinfo_raises_multihasherror_on_compute_failure(
        self,
        simple_task: SimpleTestTask,
        test_file_1: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Raise MultihashError if compute_multihash fails."""

        item = create_test_item()
        asset = Asset(href=str(test_file_1))
        item.add_asset("test", asset)

        # patch compute_multihash to error out
        def _raise(path: Path, algorithm: str = "sha2-256") -> str:
            raise RuntimeError("boom")

        monkeypatch.setattr(Task, "compute_multihash", staticmethod(_raise))

        from multihash import MultihashError  # type: ignore[import-untyped]

        with pytest.raises(MultihashError):
            simple_task.add_fileinfo_to_local_asset(asset, autofill=True)


# Tests for add_fileinfo_to_local_asset
class TestAddFileinfoToLocalAsset:
    """Tests for the add_fileinfo_to_local_asset method."""

    def test_manual_values_applied(
        self,
        simple_task: SimpleTestTask,
        test_file_1: Path,
    ) -> None:
        """Test that manual values are applied correctly."""
        item = create_test_item()
        asset = Asset(href=str(test_file_1))
        item.add_asset("test", asset)

        manual_checksum = "1220abcd1234"
        manual_size = 9999
        manual_header_size = 128
        manual_byte_order = ByteOrder.BIG_ENDIAN
        manual_local_path = "/custom/path"

        simple_task.add_fileinfo_to_local_asset(
            asset,
            checksum=manual_checksum,
            size=manual_size,
            header_size=manual_header_size,
            byte_order=manual_byte_order,
            local_path=manual_local_path,
            autofill=False,
        )

        fext = FileExtension.ext(asset)
        assert fext.checksum == manual_checksum
        assert fext.size == manual_size
        assert fext.header_size == manual_header_size
        assert fext.byte_order == manual_byte_order
        assert fext.local_path == manual_local_path

    def test_autofill_computes_size_and_checksum(
        self,
        simple_task: SimpleTestTask,
        test_file_1: Path,
    ) -> None:
        """Test that autofill computes size and checksum for local files."""
        item = create_test_item()
        asset = Asset(href=str(test_file_1))
        item.add_asset("test", asset)

        simple_task.add_fileinfo_to_local_asset(asset, autofill=True)

        fext = FileExtension.ext(asset)
        # Check size matches actual file
        assert fext.size == test_file_1.stat().st_size
        # Check checksum is set and non-empty
        assert fext.checksum is not None
        assert len(fext.checksum) > 0

    def test_manual_values_precedence_over_autofill(
        self,
        simple_task: SimpleTestTask,
        test_file_1: Path,
    ) -> None:
        """Test that manual values take precedence over autofill."""
        item = create_test_item()
        asset = Asset(href=str(test_file_1))
        item.add_asset("test", asset)

        manual_checksum = "1220manual"
        manual_size = 42

        simple_task.add_fileinfo_to_local_asset(
            asset,
            checksum=manual_checksum,
            size=manual_size,
            autofill=True,  # autofill should not override manual values
        )

        fext = FileExtension.ext(asset)
        assert fext.checksum == manual_checksum
        assert fext.size == manual_size

    def test_autofill_false_does_not_compute(
        self,
        simple_task: SimpleTestTask,
        test_file_1: Path,
    ) -> None:
        """Test that autofill=False doesn't compute anything."""
        item = create_test_item()
        asset = Asset(href=str(test_file_1))
        item.add_asset("test", asset)

        simple_task.add_fileinfo_to_local_asset(asset, autofill=False)

        fext = FileExtension.ext(asset)
        assert fext.size is None
        assert fext.checksum is None

    def test_non_local_href_with_autofill(self, simple_task: SimpleTestTask) -> None:
        """Test that non-local href doesn't trigger autofill."""
        item = create_test_item()
        asset = Asset(href="s3://bucket/file.tif")
        item.add_asset("test", asset)

        simple_task.add_fileinfo_to_local_asset(asset, autofill=True)

        fext = FileExtension.ext(asset)
        # Should not compute anything for non-local href
        assert fext.size is None
        assert fext.checksum is None

    def test_custom_hash_algorithm(
        self,
        simple_task: SimpleTestTask,
        test_file_1: Path,
    ) -> None:
        """Test using custom hash algorithm."""
        item = create_test_item()
        asset = Asset(href=str(test_file_1))
        item.add_asset("test", asset)

        simple_task.add_fileinfo_to_local_asset(
            asset,
            autofill=True,
            hash_algorithm="sha2-512",
        )

        fext = FileExtension.ext(asset)
        # Checksum should be set
        assert fext.checksum is not None
        # SHA-512 produces longer hash than SHA-256
        assert len(fext.checksum) > 70  # sha2-512 multihash is longer

    def test_autofill_preserves_existing_values(
        self,
        simple_task: SimpleTestTask,
        test_file_1: Path,
    ) -> None:
        """Test that autofill doesn't override existing size/checksum."""
        item = create_test_item()
        asset = Asset(href=str(test_file_1))
        item.add_asset("test", asset)

        # Pre-set size and checksum
        fext = FileExtension.ext(asset, add_if_missing=True)
        existing_size = 12345
        existing_checksum = "existing_hash"
        fext.size = existing_size
        fext.checksum = existing_checksum

        # Autofill should not override
        simple_task.add_fileinfo_to_local_asset(asset, autofill=True)

        assert fext.size == existing_size
        assert fext.checksum == existing_checksum


# Tests for add_fileinfo_to_local_assets
class TestAddFileinfoToLocalAssets:
    """Tests for the add_fileinfo_to_local_assets method."""

    def test_updates_all_local_assets(
        self,
        simple_task: SimpleTestTask,
        test_file_1: Path,
        test_file_2: Path,
    ) -> None:
        """Test that all local assets are updated."""
        item = create_test_item()
        item.add_asset("local1", Asset(href=str(test_file_1)))
        item.add_asset("local2", Asset(href=str(test_file_2)))

        simple_task.add_fileinfo_to_local_assets(item)

        # Both assets should have size and checksum
        fext1 = FileExtension.ext(item.assets["local1"])
        assert fext1.size == test_file_1.stat().st_size
        assert fext1.checksum is not None

        fext2 = FileExtension.ext(item.assets["local2"])
        assert fext2.size == test_file_2.stat().st_size
        assert fext2.checksum is not None

        # Different files should have different checksums
        assert fext1.checksum != fext2.checksum

    def test_skips_non_local_assets(
        self,
        simple_task: SimpleTestTask,
        test_file_1: Path,
    ) -> None:
        """Test that non-local assets are skipped."""
        item = create_test_item()
        item.add_asset("local", Asset(href=str(test_file_1)))
        item.add_asset("remote_s3", Asset(href="s3://bucket/file.tif"))
        item.add_asset("remote_http", Asset(href="http://example.com/file.tif"))

        simple_task.add_fileinfo_to_local_assets(item)

        # Local asset should be updated
        fext_local = FileExtension.ext(item.assets["local"])
        assert fext_local.size is not None
        assert fext_local.checksum is not None

        # Remote assets should not be updated
        fext_s3 = FileExtension.ext(item.assets["remote_s3"])
        assert fext_s3.size is None
        assert fext_s3.checksum is None

        fext_http = FileExtension.ext(item.assets["remote_http"])
        assert fext_http.size is None
        assert fext_http.checksum is None

    def test_custom_hash_algorithm(
        self,
        simple_task: SimpleTestTask,
        test_file_1: Path,
    ) -> None:
        """Test using custom hash algorithm for all assets."""
        item = create_test_item()
        item.add_asset("local", Asset(href=str(test_file_1)))

        simple_task.add_fileinfo_to_local_assets(item, hash_algorithm="sha2-512")

        fext = FileExtension.ext(item.assets["local"])
        assert fext.checksum is not None
        # Verify it's longer than sha2-256 would be
        assert len(fext.checksum) > 70  # SHA-512 multihash is longer

    def test_empty_item_no_errors(self, simple_task: SimpleTestTask) -> None:
        """Test that empty item (no assets) doesn't cause errors."""
        item = create_test_item()

        # Should not raise any errors
        simple_task.add_fileinfo_to_local_assets(item)

    def test_mixed_existing_and_new_metadata(
        self,
        simple_task: SimpleTestTask,
        test_file_1: Path,
        test_file_2: Path,
    ) -> None:
        """Test handling assets with some existing metadata."""
        item = create_test_item()

        # Asset with no existing metadata
        asset1 = Asset(href=str(test_file_1))
        item.add_asset("new", asset1)

        # Asset with existing size but no checksum
        asset2 = Asset(href=str(test_file_2))
        item.add_asset("partial", asset2)
        fext2 = FileExtension.ext(asset2, add_if_missing=True)
        fext2.size = 999

        simple_task.add_fileinfo_to_local_assets(item)

        # First asset should be fully populated
        fext1 = FileExtension.ext(item.assets["new"])
        assert fext1.size == test_file_1.stat().st_size
        assert fext1.checksum is not None

        # Second asset should keep existing size, add checksum
        fext2 = FileExtension.ext(item.assets["partial"])
        assert fext2.size == 999  # Preserved
        assert fext2.checksum is not None  # Added
