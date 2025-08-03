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
    """Test basic path property transformations."""
    sp = SidematterPath(Path("report.md"))

    assert sp.meta_json == Path("report.meta.json")
    assert sp.meta_yaml == Path("report.meta.yml")
    assert sp.assets_dir == Path("report.assets")


def test_path_properties_no_extension():
    """Test path properties for files without extensions."""
    sp = SidematterPath(Path("README"))

    assert sp.meta_json == Path("README.meta.json")
    assert sp.meta_yaml == Path("README.meta.yml")
    assert sp.assets_dir == Path("README.assets")


def test_path_properties_multiple_extensions():
    """Test path properties for files with multiple extensions."""
    sp = SidematterPath(Path("data.tar.gz"))

    assert sp.meta_json == Path("data.tar.meta.json")
    assert sp.meta_yaml == Path("data.tar.meta.yml")
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
        sp.meta_json.write_text('{"title": "Test"}')
        sp.meta_yaml.write_text("title: Test")

        resolved = sp.resolve_meta()
        assert resolved == sp.meta_json


def test_resolve_meta_yaml_only():
    """Test metadata resolution when only YAML exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        sp.meta_yaml.write_text("title: Test")

        resolved = sp.resolve_meta()
        assert resolved == sp.meta_yaml


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
        sp.meta_json.write_text(json.dumps(test_data))

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
        sp.meta_yaml.write_text(yaml_content)

        meta = sp.load_meta()
        assert meta["title"] == "Test Document"
        assert meta["tags"] == ["python", "test"]


def test_load_meta_invalid_json():
    """Test error handling for invalid JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        sp.meta_json.write_text("{ invalid json")

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
        sp.meta_yaml.write_text("title: Test\ndata: [unclosed")

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
        sp.meta_yaml.write_text("title: Sidecar Title\nsource: sidecar")

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


def test_write_meta_yaml_dict():
    """Test writing YAML metadata from dict."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        test_data = {"title": "Test", "tags": ["python"]}

        written_path = sp.write_meta(test_data, fmt="yaml")
        assert written_path == sp.meta_yaml
        assert sp.meta_yaml.exists()

        # Verify content
        loaded = sp.load_meta()
        assert loaded == test_data


def test_write_meta_json_dict():
    """Test writing JSON metadata from dict."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        test_data = {"title": "Test", "tags": ["python"]}

        written_path = sp.write_meta(test_data, fmt="json")
        assert written_path == sp.meta_json
        assert sp.meta_json.exists()

        # Verify content
        loaded = sp.load_meta()
        assert loaded == test_data


def test_write_meta_raw_string():
    """Test writing raw YAML/JSON string."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        raw_yaml = "title: Custom YAML\ntags: [test]\n"

        sp.write_meta(raw_yaml, fmt="yaml")
        content = sp.meta_yaml.read_text()
        assert content == raw_yaml


def test_write_meta_none_removes_files():
    """Test that writing None removes metadata files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)

        # Create both files
        sp.meta_json.write_text('{"test": true}')
        sp.meta_yaml.write_text("test: true")

        assert sp.meta_json.exists()
        assert sp.meta_yaml.exists()

        # Write None should remove both
        sp.write_meta(None)

        assert not sp.meta_json.exists()
        assert not sp.meta_yaml.exists()


def test_write_meta_creates_parents():
    """Test that parent directories are created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "subdir" / "deep" / "test.md"

        sp = SidematterPath(doc_path)
        test_data = {"title": "Test"}

        # Directory doesn't exist yet
        assert not doc_path.parent.exists()

        sp.write_meta(test_data, fmt="yaml")

        # Should have created parents
        assert sp.meta_yaml.exists()
        assert sp.meta_yaml.parent.exists()


## Asset Tests


def test_resolve_assets_none():
    """Test asset resolution when directory doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        assert sp.resolve_assets() is None


def test_resolve_assets_exists():
    """Test asset resolution when directory exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        sp.assets_dir.mkdir()

        assert sp.resolve_assets() == sp.assets_dir


def test_asset_path_creates_dir():
    """Test that asset_path creates the assets directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)
        assert not sp.assets_dir.exists()

        asset_path = sp.asset_path("image.png")

        assert sp.assets_dir.exists()
        assert asset_path == sp.assets_dir / "image.png"


def test_asset_path_no_create():
    """Test asset_path without creating directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sp = SidematterPath(doc_path)

        asset_path = sp.asset_path("image.png", create_dir=False)

        assert not sp.assets_dir.exists()
        assert asset_path == sp.assets_dir / "image.png"


def test_copy_asset():
    """Test copying an asset file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        # Create source file
        src_file = Path(tmpdir) / "source.png"
        src_file.write_text("fake image content")

        sp = SidematterPath(doc_path)
        copied_path = sp.copy_asset(src_file)

        assert copied_path == sp.assets_dir / "source.png"
        assert copied_path.exists()
        assert copied_path.read_text() == "fake image content"


def test_copy_asset_custom_name():
    """Test copying asset with custom destination name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        # Create source file
        src_file = Path(tmpdir) / "source.png"
        src_file.write_text("fake image content")

        sp = SidematterPath(doc_path)
        copied_path = sp.copy_asset(src_file, dest_name="renamed.png")

        assert copied_path == sp.assets_dir / "renamed.png"
        assert copied_path.exists()
        assert copied_path.read_text() == "fake image content"


## Convenience Function Tests


def test_resolve_sidematter_empty():
    """Test resolve_sidematter with no metadata or assets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        sidematter = resolve_sidematter(doc_path)

        assert isinstance(sidematter, Sidematter)
        assert sidematter.doc_path == doc_path
        assert sidematter.meta_path is None
        assert sidematter.meta == {}
        assert sidematter.assets_path is None


def test_resolve_sidematter_with_metadata():
    """Test resolve_sidematter with metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        # Create metadata
        sp = SidematterPath(doc_path)
        test_data = {"title": "Test Document"}
        sp.write_meta(test_data)

        sidematter = resolve_sidematter(doc_path)

        assert sidematter.meta_path == sp.meta_yaml
        assert sidematter.meta == test_data


def test_resolve_sidematter_with_assets():
    """Test resolve_sidematter with assets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        # Create assets directory
        sp = SidematterPath(doc_path)
        sp.assets_dir.mkdir()
        (sp.assets_dir / "test.png").touch()

        sidematter = resolve_sidematter(doc_path)

        assert sidematter.assets_path == sp.assets_dir


def test_resolve_sidematter_string_path():
    """Test resolve_sidematter with string path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "test.md"
        doc_path.touch()

        # Pass string instead of Path
        sidematter = resolve_sidematter(str(doc_path))

        assert sidematter.doc_path == doc_path


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
        assert sp.meta_yaml.exists()
        assert chart_path.exists()
        assert chart_path == sp.assets_dir / "chart.png"

        # Test loading
        loaded_meta = sp.load_meta()
        assert loaded_meta == metadata

        # Test convenience function
        sidematter = resolve_sidematter(doc_path)
        assert sidematter.meta == metadata
        assert sidematter.assets_path == sp.assets_dir
