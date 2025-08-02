from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from frontmatter_format import fmf_read_frontmatter, from_yaml_string, to_yaml_string
from strif import atomic_output_file, copyfile_atomic


class SidematterError(RuntimeError):
    """
    Raised for sidematter read/write problems.
    """


@dataclass(slots=True, frozen=True)
class SidematterPath:
    """
    A lightweight wrapper around a *base document* that exposes all sidematter
    locations plus helpers for reading / writing them.
    """

    doc: Path

    # Path properties (may not exist on disk)

    @property
    def meta_json(self) -> Path:
        return self.doc.with_suffix(".meta.json")

    @property
    def meta_yaml(self) -> Path:
        return self.doc.with_suffix(".meta.yml")

    @property
    def assets_dir(self) -> Path:
        return self.doc.with_name(f"{self.doc.stem}.assets")

    # Metadata helpers

    def resolve_meta(self) -> Path | None:
        """
        Return the first existing metadata path following the precedence order:
        1. JSON (.meta.json)
        2. YAML (.meta.yml)
        Returns None if neither exists.
        """
        if self.meta_json.exists():
            return self.meta_json
        if self.meta_yaml.exists():
            return self.meta_yaml
        return None

    def load_meta(self, *, frontmatter_fallback: bool = True) -> dict[str, Any]:
        """
        Load metadata following the precedence order:
        1. JSON sidecar (.meta.json)
        2. YAML sidecar (.meta.yml)
        3. YAML frontmatter in the document itself (if frontmatter_fallback=True and file exists)

        Args:
            frontmatter_fallback: If True and no sidecar metadata file exists, attempt to read
                frontmatter from the document itself. Default is True.

        Returns:
            Dictionary containing the metadata, or {} if metadata is not found.

        Raises:
            SidematterError: If metadata file exists but cannot be parsed.
        """
        p = self.resolve_meta()
        if p is not None:
            try:
                if p.suffix == ".json":
                    return json.loads(p.read_text(encoding="utf-8"))
                return from_yaml_string(p.read_text(encoding="utf-8")) or {}
            except Exception as e:
                raise SidematterError(f"Error loading metadata: {p}") from e

        # Try frontmatter fallback if enabled and document exists
        if frontmatter_fallback and self.doc.exists():
            try:
                return fmf_read_frontmatter(self.doc) or {}
            except Exception:
                # If frontmatter reading fails, just return empty metadata
                return {}

        return {}

    def write_meta(
        self,
        data: dict[str, Any] | str | None,
        *,
        fmt: Literal["yaml", "json"] = "yaml",
        key_sort: Callable[[str], Any] | None = None,
        make_parents: bool = True,
    ) -> Path:
        """
        Serialize `data` to YAML or JSON sidecar. If `data` is a raw string it is
        written verbatim. Returns the path written.
        """
        if fmt not in ("yaml", "json"):
            raise ValueError("fmt must be 'yaml' or 'json'")

        # Choose target path
        p = self.meta_yaml if fmt == "yaml" else self.meta_json

        try:
            if data is None:
                # Remove both sidecars if they exist
                self.meta_json.unlink(missing_ok=True)
                self.meta_yaml.unlink(missing_ok=True)
                return p

            # Use atomic file writing to ensure integrity
            with atomic_output_file(p, make_parents=make_parents) as temp_path:
                if isinstance(data, str):  # Raw YAML/JSON already formatted
                    temp_path.write_text(data, encoding="utf-8")
                elif fmt == "json":
                    temp_path.write_text(
                        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                else:  # YAML from dict
                    temp_path.write_text(
                        to_yaml_string(data, key_sort=key_sort),
                        encoding="utf-8",
                    )
            return p
        except Exception as e:
            raise SidematterError(f"Error writing metadata to {p}") from e

    # Asset helpers

    def resolve_assets(self) -> Path | None:
        return self.assets_dir if self.assets_dir.is_dir() else None

    def asset_path(self, name: str | Path, create_dir: bool = True) -> Path:
        """
        Return the canonical path for an asset **and** (optionally) create the
        `.assets/` directory so callers can write to it immediately.
        """
        if create_dir:
            self.assets_dir.mkdir(parents=True, exist_ok=True)
        return self.assets_dir / Path(name).name

    def copy_asset(self, src: str | Path, dest_name: str | None = None) -> Path:
        """
        Convenience wrapper: copy a file into the asset directory and return its
        new path. Uses atomic copy to ensure file integrity.
        """
        src_path = Path(src)
        target = self.asset_path(dest_name or src_path.name)
        copyfile_atomic(src_path, target)
        return target


def smf_read(doc: str | Path, *, frontmatter_fallback: bool = True) -> Sidematter:
    """
    Simpler functional entry point that returns an *immutable* snapshot of the
    sidematter.  (If you need mutability, stick with `SidematterPath`.)

    Args:
        doc: Path to the document file.
        frontmatter_fallback: If True and no sidecar files exist, attempt to read
            frontmatter from the document itself. Default is True.

    Returns:
        Sidematter object containing the document path, metadata path, metadata dict,
        and assets path.
    """
    sp = SidematterPath(Path(doc))
    return Sidematter(
        doc_path=sp.doc,
        meta_path=sp.resolve_meta(),
        meta=sp.load_meta(frontmatter_fallback=frontmatter_fallback),
        assets_path=sp.resolve_assets(),
    )


@dataclass(frozen=True)
class Sidematter:
    """
    Immutable snapshot of sidematter data.
    """

    doc_path: Path
    meta_path: Path | None
    meta: dict[str, Any]
    assets_path: Path | None
