"""
Utilities for handling files with sidematter (metadata and assets).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from strif import copyfile_atomic

from sidematter_format.sidematter_format import resolve_sidematter


def copy_with_sidematter(
    src_path: str | Path, dest_path: str | Path, *, make_parents: bool = True
) -> None:
    """
    Copy a file with its sidematter files (metadata and assets).
    """
    src = Path(src_path)
    dest = Path(dest_path)

    # Get source sidematter and rename for destination
    src_sidematter = resolve_sidematter(src, parse_meta=False)
    dest_sidematter = src_sidematter.renamed_as(dest)

    # Copy metadata if it exists
    if src_sidematter.meta_path is not None and dest_sidematter.meta_path is not None:
        copyfile_atomic(
            src_sidematter.meta_path, dest_sidematter.meta_path, make_parents=make_parents
        )

    # Copy assets if they exist
    if src_sidematter.assets_dir is not None and dest_sidematter.assets_dir is not None:
        if make_parents:
            dest_sidematter.assets_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_sidematter.assets_dir, dest_sidematter.assets_dir, dirs_exist_ok=True)

    # Copy the main file
    copyfile_atomic(src, dest, make_parents=make_parents)


def move_with_sidematter(
    src_path: str | Path, dest_path: str | Path, *, make_parents: bool = True
) -> None:
    """
    Move a file with its sidematter files (metadata and assets).
    """
    src = Path(src_path)
    dest = Path(dest_path)

    # Get source sidematter and rename for destination
    src_sidematter = resolve_sidematter(src, parse_meta=False)
    dest_sidematter = src_sidematter.renamed_as(dest)

    if make_parents:
        dest.parent.mkdir(parents=True, exist_ok=True)

    # Move metadata if it exists
    if src_sidematter.meta_path is not None and dest_sidematter.meta_path is not None:
        shutil.move(src_sidematter.meta_path, dest_sidematter.meta_path)

    # Move assets if they exist
    if src_sidematter.assets_dir is not None and dest_sidematter.assets_dir is not None:
        shutil.move(src_sidematter.assets_dir, dest_sidematter.assets_dir)

    # Move the main file
    shutil.move(src, dest)


def remove_with_sidematter(file_path: str | Path) -> None:
    """
    Remove a file with its sidematter files (metadata and assets).
    """
    path = Path(file_path)
    sidematter = resolve_sidematter(path, parse_meta=False)

    # Remove metadata file if it exists
    if sidematter.meta_path is not None:
        sidematter.meta_path.unlink(missing_ok=True)

    # Remove assets directory if it exists
    if sidematter.assets_dir is not None:
        shutil.rmtree(sidematter.assets_dir, ignore_errors=True)

    # Remove the main file
    path.unlink(missing_ok=True)
