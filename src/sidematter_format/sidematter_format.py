from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from frontmatter_format import fmf_read_frontmatter, from_yaml_string, to_yaml_string
from strif import atomic_output_file, copyfile_atomic

META_NAME = "meta"
JSON_SUFFIX = f".{META_NAME}.json"
YAML_SUFFIX = f".{META_NAME}.yml"

ASSETS_SUFFIX = "assets"


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

    primary: Path
    """The primary document path."""

    # Path properties (may not exist on disk)

    @property
    def meta_json_path(self) -> Path:
        return self.primary.with_suffix(JSON_SUFFIX)

    @property
    def meta_yaml_path(self) -> Path:
        return self.primary.with_suffix(YAML_SUFFIX)

    @property
    def assets_dir(self) -> Path:
        return self.primary.with_name(f"{self.primary.stem}.{ASSETS_SUFFIX}")

    # Metadata helpers

    def resolve_meta(self) -> Path | None:
        """
        Return the first existing metadata path following the precedence order
        (`.meta.json` then `.meta.yml`) or None if neither exists.
        """
        if self.meta_json_path.exists():
            return self.meta_json_path
        if self.meta_yaml_path.exists():
            return self.meta_yaml_path
        return None

    def load_meta(self, *, use_frontmatter: bool = True) -> dict[str, Any]:
        """
        Load metadata following the precedence order:
        1. JSON sidecar (.meta.json)
        2. YAML sidecar (.meta.yml)
        3. YAML frontmatter in the document itself (if use_frontmatter is True)

        Args:
            use_frontmatter: If True and no sidecar metadata file exists, attempt to read
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
        if use_frontmatter and self.primary.exists():
            try:
                return fmf_read_frontmatter(self.primary) or {}
            except Exception:
                # If frontmatter reading fails, just return empty metadata
                return {}

        return {}

    def resolve(self, *, parse_meta: bool = True, use_frontmatter: bool = True) -> Sidematter:
        meta = None
        if parse_meta:
            meta = self.load_meta(use_frontmatter=use_frontmatter)

        return Sidematter(
            primary=self.primary,
            meta_path=self.resolve_meta(),
            meta=meta,
            assets_path=self.resolve_assets(),
        )

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
        p = self.meta_yaml_path if fmt == "yaml" else self.meta_json_path

        try:
            if data is None:
                # Remove both sidecars if they exist
                self.meta_json_path.unlink(missing_ok=True)
                self.meta_yaml_path.unlink(missing_ok=True)
                return p

            # Use atomic file writing to ensure integrity
            with atomic_output_file(p, make_parents=make_parents) as temp_path:
                if isinstance(data, str):  # Raw YAML/JSON already formatted
                    temp_path.write_text(data, encoding="utf-8")
                elif fmt == "json":
                    temp_path.write_text(
                        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                    )
                else:  # YAML from dict
                    temp_path.write_text(to_yaml_string(data, key_sort=key_sort), encoding="utf-8")
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


def resolve_sidematter(
    primary: str | Path, *, parse_meta: bool = True, use_frontmatter: bool = True
) -> Sidematter:
    """
    Convenience function that returns an *immutable* snapshot of the sidematter
    found for a given document, based on checking the expected paths.

    Args:
        primary: Path to the document file.
        parse_meta: If True, parse the metadata from the document. Default is True.
        use_frontmatter: If True and no sidecar files exist, attempt to read
            frontmatter from the document itself. Default is True.

    Returns:
        Sidematter object containing the document path, metadata path, metadata dict,
        and assets path.
    """
    return SidematterPath(Path(primary)).resolve(
        parse_meta=parse_meta, use_frontmatter=use_frontmatter
    )


@dataclass(frozen=True)
class Sidematter:
    """
    Snapshot of sidematter filenames and metadata.
    This is a pure, immutable data class; it does not touch the filesystem.
    """

    primary: Path

    meta_path: Path | None
    """Path to the metadata file, if found."""

    assets_path: Path | None
    """Path to the assets directory, if found."""

    meta: dict[str, Any] | None
    """Actual metadata, if parsed."""

    @property
    def path_list(self) -> list[Path]:
        """
        Return primary path as well as metadata and assets folder path, if they exist.
        """
        return [p for p in [self.primary, self.meta_path, self.assets_path] if p]

    def rename_as(self, new_primary: Path) -> Sidematter:
        """
        A convenience method for naming files: return a new Sidematter with the primary path
        renamed and the sidematter paths updated accordingly.
        """
        new_sm = SidematterPath(new_primary)
        new_meta_path = None
        if self.meta_path is not None:
            # Preserve the metadata format from the original
            if self.meta_path.name.endswith(JSON_SUFFIX):
                new_meta_path = new_sm.meta_json_path
            elif self.meta_path.name.endswith(YAML_SUFFIX):
                new_meta_path = new_sm.meta_yaml_path
            else:
                # Fallback: preserve whatever suffix the source has
                new_meta_path = new_primary.with_suffix(self.meta_path.suffix)

        new_assets_path = new_sm.assets_dir if self.assets_path is not None else None

        return Sidematter(
            primary=new_primary,
            meta_path=new_meta_path,
            meta=self.meta,
            assets_path=new_assets_path,
        )
