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
    copy_sidematter,
    move_sidematter,
    remove_sidematter,
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

        result = copy_sidematter(src, dest)

        assert dest.exists()
        assert dest.read_text() == "Hello world!"
        assert result.primary == dest
        assert result.meta_path is None
        assert result.assets_dir is None


def test_copy_with_json_metadata():
    """Test copying a file with JSON metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.md"
        dest = tmpdir / "dest.md"

        create_test_file_with_sidematter(src)

        result = copy_sidematter(src, dest)

        assert dest.exists()
        assert dest.read_text() == src.read_text()

        dest_sp = Sidematter(dest)
        assert dest_sp.meta_json_path.exists()
        assert json.loads(dest_sp.meta_json_path.read_text()) == {
            "title": "Test",
            "author": "Test User",
        }

        assert dest_sp.assets_dir.exists()
        assert (dest_sp.assets_dir / "image.png").read_text() == "fake png data"
        assert (dest_sp.assets_dir / "data.csv").read_text() == "col1,col2\nval1,val2"

        # Check return value
        assert result.primary == dest
        assert result.meta_path == dest_sp.meta_json_path
        assert result.assets_dir == dest_sp.assets_dir


def test_copy_with_yaml_metadata():
    """Test copying a file with YAML metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.md"
        dest = tmpdir / "dest.md"

        create_test_file_yaml_meta(src)

        result = copy_sidematter(src, dest)

        assert dest.exists()
        assert dest.read_text() == src.read_text()

        dest_sp = Sidematter(dest)
        assert dest_sp.meta_yaml_path.exists()
        assert dest_sp.meta_yaml_path.read_text() == "title: Test\nauthor: Test User"

        # Check return value
        assert result.primary == dest
        assert result.meta_path == dest_sp.meta_yaml_path
        assert result.assets_dir is None


def test_copy_make_parents():
    """Test copying with make_parents=True creates directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.txt"
        dest = tmpdir / "subdir" / "nested" / "dest.txt"

        src.write_text("Test content")

        result = copy_sidematter(src, dest, make_parents=True)

        assert dest.exists()
        assert dest.read_text() == "Test content"
        assert result.primary == dest


def test_copy_make_parents_false():
    """Test copying with make_parents=False fails if parent doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.txt"
        dest = tmpdir / "nonexistent" / "dest.txt"

        src.write_text("Test content")

        with pytest.raises(FileNotFoundError):
            copy_sidematter(src, dest, make_parents=False)


## Move Tests


def test_move_regular_file():
    """Test moving a regular file without sidematter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.txt"
        dest = tmpdir / "dest.txt"

        src.write_text("Hello world!")

        result = move_sidematter(src, dest)

        assert not src.exists()
        assert dest.exists()
        assert dest.read_text() == "Hello world!"
        assert result.primary == dest
        assert result.meta_path is None
        assert result.assets_dir is None


def test_move_with_sidematter():
    """Test moving a file with metadata and assets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.md"
        dest = tmpdir / "dest.md"

        create_test_file_with_sidematter(src)

        result = move_sidematter(src, dest)

        src_sp = Sidematter(src)
        assert not src.exists()
        assert not src_sp.meta_json_path.exists()
        assert not src_sp.assets_dir.exists()

        assert dest.exists()
        dest_sp = Sidematter(dest)
        assert dest_sp.meta_json_path.exists()
        assert dest_sp.assets_dir.exists()
        assert (dest_sp.assets_dir / "image.png").exists()

        # Check return value
        assert result.primary == dest
        assert result.meta_path == dest_sp.meta_json_path
        assert result.assets_dir == dest_sp.assets_dir


def test_move_make_parents():
    """Test moving with make_parents=True creates directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.txt"
        dest = tmpdir / "subdir" / "dest.txt"

        src.write_text("Test content")

        result = move_sidematter(src, dest, make_parents=True)

        assert not src.exists()
        assert dest.exists()
        assert dest.read_text() == "Test content"
        assert result.primary == dest


## Remove Tests


def test_remove_regular_file():
    """Test removing a regular file without sidematter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        test_file = tmpdir / "test.txt"

        test_file.write_text("Hello world!")
        assert test_file.exists()

        remove_sidematter(test_file)

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

        remove_sidematter(test_file)

        assert not test_file.exists()
        assert not sp.meta_json_path.exists()
        assert not sp.assets_dir.exists()


