from __future__ import annotations

import json
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from sidematter_format import (
    Sidematter,
    SidematterError,
    SidematterPath,
    resolve_sidematter,
)

## Basic Path Property Tests


def test_path_properties():
    """Test path property transformations for various file types."""
    # Standard file with extension
    sp = SidematterPath(Path("report.md"))
    assert sp.meta_json_path == Path("report.meta.json")
    assert sp.meta_yaml_path == Path("report.meta.yml")
    assert sp.assets_dir == Path("report.assets")

    # File without extension
    sp = SidematterPath(Path("README"))
    assert sp.meta_json_path == Path("README.meta.json")
    assert sp.meta_yaml_path == Path("README.meta.yml")
    assert sp.assets_dir == Path("README.assets")

    # File with multiple extensions
    sp = SidematterPath(Path("data.tar.gz"))
    assert sp.meta_json_path == Path("data.tar.meta.json")
    assert sp.meta_yaml_path == Path("data.tar.meta.yml")
    assert sp.assets_dir == Path("data.tar.assets")


## Metadata Resolution Tests


def test_resolve_meta_none_exist():
    """Test metadata resolution when no files exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        assert sp.resolve_meta() is None


def test_resolve_meta_json_precedence():
    """Test that JSON metadata takes precedence over YAML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        sp.meta_json_path.write_text('{"title": "Test"}')
        sp.meta_yaml_path.write_text("title: Test")

        resolved = sp.resolve_meta()
        assert resolved == sp.meta_json_path


def test_resolve_meta_yaml_only():
    """Test metadata resolution when only YAML exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        sp.meta_yaml_path.write_text("title: Test")

        resolved = sp.resolve_meta()
        assert resolved == sp.meta_yaml_path


def test_rename_as():
    """Test Sidematter.rename_as preserves metadata format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / "source.md"
        dest_path = Path(tmpdir) / "dest.md"

        # Create a sidematter with JSON metadata
        src_sm = SidematterPath(src_path)
        src_sm.meta_json_path.write_text('{"test": true}')

        sidematter = resolve_sidematter(src_path)
        renamed = sidematter.rename_as(dest_path)

        dest_sm = SidematterPath(dest_path)
        assert renamed.primary == dest_path
        assert renamed.meta_path == dest_sm.meta_json_path


## Metadata Loading Tests


def test_load_meta_empty():
    """Test loading metadata when no files exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        meta = sp.load_meta()
        assert meta == {}


def test_load_meta_json():
    """Test loading JSON metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        test_data = {"title": "Test", "tags": ["python", "test"]}
        sp.meta_json_path.write_text(json.dumps(test_data))

        meta = sp.load_meta()
        assert meta == test_data


def test_load_meta_yaml():
    """Test loading YAML metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        yaml_content = dedent("""
            title: Test Document
            tags:
              - python
              - test
        """).strip()
        sp.meta_yaml_path.write_text(yaml_content)

        meta = sp.load_meta()
        assert meta["title"] == "Test Document"
        assert meta["tags"] == ["python", "test"]


def test_load_meta_invalid_json():
    """Test error handling for invalid JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        sp.meta_json_path.write_text("{ invalid json")

        with pytest.raises(SidematterError) as exc_info:
            sp.load_meta()

        assert "Error loading metadata" in str(exc_info.value)


