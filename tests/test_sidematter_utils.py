"""
Tests for sidematter utilities functions.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from sidematter_format import (
    Sidematter,
    copy_with_sidematter,
    move_with_sidematter,
    remove_with_sidematter,
)


def create_test_file_with_sidematter(base_path: Path) -> None:
    """Helper to create a test file with metadata and assets."""
    # Create main file
    base_path.write_text("# Test Document\n\nThis is a test document.")

    # Create metadata
    sp = Sidematter(base_path)
    sp.meta_json_path.write_text(json.dumps({"title": "Test", "author": "Test User"}))

    # Create assets
    sp.assets_dir.mkdir(exist_ok=True)
    (sp.assets_dir / "image.png").write_text("fake png data")
    (sp.assets_dir / "data.csv").write_text("col1,col2\nval1,val2")


def create_test_file_yaml_meta(base_path: Path) -> None:
    """Helper to create a test file with YAML metadata."""
    base_path.write_text("# Test Document\n\nThis is a test document.")

    sp = Sidematter(base_path)
    sp.meta_yaml_path.write_text("title: Test\nauthor: Test User")


## Copy Tests


def test_copy_regular_file():
    """Test copying a regular file without sidematter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.txt"
        dest = tmpdir / "dest.txt"

        src.write_text("Hello world!")

        copy_with_sidematter(src, dest)

        assert dest.exists()
        assert dest.read_text() == "Hello world!"


def test_copy_with_json_metadata():
    """Test copying a file with JSON metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.md"
        dest = tmpdir / "dest.md"

        create_test_file_with_sidematter(src)

        copy_with_sidematter(src, dest)

        # Check main file
        assert dest.exists()
        assert dest.read_text() == src.read_text()

        # Check metadata
        dest_sp = Sidematter(dest)
        assert dest_sp.meta_json_path.exists()
        assert json.loads(dest_sp.meta_json_path.read_text()) == {
            "title": "Test",
            "author": "Test User",
        }

        # Check assets
        assert dest_sp.assets_dir.exists()
        assert (dest_sp.assets_dir / "image.png").read_text() == "fake png data"
        assert (dest_sp.assets_dir / "data.csv").read_text() == "col1,col2\nval1,val2"


def test_copy_with_yaml_metadata():
    """Test copying a file with YAML metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.md"
        dest = tmpdir / "dest.md"

        create_test_file_yaml_meta(src)

        copy_with_sidematter(src, dest)

        # Check main file
        assert dest.exists()
        assert dest.read_text() == src.read_text()

        # Check metadata
        dest_sp = Sidematter(dest)
        assert dest_sp.meta_yaml_path.exists()
        assert dest_sp.meta_yaml_path.read_text() == "title: Test\nauthor: Test User"


def test_copy_make_parents():
    """Test copying with make_parents=True creates directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.txt"
        dest = tmpdir / "subdir" / "nested" / "dest.txt"

        src.write_text("Test content")

        copy_with_sidematter(src, dest, make_parents=True)

        assert dest.exists()
        assert dest.read_text() == "Test content"


def test_copy_make_parents_false():
    """Test copying with make_parents=False fails if parent doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.txt"
        dest = tmpdir / "nonexistent" / "dest.txt"

        src.write_text("Test content")

        with pytest.raises(FileNotFoundError):
            copy_with_sidematter(src, dest, make_parents=False)


## Move Tests


def test_move_regular_file():
    """Test moving a regular file without sidematter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.txt"
        dest = tmpdir / "dest.txt"

        src.write_text("Hello world!")

        move_with_sidematter(src, dest)

        assert not src.exists()
        assert dest.exists()
        assert dest.read_text() == "Hello world!"


def test_move_with_sidematter():
    """Test moving a file with metadata and assets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.md"
        dest = tmpdir / "dest.md"

        create_test_file_with_sidematter(src)

        move_with_sidematter(src, dest)

        # Check source is gone
        src_sp = Sidematter(src)
        assert not src.exists()
        assert not src_sp.meta_json_path.exists()
        assert not src_sp.assets_dir.exists()

        # Check destination exists
        assert dest.exists()
        dest_sp = Sidematter(dest)
        assert dest_sp.meta_json_path.exists()
        assert dest_sp.assets_dir.exists()
        assert (dest_sp.assets_dir / "image.png").exists()