def test_remove_nonexistent_file():
    """Test removing a file that doesn't exist (should not raise error)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        nonexistent = tmpdir / "nonexistent.txt"

        remove_sidematter(nonexistent)


def test_remove_partial_sidematter():
    """Test removing when only some sidematter files exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        test_file = tmpdir / "test.md"

        test_file.write_text("Test content")
        sp = Sidematter(test_file)
        sp.meta_yaml_path.write_text("title: Test")

        assert test_file.exists()
        assert sp.meta_yaml_path.exists()
        assert not sp.assets_dir.exists()

        remove_sidematter(test_file)

        assert not test_file.exists()
        assert not sp.meta_yaml_path.exists()


## Test Return Value for File Counting


def test_copy_return_value_file_counting():
    """Test that return value can be used to count files copied."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Test with no sidematter
        src = tmpdir / "doc1.md"
        dest = tmpdir / "copy1.md"
        src.write_text("Content")
        result = copy_sidematter(src, dest)
        # Only primary file
        assert len(result.path_list) == 1

        # Test with metadata only
        src = tmpdir / "doc2.md"
        dest = tmpdir / "copy2.md"
        create_test_file_yaml_meta(src)
        result = copy_sidematter(src, dest)
        # Primary + metadata
        assert len(result.path_list) == 2

        # Test with full sidematter
        src = tmpdir / "doc3.md"
        dest = tmpdir / "copy3.md"
        create_test_file_with_sidematter(src)
        result = copy_sidematter(src, dest)
        # Primary + metadata + assets dir
        assert len(result.path_list) == 3
        assert result.primary in result.path_list
        assert result.meta_path in result.path_list
        assert result.assets_dir in result.path_list


def test_move_return_value_file_counting():
    """Test that return value can be used to count files moved."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Test with full sidematter
        src = tmpdir / "doc.md"
        dest = tmpdir / "moved.md"
        create_test_file_with_sidematter(src)
        result = move_sidematter(src, dest)
        # Primary + metadata + assets dir
        assert len(result.path_list) == 3

        # Test with selective move
        src = tmpdir / "doc2.md"
        dest = tmpdir / "moved2.md"
        create_test_file_with_sidematter(src)
        result = move_sidematter(src, dest, move_metadata=False)
        # Primary + assets dir (no metadata)
        assert len(result.path_list) == 2
        assert result.primary in result.path_list
        assert result.assets_dir in result.path_list
        assert result.meta_path is None


## Edge Cases and Error Handling


def test_copy_string_paths():
    """Test that string paths work correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_str = str(Path(tmpdir) / "source.txt")
        dest_str = str(Path(tmpdir) / "dest.txt")

        Path(src_str).write_text("Test content")

        result = copy_sidematter(src_str, dest_str)

        assert Path(dest_str).exists()
        assert Path(dest_str).read_text() == "Test content"
        assert result.primary == Path(dest_str)


def test_move_overwrites_existing():
    """Test that move overwrites existing destination files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.txt"
        dest = tmpdir / "dest.txt"

        src.write_text("Source content")
        dest.write_text("Dest content")

        result = move_sidematter(src, dest)

        assert not src.exists()
        assert dest.exists()
        assert dest.read_text() == "Source content"
        assert result.primary == dest


def test_copy_preserves_original():
    """Test that copy preserves the original file and sidematter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.md"
        dest = tmpdir / "dest.md"

        create_test_file_with_sidematter(src)

        result = copy_sidematter(src, dest)

        src_sp = Sidematter(src)
        assert src.exists()
        assert src_sp.meta_json_path.exists()
        assert src_sp.assets_dir.exists()

        dest_sp = Sidematter(dest)
        assert dest.exists()
        assert dest_sp.meta_json_path.exists()
        assert dest_sp.assets_dir.exists()

        # Check return value
        assert result.primary == dest
        assert result.meta_path == dest_sp.meta_json_path
        assert result.assets_dir == dest_sp.assets_dir


def test_copy_only_assets():
    """Test copying when only assets exist (no metadata)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.md"
        dest = tmpdir / "dest.md"

        src.write_text("Test content")
        src_sp = Sidematter(src)
        src_sp.assets_dir.mkdir()
        (src_sp.assets_dir / "test.png").write_text("fake png")

        result = copy_sidematter(src, dest)

        assert dest.exists()
        dest_sp = Sidematter(dest)
        assert dest_sp.assets_dir.exists()
        assert (dest_sp.assets_dir / "test.png").exists()
        assert not dest_sp.meta_json_path.exists()
        assert not dest_sp.meta_yaml_path.exists()

        # Check return value
        assert result.primary == dest
        assert result.meta_path is None
        assert result.assets_dir == dest_sp.assets_dir