def test_load_meta_invalid_yaml():
    """Test error handling for invalid YAML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        # Use actually invalid YAML - unclosed bracket
        sp.meta_yaml_path.write_text("title: Test\ndata: [unclosed")

        with pytest.raises(SidematterError) as exc_info:
            sp.load_meta()

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

        sp = SidematterPath(doc_path)

        # With use_frontmatter=True (default)
        meta = sp.load_meta()
        assert meta["title"] == "Frontmatter Title"
        assert meta["author"] == "John Doe"
        assert meta["tags"] == ["test", "frontmatter"]

        # With use_frontmatter=False
        meta_no_fallback = sp.load_meta(use_frontmatter=False)
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

        sp = SidematterPath(doc_path)

        # Create a sidecar file
        sp.meta_yaml_path.write_text("title: Sidecar Title\nsource: sidecar")

        # Should load from sidecar, not frontmatter
        meta = sp.load_meta()
        assert meta["title"] == "Sidecar Title"
        assert meta["source"] == "sidecar"


def test_load_meta_frontmatter_non_text_file():
    """Test frontmatter fallback gracefully handles non-text files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "image.png"
        # Write some binary data
        doc_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

        sp = SidematterPath(doc_path)

        # Should return empty dict without error
        meta = sp.load_meta()
        assert meta == {}


def test_load_meta_frontmatter_no_frontmatter():
    """Test frontmatter fallback when document has no frontmatter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.write_text("# Just a document\n\nNo frontmatter here.")

        sp = SidematterPath(doc_path)

        # Should return empty dict
        meta = sp.load_meta()
        assert meta == {}


## Metadata Writing Tests


def test_write_meta_dict():
    """Test writing metadata from dict in both formats."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()
        sp = SidematterPath(doc_path)
        test_data = {"title": "Test", "tags": ["python"]}

        # Test YAML format
        written_path = sp.write_meta(test_data, fmt="yaml")
        assert written_path == sp.meta_yaml_path
        assert sp.meta_yaml_path.exists()
        assert sp.load_meta() == test_data

        # Clear metadata
        sp.write_meta(None)

        # Test JSON format
        written_path = sp.write_meta(test_data, fmt="json")
        assert written_path == sp.meta_json_path
        assert sp.meta_json_path.exists()
        assert sp.load_meta() == test_data


def test_write_meta_raw_string():
    """Test writing raw YAML/JSON string."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        raw_yaml = "title: Custom YAML\ntags: [test]\n"

        sp.write_meta(raw_yaml, fmt="yaml")
        content = sp.meta_yaml_path.read_text()
        assert content == raw_yaml


def test_write_meta_none_removes_files():
    """Test that writing None removes metadata files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)

        # Create both files
        sp.meta_json_path.write_text('{"test": true}')
        sp.meta_yaml_path.write_text("test: true")

        assert sp.meta_json_path.exists()
        assert sp.meta_yaml_path.exists()

        # Write None should remove both
        sp.write_meta(None)

        assert not sp.meta_json_path.exists()
        assert not sp.meta_yaml_path.exists()


## Asset Tests


def test_resolve_assets():
    """Test asset directory resolution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        # Directory doesn't exist
        assert sp.resolve_assets() is None

        # Directory exists
        sp.assets_dir.mkdir()
        assert sp.resolve_assets() == sp.assets_dir


def test_copy_asset():
    """Test copying asset files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()
        sp = SidematterPath(doc_path)

        # Create source file
        src_file = Path(tmpdir) / "source.png"
        src_file.write_text("fake image content")

        # Test default name
        copied_path = sp.copy_asset(src_file)
        assert copied_path == sp.assets_dir / "source.png"
        assert copied_path.exists()
        assert copied_path.read_text() == "fake image content"

        # Test custom name
        copied_path2 = sp.copy_asset(src_file, dest_name="renamed.png")
        assert copied_path2 == sp.assets_dir / "renamed.png"
        assert copied_path2.exists()
        assert copied_path2.read_text() == "fake image content"


