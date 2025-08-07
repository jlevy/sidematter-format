from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, cast, runtime_checkable

from strif import atomic_output_file, format_iso_timestamp


@runtime_checkable
class AsDictProtocol(Protocol):
    """Protocol for objects that can render themselves as a JSON-like dict."""

    def as_dict(self) -> dict[str, Any]: ...


def _default(obj: Any) -> Any:
    """
    Reasonable JSON fallback encoder for unsupported types.
    Keeps behavior centralized and aligned with YAML representers.

    Policy:
    - datetime: ISO-8601 with trailing Z (via `strif.format_iso_timestamp`).
    - date/time: `.isoformat()`.
    - Enum: `.value`.
    - Dataclasses: `asdict()`.
    - Objects with `as_dict()`: use that mapping.
    - Path: string path.
    - set: convert to list.
    """
    if isinstance(obj, datetime):
        return format_iso_timestamp(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, AsDictProtocol):
        return obj.as_dict()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, set):
        return list(cast(Iterable[Any], obj))
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def to_json_string(value: Any, *, indent: int | None = 2) -> str:
    """
    Serialize any value to a JSON string using the sensible defaults
    for enums and dates/times.
    """
    return json.dumps(value, default=_default, indent=indent, ensure_ascii=False)


def write_json_file(value: Any, path: str | Path, *, indent: int | None = 2) -> None:
    """
    Write JSON to a file atomically using the sensible defaults
    for enums and dates/times.
    """
    p = Path(path)
    with atomic_output_file(p) as f:
        f.write_text(to_json_string(value, indent=indent), encoding="utf-8")