def test_copy_only_metadata():
    """Test copying when only metadata exists (no assets)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src = tmpdir / "source.md"
        dest = tmpdir / "dest.md"

        create_test_file_yaml_meta(src)

        result = copy_sidematter(src, dest)

        assert dest.exists()
        dest_sp = Sidematter(dest)
        assert dest_sp.meta_yaml_path.exists()
        assert not dest_sp.assets_dir.exists()

        # Check return value
        assert result.primary == dest
        assert result.meta_path == dest_sp.meta_yaml_path
        assert result.assets_dir is None


## Tests for selective copying/moving


def test_copy_selective():
    """Test selective copying of components."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        src = tmpdir / "src1.md"
        dest = tmpdir / "dest1.md"
        create_test_file_with_sidematter(src)
        result = copy_sidematter(src, dest, copy_original=False)
        assert src.exists() and not dest.exists()
        dest_sp = Sidematter(dest)
        assert dest_sp.meta_json_path.exists() and dest_sp.assets_dir.exists()
        # Return value should still indicate what's present at dest
        assert result.primary == dest
        assert result.meta_path == dest_sp.meta_json_path
        assert result.assets_dir == dest_sp.assets_dir

        src = tmpdir / "src2.md"
        dest = tmpdir / "dest2.md"
        create_test_file_with_sidematter(src)
        result = copy_sidematter(src, dest, copy_metadata=False)
        assert dest.exists()
        dest_sp = Sidematter(dest)
        assert dest_sp.assets_dir.exists() and not dest_sp.meta_json_path.exists()
        assert result.primary == dest
        assert result.meta_path is None
        assert result.assets_dir == dest_sp.assets_dir

        src = tmpdir / "src3.md"
        dest = tmpdir / "dest3.md"
        create_test_file_with_sidematter(src)
        result = copy_sidematter(src, dest, copy_assets=False)
        assert dest.exists()
        dest_sp = Sidematter(dest)
        assert dest_sp.meta_json_path.exists() and not dest_sp.assets_dir.exists()
        assert result.primary == dest
        assert result.meta_path == dest_sp.meta_json_path
        assert result.assets_dir is None


def test_move_selective():
    """Test selective moving of components."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        src = tmpdir / "src1.md"
        dest = tmpdir / "dest1.md"
        create_test_file_with_sidematter(src)
        src_sp = Sidematter(src)
        result = move_sidematter(src, dest, move_original=False)
        assert src.exists() and not dest.exists()
        assert not src_sp.meta_json_path.exists() and not src_sp.assets_dir.exists()
        dest_sp = Sidematter(dest)
        assert dest_sp.meta_json_path.exists() and dest_sp.assets_dir.exists()
        # Return value should still indicate what's present at dest
        assert result.primary == dest
        assert result.meta_path == dest_sp.meta_json_path
        assert result.assets_dir == dest_sp.assets_dir

        src = tmpdir / "src2.md"
        dest = tmpdir / "dest2.md"
        create_test_file_with_sidematter(src)
        src_sp = Sidematter(src)
        result = move_sidematter(src, dest, move_metadata=False)
        assert not src.exists() and dest.exists()
        assert src_sp.meta_json_path.exists()
        dest_sp = Sidematter(dest)
        assert dest_sp.assets_dir.exists() and not dest_sp.meta_json_path.exists()
        assert result.primary == dest
        assert result.meta_path is None
        assert result.assets_dir == dest_sp.assets_dir

        src = tmpdir / "src3.md"
        dest = tmpdir / "dest3.md"
        create_test_file_with_sidematter(src)
        src_sp = Sidematter(src)
        result = move_sidematter(src, dest, move_assets=False)
        assert not src.exists() and dest.exists()
        assert src_sp.assets_dir.exists()
        dest_sp = Sidematter(dest)
        assert dest_sp.meta_json_path.exists() and not dest_sp.assets_dir.exists()
        assert result.primary == dest
        assert result.meta_path == dest_sp.meta_json_path
        assert result.assets_dir is None