def test_copy_assets_from():
    """Test copy_assets_from with various scenarios."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()
        sp = SidematterPath(doc_path)

        # Test single file
        src_dir = Path(tmpdir) / "single"
        src_dir.mkdir()
        (src_dir / "file.png").write_text("content")

        copied = sp.copy_assets_from(src_dir)
        assert len(copied) == 1
        assert copied[0].name == "file.png"

        # Test multiple files
        src_dir2 = Path(tmpdir) / "multiple"
        src_dir2.mkdir()
        (src_dir2 / "a.png").write_text("a")
        (src_dir2 / "b.jpg").write_text("b")
        (src_dir2 / "c.txt").write_text("c")

        copied = sp.copy_assets_from(src_dir2)
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

        copied = sp.copy_assets_from(src_dir3)
        assert len(copied) == 3
        assert {p.name for p in copied} == {"root.txt", "nested.png", "file.txt"}

        # Test custom glob pattern
        src_dir4 = Path(tmpdir) / "filtered"
        src_dir4.mkdir()
        (src_dir4 / "keep.png").write_text("keep")
        (src_dir4 / "skip.txt").write_text("skip")

        copied = sp.copy_assets_from(src_dir4, glob="*.png")
        assert len(copied) == 1
        assert copied[0].name == "keep.png"

        # Test empty directory still creates assets dir
        empty_dir = Path(tmpdir) / "empty"
        empty_dir.mkdir()

        copied = sp.copy_assets_from(empty_dir)
        assert len(copied) == 0
        assert sp.assets_dir.exists()

        # Test error on nonexistent source
        with pytest.raises(ValueError, match="is not a directory"):
            sp.copy_assets_from(Path(tmpdir) / "nonexistent")


## Convenience Function Tests


def test_resolve_sidematter():
    """Test resolve_sidematter in various scenarios."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()
        sp = SidematterPath(doc_path)

        # Test empty sidematter
        sidematter = resolve_sidematter(doc_path)
        assert isinstance(sidematter, Sidematter)
        assert sidematter.primary == doc_path
        assert sidematter.meta_path is None
        assert sidematter.meta == {}
        assert sidematter.assets_path is None

        # Test with metadata
        test_data = {"title": "Test Document"}
        sp.write_meta(test_data)
        sidematter = resolve_sidematter(doc_path)
        assert sidematter.meta_path == sp.meta_yaml_path
        assert sidematter.meta == test_data

        # Test with assets
        sp.assets_dir.mkdir()
        (sp.assets_dir / "test.png").touch()
        sidematter = resolve_sidematter(doc_path)
        assert sidematter.assets_path == sp.assets_dir

        # Test with string path
        sidematter = resolve_sidematter(str(doc_path))
        assert sidematter.primary == doc_path


def test_resolve_sidematter_with_frontmatter():
    """Test resolve_sidematter with frontmatter fallback."""
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
        sidematter = resolve_sidematter(doc_path)
        assert sidematter.meta is not None
        assert sidematter.meta["title"] == "Document with Frontmatter"
        assert sidematter.meta["version"] == 1.0
        assert sidematter.meta_path is None  # No sidecar file

        # With use_frontmatter=False
        sidematter_no_fallback = resolve_sidematter(doc_path, use_frontmatter=False)
        assert sidematter_no_fallback.meta == {}


## Integration Tests


def test_full_workflow():
    """Test a complete workflow with metadata and assets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "report.md"
        doc_path.write_text("# My Report\n\nSee ![chart](report.assets/chart.png)")

        sp = SidematterPath(doc_path)

        # Add metadata
        metadata = {"title": "Q3 Report", "author": "Jane Doe", "tags": ["finance", "quarterly"]}
        sp.write_meta(metadata, fmt="yaml")

        # Add asset
        chart_src = Path(tmpdir) / "temp_chart.png"
        chart_src.write_text("fake chart data")
        chart_path = sp.copy_asset(chart_src, "chart.png")

        # Verify everything
        assert sp.meta_yaml_path.exists()
        assert chart_path.exists()
        assert chart_path == sp.assets_dir / "chart.png"

        # Test loading
        loaded_meta = sp.load_meta()
        assert loaded_meta == metadata

        # Test convenience function
        sidematter = resolve_sidematter(doc_path)
        assert sidematter.meta == metadata
        assert sidematter.assets_path == sp.assets_dir
