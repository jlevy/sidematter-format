from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from frontmatter_format import fmf_read_frontmatter, from_yaml_string, to_yaml_string
from strif import atomic_output_file, copyfile_atomic

from sidematter_format.json_conventions import to_json_string

META_NAME = "meta"
JSON_SUFFIX = f".{META_NAME}.json"
YAML_SUFFIX = f".{META_NAME}.yml"

ASSETS_SUFFIX = "assets"


class SidematterError(RuntimeError):
    """
    Raised for sidematter read/write problems.
    """


@dataclass(slots=True, frozen=True)
class Sidematter:
    """
    A wrapper around a "primary" file that exposes reading and modifying sidematter
    files. Includes helpers for resolving, finding, and reading/writing metadata and
    assets.

    For simple reading, call `resolve()` immediately to get a `ResolvedSidematter`
    object with all the sidematter paths and metadata.
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

    # Resolving and finding paths.

    def resolve(
        self, *, parse_meta: bool = True, use_frontmatter: bool = True
    ) -> ResolvedSidematter:
        """
        Check filesystem for metadata, optionally including frontmatter, as well as
        sidematter metadata and assets, and return a snapshot of what is currently present.

        Args:
            primary: Path to the document file.
            parse_meta: If True, parse the metadata from the document. Default is True.
            use_frontmatter: If True and no sidecar files exist, attempt to read
                frontmatter from the document itself. Default is True.

        Returns:
            Sidematter object containing the document path, metadata path, metadata dict,
            and assets path.
        """
        meta = None
        if parse_meta:
            try:
                meta = self.read_meta(use_frontmatter=use_frontmatter)
            except SidematterError:
                # If can't parse metadata, just leave unresolved
                pass

        return ResolvedSidematter(
            primary=self.primary,
            meta_path=self.resolve_meta(),
            meta=meta,
            assets_dir=self.resolve_assets(),
        )

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

    def resolve_assets(self) -> Path | None:
        return self.assets_dir if self.assets_dir.is_dir() else None

    # Reading and writing metadata.

    def read_meta(self, *, use_frontmatter: bool = True) -> dict[str, Any]:
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
                parsed: Any = from_yaml_string(p.read_text(encoding="utf-8")) or {}
                if not isinstance(parsed, dict):
                    raise SidematterError(f"Metadata is not a dict: got {type(parsed)}: {p}")
                return cast(dict[str, Any], parsed)
            except Exception as e:
                raise SidematterError(f"Error loading metadata: {p}: {e}") from e

        # Try frontmatter fallback if enabled and document exists
        if use_frontmatter and self.primary.exists():
            try:
                return fmf_read_frontmatter(self.primary) or {}
            except Exception:
                # If frontmatter reading fails, just return empty metadata
                return {}

        return {}

    def write_meta(
        self,
        data: dict[str, Any] | str,
        *,
        formats: Literal["yaml", "json", "all"] = "yaml",
        key_sort: Callable[[str], Any] | None = None,
        make_parents: bool = True,
    ) -> Path:
        """
        Serialize `data` to one or both sidecar files according to `formats`.

        If `data` is a raw string, it is written verbatim for the selected single format.
        When `formats == "all"`, both YAML and JSON are written and returns the JSON path.
        """
        if formats not in ("yaml", "json", "all"):
            raise ValueError("formats must be 'yaml', 'json', or 'all'")

        fmts: list[str] = ["yaml", "json"] if formats == "all" else [formats]

        # Require format for raw string data.
        if isinstance(data, str) and len(fmts) > 1:
            raise ValueError(
                "Cannot write raw string to multiple formats; provide a dict or choose one format"
            )

        # Return-path rules
        return_path: Path = (
            self.meta_yaml_path if ("json" not in fmts and "yaml" in fmts) else self.meta_json_path
        )

        last_path: Path | None = None
        try:
            for fmt in fmts:
                p = self.meta_yaml_path if fmt == "yaml" else self.meta_json_path
                last_path = p
                # Use atomic file writing to ensure integrity
                with atomic_output_file(p, make_parents=make_parents) as temp_path:
                    if isinstance(data, str):  # Raw YAML/JSON already formatted
                        temp_path.write_text(data)
                    elif fmt == "json":
                        # Write JSON and trailing newline in a single call to avoid overwriting
                        temp_path.write_text(to_json_string(data) + "\n")
                    else:  # YAML from dict
                        temp_path.write_text(to_yaml_string(data, key_sort=key_sort))
            return return_path
        except Exception as e:
            raise SidematterError(f"Error writing metadata: {last_path or 'unknown path'}") from e

    def delete_meta(
        self,
        *,
        formats: Literal["yaml", "json", "all"] = "all",
    ) -> None:
        """
        Delete sidecar metadata files according to `formats`.
        """
        if formats not in ("yaml", "json", "all"):
            raise ValueError("formats must be 'yaml', 'json', or 'all'")
        fmts: list[str] = ["yaml", "json"] if formats == "all" else [formats]
        for fmt in fmts:
            p = self.meta_yaml_path if fmt == "yaml" else self.meta_json_path
            p.unlink(missing_ok=True)

    # Asset helpers

    def asset_path(self, name: str | Path) -> Path:
        """
        Path of an asset in the assets directory.
        """
        return self.assets_dir / name

    def add_asset(self, src: str | Path, dest_name: str | None = None) -> Path:
        """
        Convenience wrapper to copy a file into the asset directory and return its
        new path. Uses atomic copy to ensure file integrity.
        """
        src_path = Path(src)
        target = self.asset_path(dest_name or src_path.name)
        copyfile_atomic(src_path, target, make_parents=True)
        return target

    def copy_assets_from(self, src_dir: str | Path, glob: str = "**/*") -> list[Path]:
        """
        Copy all files from a directory into the asset directory.
        """
        src_path = Path(src_dir)
        if not src_path.is_dir():
            raise ValueError(f"Asset source is not a directory: {src_path!r}")

        self.assets_dir.mkdir(parents=True, exist_ok=True)
        copied: list[Path] = []
        for path in src_path.glob(glob):
            if path.is_file():
                copied.append(self.add_asset(path))
        return copied


@dataclass(frozen=True)
class ResolvedSidematter:
    """
    Snapshot of sidematter filenames and metadata. It should
    This is a pure, immutable data class; it does not touch the filesystem.
    """

    primary: Path

    meta_path: Path | None
    """Path to the metadata file, if found."""

    assets_dir: Path | None
    """Path to the assets directory, if found."""

    meta: dict[str, Any] | None
    """Actual metadata, if parsed."""

    @property
    def path_list(self) -> list[Path]:
        """
        Return primary path as well as metadata and assets folder path, if they exist.
        """
        return [p for p in [self.primary, self.meta_path, self.assets_dir] if p]

    def renamed_as(self, new_primary: Path) -> ResolvedSidematter:
        """
        A convenience method for naming files: return a new Sidematter with the primary path
        renamed and the sidematter paths updated accordingly.
        """
        new_sm = Sidematter(new_primary)
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

        new_assets_path = new_sm.assets_dir if self.assets_dir is not None else None

        return ResolvedSidematter(
            primary=new_primary,
            meta_path=new_meta_path,
            meta=self.meta,
            assets_dir=new_assets_path,
        )
