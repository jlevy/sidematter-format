from __future__ import annotations

import json
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from sidematter_format import (
    ResolvedSidematter,
    Sidematter,
    SidematterError,
)

## Basic Path Property Tests


def test_path_properties():
    """Test path property transformations for various file types."""
    # Standard file with extension
    sm = Sidematter(Path("report.md"))
    assert sm.meta_json_path == Path("report.meta.json")
    assert sm.meta_yaml_path == Path("report.meta.yml")
    assert sm.assets_dir == Path("report.assets")

    # File without extension
    sm = Sidematter(Path("README"))
    assert sm.meta_json_path == Path("README.meta.json")
    assert sm.meta_yaml_path == Path("README.meta.yml")
    assert sm.assets_dir == Path("README.assets")

    # File with multiple extensions
    sm = Sidematter(Path("data.tar.gz"))
    assert sm.meta_json_path == Path("data.tar.meta.json")
    assert sm.meta_yaml_path == Path("data.tar.meta.yml")
    assert sm.assets_dir == Path("data.tar.assets")


## Metadata Resolution Tests


def test_resolve_meta_none_exist():
    """Test metadata resolution when no files exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sm = Sidematter(doc_path)
        assert sm.resolve_meta() is None


def test_resolve_meta_json_precedence():
    """Test that JSON metadata takes precedence over YAML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sm = Sidematter(doc_path)
        sm.meta_json_path.write_text('{"title": "Test"}')
        sm.meta_yaml_path.write_text("title: Test")

        resolved = sm.resolve_meta()
        assert resolved == sm.meta_json_path


def test_resolve_meta_yaml_only():
    """Test metadata resolution when only YAML exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sm = Sidematter(doc_path)
        sm.meta_yaml_path.write_text("title: Test")

        resolved = sm.resolve_meta()
        assert resolved == sm.meta_yaml_path


def test_rename_as():
    """Test Sidematter.rename_as preserves metadata format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / "source.md"
        dest_path = Path(tmpdir) / "dest.md"

        # Create a sidematter with JSON metadata
        src_sm = Sidematter(src_path)
        src_sm.meta_json_path.write_text('{"test": true}')

        sidematter = Sidematter(src_path).resolve()
        renamed = sidematter.renamed_as(dest_path)

        dest_sm = Sidematter(dest_path)
        assert renamed.primary == dest_path
        assert renamed.meta_path == dest_sm.meta_json_path


## Metadata Loading Tests


def test_load_meta_empty():
    """Test loading metadata when no files exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sm = Sidematter(doc_path)
        meta = sm.read_meta()
        assert meta == {}


def test_load_meta_json():
    """Test loading JSON metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sm = Sidematter(doc_path)
        test_data = {"title": "Test", "tags": ["python", "test"]}
        sm.meta_json_path.write_text(json.dumps(test_data))

        meta = sm.read_meta()
        assert meta == test_data


def test_load_meta_yaml():
    """Test loading YAML metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sm = Sidematter(doc_path)
        yaml_content = dedent("""
            title: Test Document
            tags:
              - python
              - test
        """).strip()
        sm.meta_yaml_path.write_text(yaml_content)

        meta = sm.read_meta()
        assert meta["title"] == "Test Document"
        assert meta["tags"] == ["python", "test"]


def test_load_meta_invalid_json():
    """Test error handling for invalid JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sm = Sidematter(doc_path)
        sm.meta_json_path.write_text("{ invalid json")

        with pytest.raises(SidematterError) as exc_info:
            sm.read_meta()

        assert "Error loading metadata" in str(exc_info.value)


def test_load_meta_invalid_yaml():
    """Test error handling for invalid YAML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sm = Sidematter(doc_path)
        # Use actually invalid YAML - unclosed bracket
        sm.meta_yaml_path.write_text("title: Test\ndata: [unclosed")

        with pytest.raises(SidematterError) as exc_info:
            sm.read_meta()

        assert "Error loading metadata" in str(exc_info.value)


def test_load_meta_frontmatter_fallback():
    """Test loading metadata from frontmatter when no sidecar files exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_content = dedent("""
            ---
            title: Frontmatter Title
            author: John Doe
            tags:
              - test
              - frontmatter
            ---
            
            # Document content
            
            This is the main content.
        """).strip()
        doc_path.write_text(doc_content)

        sm = Sidematter(doc_path)

        # With use_frontmatter=True (default)
        meta = sm.read_meta()
        assert meta["title"] == "Frontmatter Title"
        assert meta["author"] == "John Doe"
        assert meta["tags"] == ["test", "frontmatter"]

        # With use_frontmatter=False
        meta_no_fallback = sm.read_meta(use_frontmatter=False)
        assert meta_no_fallback == {}