def test_move_make_parents():
    """Test moving with make_parents=True creates directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.txt"
        dest = tmpdir / "subdir" / "dest.txt"

        src.write_text("Test content")

        move_with_sidematter(src, dest, make_parents=True)

        assert not src.exists()
        assert dest.exists()
        assert dest.read_text() == "Test content"


## Remove Tests


def test_remove_regular_file():
    """Test removing a regular file without sidematter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        test_file = tmpdir / "test.txt"

        test_file.write_text("Hello world!")
        assert test_file.exists()

        remove_with_sidematter(test_file)

        assert not test_file.exists()


def test_remove_with_sidematter():
    """Test removing a file with metadata and assets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        test_file = tmpdir / "test.md"

        create_test_file_with_sidematter(test_file)

        sp = Sidematter(test_file)
        assert test_file.exists()
        assert sp.meta_json_path.exists()
        assert sp.assets_dir.exists()

        remove_with_sidematter(test_file)

        assert not test_file.exists()
        assert not sp.meta_json_path.exists()
        assert not sp.assets_dir.exists()


def test_remove_nonexistent_file():
    """Test removing a file that doesn't exist (should not raise error)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        nonexistent = tmpdir / "nonexistent.txt"

        # Should not raise an error
        remove_with_sidematter(nonexistent)


def test_remove_partial_sidematter():
    """Test removing when only some sidematter files exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        test_file = tmpdir / "test.md"

        # Create main file and metadata but no assets
        test_file.write_text("Test content")
        sp = Sidematter(test_file)
        sp.meta_yaml_path.write_text("title: Test")

        assert test_file.exists()
        assert sp.meta_yaml_path.exists()
        assert not sp.assets_dir.exists()

        remove_with_sidematter(test_file)

        assert not test_file.exists()
        assert not sp.meta_yaml_path.exists()


## Edge Cases and Error Handling


def test_copy_string_paths():
    """Test that string paths work correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_str = str(Path(tmpdir) / "source.txt")
        dest_str = str(Path(tmpdir) / "dest.txt")

        Path(src_str).write_text("Test content")

        copy_with_sidematter(src_str, dest_str)

        assert Path(dest_str).exists()
        assert Path(dest_str).read_text() == "Test content"


def test_move_overwrites_existing():
    """Test that move overwrites existing destination files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.txt"
        dest = tmpdir / "dest.txt"

        src.write_text("Source content")
        dest.write_text("Dest content")

        move_with_sidematter(src, dest)

        assert not src.exists()
        assert dest.exists()
        assert dest.read_text() == "Source content"


def test_copy_preserves_original():
    """Test that copy preserves the original file and sidematter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.md"
        dest = tmpdir / "dest.md"

        create_test_file_with_sidematter(src)

        copy_with_sidematter(src, dest)

        # Original should still exist
        src_sp = Sidematter(src)
        assert src.exists()
        assert src_sp.meta_json_path.exists()
        assert src_sp.assets_dir.exists()

        # Copy should also exist
        dest_sp = Sidematter(dest)
        assert dest.exists()
        assert dest_sp.meta_json_path.exists()
        assert dest_sp.assets_dir.exists()


def test_copy_only_assets():
    """Test copying when only assets exist (no metadata)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.md"
        dest = tmpdir / "dest.md"

        # Create main file and assets but no metadata
        src.write_text("Test content")
        src_sp = Sidematter(src)
        src_sp.assets_dir.mkdir()
        (src_sp.assets_dir / "test.png").write_text("fake png")

        copy_with_sidematter(src, dest)

        assert dest.exists()
        dest_sp = Sidematter(dest)
        assert dest_sp.assets_dir.exists()
        assert (dest_sp.assets_dir / "test.png").exists()
        assert not dest_sp.meta_json_path.exists()
        assert not dest_sp.meta_yaml_path.exists()


def test_copy_only_metadata():
    """Test copying when only metadata exists (no assets)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.md"
        dest = tmpdir / "dest.md"

        # Create main file and metadata but no assets
        create_test_file_yaml_meta(src)

        copy_with_sidematter(src, dest)

        assert dest.exists()
        dest_sp = Sidematter(dest)
        assert dest_sp.meta_yaml_path.exists()
        assert not dest_sp.assets_dir.exists()
