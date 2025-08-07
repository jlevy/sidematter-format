from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum
from functools import cache
from typing import Any, cast

from frontmatter_format.yaml_util import add_default_yaml_customizer
from ruamel.yaml import Representer
from strif import format_iso_timestamp


@cache
def register_default_yaml_representers() -> None:
    """
    Centralized YAML customization for consistent serialization of:
    - Enum: serialize as `.value`
    - datetime: ISO-8601 with trailing Z (via `strif.format_iso_timestamp`)
    - date/time: `.isoformat()`

    Call once at startup to enable these representers everywhere.
    """

    def represent_enum(dumper: Representer, data: Enum) -> Any:
        return cast(Any, dumper).represent_str(data.value)

    def represent_datetime(dumper: Representer, data: datetime) -> Any:
        return cast(Any, dumper).represent_str(format_iso_timestamp(data))

    def represent_date(dumper: Representer, data: date) -> Any:
        return cast(Any, dumper).represent_str(data.isoformat())

    def represent_time(dumper: Representer, data: time) -> Any:
        return cast(Any, dumper).represent_str(data.isoformat())

    def _customize_enum(yaml: Any) -> None:
        yaml.representer.add_multi_representer(Enum, represent_enum)

    def _customize_datetime(yaml: Any) -> None:
        yaml.representer.add_representer(datetime, represent_datetime)

    def _customize_date(yaml: Any) -> None:
        yaml.representer.add_representer(date, represent_date)

    def _customize_time(yaml: Any) -> None:
        yaml.representer.add_representer(time, represent_time)

    add_default_yaml_customizer(_customize_enum)
    add_default_yaml_customizer(_customize_datetime)
    add_default_yaml_customizer(_customize_date)
    add_default_yaml_customizer(_customize_time)


# Maybe useful in the future?

# from pydantic import BaseModel

# def represent_pydantic(dumper: Representer, data: BaseModel) -> Any:
#     """Represent Pydantic models as YAML dictionaries."""
#     return dumper.represent_dict(data.model_dump())

# add_default_yaml_customizer(
#     lambda yaml: yaml.representer.add_multi_representer(BaseModel, represent_pydantic)
# )