def test_load_meta_sidecar_precedence_over_frontmatter():
    """Test that sidecar files take precedence over frontmatter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_content = dedent("""
            ---
            title: Frontmatter Title
            source: frontmatter
            ---
            
            # Document content
        """).strip()
        doc_path.write_text(doc_content)

        sm = Sidematter(doc_path)

        # Create a sidecar file
        sm.meta_yaml_path.write_text("title: Sidecar Title\nsource: sidecar")

        # Should load from sidecar, not frontmatter
        meta = sm.read_meta()
        assert meta["title"] == "Sidecar Title"
        assert meta["source"] == "sidecar"


def test_load_meta_frontmatter_non_text_file():
    """Test frontmatter fallback gracefully handles non-text files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "image.png"
        # Write some binary data
        doc_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

        sm = Sidematter(doc_path)

        # Should return empty dict without error
        meta = sm.read_meta()
        assert meta == {}


def test_load_meta_frontmatter_no_frontmatter():
    """Test frontmatter fallback when document has no frontmatter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.write_text("# Just a document\n\nNo frontmatter here.")

        sm = Sidematter(doc_path)

        # Should return empty dict
        meta = sm.read_meta()
        assert meta == {}


## Metadata Writing Tests


def test_write_meta_dict():
    """Test writing metadata from dict in both formats."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()
        sm = Sidematter(doc_path)
        test_data = {"title": "Test", "tags": ["python"]}

        # Test YAML format
        written_path = sm.write_meta(test_data, formats="yaml")
        assert written_path == sm.meta_yaml_path
        assert sm.meta_yaml_path.exists()
        assert sm.read_meta() == test_data

        # Clear metadata
        sm.delete_meta()

        # Test JSON format
        written_path = sm.write_meta(test_data, formats="json")
        assert written_path == sm.meta_json_path
        assert sm.meta_json_path.exists()
        assert sm.read_meta() == test_data


def test_write_meta_raw_string():
    """Test writing raw YAML/JSON string."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sm = Sidematter(doc_path)
        raw_yaml = "title: Custom YAML\ntags: [test]\n"

        sm.write_meta(raw_yaml, formats="yaml")
        content = sm.meta_yaml_path.read_text()
        assert content == raw_yaml


def test_delete_meta_removes_files():
    """Test that delete_meta removes metadata files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sm = Sidematter(doc_path)

        # Create both files
        sm.meta_json_path.write_text('{"test": true}')
        sm.meta_yaml_path.write_text("test: true")

        assert sm.meta_json_path.exists()
        assert sm.meta_yaml_path.exists()

        # delete_meta should remove both
        sm.delete_meta()

        assert not sm.meta_json_path.exists()
        assert not sm.meta_yaml_path.exists()


## Asset Tests


def test_resolve_assets():
    """Test asset directory resolution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sm = Sidematter(doc_path)
        # Directory doesn't exist
        assert sm.resolve_assets() is None

        # Directory exists
        sm.assets_dir.mkdir()
        assert sm.resolve_assets() == sm.assets_dir


def test_copy_asset():
    """Test copying asset files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()
        sm = Sidematter(doc_path)

        # Create source file
        src_file = Path(tmpdir) / "source.png"
        src_file.write_text("fake image content")

        # Test default name
        copied_path = sm.add_asset(src_file)
        assert copied_path == sm.assets_dir / "source.png"
        assert copied_path.exists()
        assert copied_path.read_text() == "fake image content"

        # Test custom name
        copied_path2 = sm.add_asset(src_file, dest_name="renamed.png")
        assert copied_path2 == sm.assets_dir / "renamed.png"
        assert copied_path2.exists()
        assert copied_path2.read_text() == "fake image content"


