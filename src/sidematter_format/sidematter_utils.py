"""
Utilities for handling files with sidematter (metadata and assets).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from strif import copyfile_atomic

from sidematter_format.sidematter_format import Sidematter


def copy_sidematter(
    src_path: str | Path,
    dest_path: str | Path,
    *,
    make_parents: bool = True,
    copy_original: bool = True,
    copy_assets: bool = True,
    copy_metadata: bool = True,
) -> None:
    """
    Copy a file with its sidematter files (metadata and assets).

    By default copies the file and all its sidematter. Use the boolean
    flags to selectively copy only certain components.
    """
    src = Path(src_path)
    dest = Path(dest_path)

    src_paths = Sidematter(src).resolve(parse_meta=False)
    dest_paths = src_paths.renamed_as(dest)

    if copy_metadata and src_paths.meta_path is not None and dest_paths.meta_path is not None:
        copyfile_atomic(src_paths.meta_path, dest_paths.meta_path, make_parents=make_parents)

    if copy_assets and src_paths.assets_dir is not None and dest_paths.assets_dir is not None:
        if make_parents:
            dest_paths.assets_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_paths.assets_dir, dest_paths.assets_dir, dirs_exist_ok=True)

    if copy_original:
        copyfile_atomic(src, dest, make_parents=make_parents)


def move_sidematter(
    src_path: str | Path,
    dest_path: str | Path,
    *,
    make_parents: bool = True,
    move_original: bool = True,
    move_assets: bool = True,
    move_metadata: bool = True,
) -> None:
    """
    Move a file with its sidematter files (metadata and assets).

    By default moves the file and all its sidematter. Use the boolean
    flags to selectively move only certain components.
    """
    src = Path(src_path)
    dest = Path(dest_path)

    src_paths = Sidematter(src).resolve(parse_meta=False)
    dest_paths = src_paths.renamed_as(dest)

    if make_parents:
        dest.parent.mkdir(parents=True, exist_ok=True)

    if move_metadata and src_paths.meta_path is not None and dest_paths.meta_path is not None:
        shutil.move(src_paths.meta_path, dest_paths.meta_path)

    if move_assets and src_paths.assets_dir is not None and dest_paths.assets_dir is not None:
        shutil.move(src_paths.assets_dir, dest_paths.assets_dir)

    if move_original:
        shutil.move(src, dest)


def remove_sidematter(file_path: str | Path) -> None:
    """
    Remove a file with its sidematter files (metadata and assets).
    """
    path = Path(file_path)
    sidematter = Sidematter(path).resolve(parse_meta=False)

    if sidematter.meta_path is not None:
        sidematter.meta_path.unlink(missing_ok=True)

    if sidematter.assets_dir is not None:
        shutil.rmtree(sidematter.assets_dir, ignore_errors=True)

    path.unlink(missing_ok=True)