def test_copy_assets_from():
    """Test copy_assets_from with various scenarios."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()
        sm = Sidematter(doc_path)

        # Test single file
        src_dir = Path(tmpdir) / "single"
        src_dir.mkdir()
        (src_dir / "file.png").write_text("content")

        copied = sm.copy_assets_from(src_dir)
        assert len(copied) == 1
        assert copied[0].name == "file.png"

        # Test multiple files
        src_dir2 = Path(tmpdir) / "multiple"
        src_dir2.mkdir()
        (src_dir2 / "a.png").write_text("a")
        (src_dir2 / "b.jpg").write_text("b")
        (src_dir2 / "c.txt").write_text("c")

        copied = sm.copy_assets_from(src_dir2)
        assert len(copied) == 3
        assert {p.name for p in copied} == {"a.png", "b.jpg", "c.txt"}

        # Test nested directories with default **/* pattern
        src_dir3 = Path(tmpdir) / "nested"
        src_dir3.mkdir()
        (src_dir3 / "root.txt").write_text("root")
        (src_dir3 / "sub").mkdir()
        (src_dir3 / "sub" / "nested.png").write_text("nested")
        (src_dir3 / "sub" / "deep").mkdir()
        (src_dir3 / "sub" / "deep" / "file.txt").write_text("deep")

        copied = sm.copy_assets_from(src_dir3)
        assert len(copied) == 3
        assert {p.name for p in copied} == {"root.txt", "nested.png", "file.txt"}

        # Test custom glob pattern
        src_dir4 = Path(tmpdir) / "filtered"
        src_dir4.mkdir()
        (src_dir4 / "keep.png").write_text("keep")
        (src_dir4 / "skip.txt").write_text("skip")

        copied = sm.copy_assets_from(src_dir4, glob="*.png")
        assert len(copied) == 1
        assert copied[0].name == "keep.png"

        # Test empty directory still creates assets dir
        empty_dir = Path(tmpdir) / "empty"
        empty_dir.mkdir()

        copied = sm.copy_assets_from(empty_dir)
        assert len(copied) == 0
        assert sm.assets_dir.exists()

        # Test error on nonexistent source
        with pytest.raises(ValueError, match="is not a directory"):
            sm.copy_assets_from(Path(tmpdir) / "nonexistent")


## Convenience Function Tests


def test_resolve_sidematter():
    """Test Sidematter(...).resolve() in various scenarios."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()
        sm = Sidematter(doc_path)

        # Test empty sidematter
        sidematter = Sidematter(doc_path).resolve()
        assert isinstance(sidematter, ResolvedSidematter)
        assert sidematter.primary == doc_path
        assert sidematter.meta_path is None
        assert sidematter.meta == {}
        assert sidematter.assets_dir is None

        # Test with metadata
        test_data = {"title": "Test Document"}
        sm.write_meta(test_data)
        sidematter = Sidematter(doc_path).resolve()
        assert sidematter.meta_path == sm.meta_yaml_path
        assert sidematter.meta == test_data

        # Test with assets
        sm.assets_dir.mkdir()
        (sm.assets_dir / "test.png").touch()
        sidematter = Sidematter(doc_path).resolve()
        assert sidematter.assets_dir == sm.assets_dir

        # Test with string path
        sidematter = Sidematter(Path(str(doc_path))).resolve()
        assert sidematter.primary == doc_path


def test_resolve_sidematter_with_frontmatter():
    """Test Sidematter(...).resolve() with frontmatter fallback."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_content = dedent("""
            ---
            title: Document with Frontmatter
            version: 1.0
            ---
            
            # Content here
        """).strip()
        doc_path.write_text(doc_content)

        # With use_frontmatter=True (default)
        sidematter = Sidematter(doc_path).resolve()
        assert sidematter.meta is not None
        assert sidematter.meta["title"] == "Document with Frontmatter"
        assert sidematter.meta["version"] == 1.0
        assert sidematter.meta_path is None  # No sidecar file

        # With use_frontmatter=False
        sidematter_no_fallback = Sidematter(doc_path).resolve(use_frontmatter=False)
        assert sidematter_no_fallback.meta == {}


## Integration Tests


def test_full_workflow():
    """Test a complete workflow with metadata and assets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "report.md"
        doc_path.write_text("# My Report\n\nSee ![chart](report.assets/chart.png)")

        sm = Sidematter(doc_path)

        # Add metadata
        metadata = {"title": "Q3 Report", "author": "Jane Doe", "tags": ["finance", "quarterly"]}
        sm.write_meta(metadata, formats="yaml")

        # Add asset
        chart_src = Path(tmpdir) / "temp_chart.png"
        chart_src.write_text("fake chart data")
        chart_path = sm.add_asset(chart_src, "chart.png")

        # Verify everything
        assert sm.meta_yaml_path.exists()
        assert chart_path.exists()
        assert chart_path == sm.assets_dir / "chart.png"

        # Test loading
        loaded_meta = sm.read_meta()
        assert loaded_meta == metadata

        # Test convenience function
        sidematter = Sidematter(doc_path).resolve()
        assert sidematter.meta == metadata
        assert sidematter.assets_dir == sm.assets_dir
