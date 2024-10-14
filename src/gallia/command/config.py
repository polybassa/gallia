# SPDX-FileCopyrightText: AISEC Pentesting Team
#
# SPDX-License-Identifier: Apache-2.0

import binascii
import os
import tomllib
from abc import ABC
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    TypeAlias,
    TypeVar,
    Union,
    Unpack,
    get_args,
    get_origin,
)

from pydantic import BeforeValidator
from pydantic.fields import _FromFieldInfoInputs
from pydantic_argparse import BaseCommand
from pydantic_argparse.utils.field import ArgFieldInfo
from pydantic_core import PydanticUndefined

from gallia.config import Config
from gallia.utils import unravel, unravel_2d

registry: dict[str, str] = {}


def err_int(x: str, base: int) -> int:
    try:
        return int(x, base)
    except ValueError:
        base_suffix = ""

        if base != 0:
            base_suffix = f" with base {base}"

        raise ValueError(
            f"{repr(x)} is not a valid representation for an integer{base_suffix}"
        ) from None


AutoInt = Annotated[int, BeforeValidator(lambda x: x if isinstance(x, int) else err_int(x, 0))]


HexInt = Annotated[int, BeforeValidator(lambda x: x if isinstance(x, int) else err_int(x, 16))]


HexBytes = Annotated[
    bytes,
    BeforeValidator(lambda x: x if isinstance(x, bytes) else binascii.unhexlify(x)),
]


Ranges = Annotated[list[int], BeforeValidator(lambda x: x if isinstance(x, list) else unravel(x))]


Ranges2D = Annotated[
    dict[int, list[int]],
    BeforeValidator(
        lambda x: x
        if isinstance(x, dict)
        else unravel_2d(" ".join(x))
        if isinstance(x, list)
        else unravel_2d(x)
    ),
]


T = TypeVar("T")


EnumType = TypeVar("EnumType", bound=Enum)


def auto_enum(x: str, enum_type: type[EnumType]) -> EnumType:
    try:
        return enum_type[x]
    except KeyError:
        try:
            return enum_type(x)
        except ValueError:
            try:
                return enum_type(int(x, 0))
            except ValueError:
                pass

    raise ValueError(f"{x} is not a valid key or value for {enum_type}")


if TYPE_CHECKING:
    Idempotent: TypeAlias = Annotated[T, ""]
    EnumArg: TypeAlias = Annotated[EnumType, ""]
else:

    class _TrickType:
        def __init__(self, function: Callable[[type[T]], type[T]]):
            self.function = function

        def __getitem__(self, cls: type[T]) -> type[T]:
            return self.function(cls)

    Idempotent = _TrickType(
        lambda cls: Annotated[cls, BeforeValidator(lambda x: x if isinstance(x, cls) else cls(x))]
    )
    EnumArg = _TrickType(
        lambda cls: Annotated[
            cls, BeforeValidator(lambda x: x if isinstance(x, cls) else auto_enum(x, cls))
        ]
    )


class ConfigArgFieldInfo(ArgFieldInfo):
    def __init__(
        self,
        default: Any,
        positional: bool,
        short: str | None,
        metavar: str | None,
        cli_group: str | None,
        const: Any,
        hidden: bool,
        config_section: str | None,
        **kwargs: Unpack[_FromFieldInfoInputs],
    ):
        super().__init__(
            default=default,
            positional=positional,
            short=short,
            metavar=metavar,
            cli_group=cli_group,
            const=const,
            hidden=hidden,
            **kwargs,
        )

        self.config_section = config_section


# TODO: Docstring
def Field(
    default: Any = PydanticUndefined,
    positional: bool = False,
    short: str | None = None,
    metavar: str | None = None,
    group: str | None = None,
    const: Any = PydanticUndefined,
    hidden: bool = False,
    config_section: str | None = None,
    **kwargs: Unpack[_FromFieldInfoInputs],
) -> Any:
    return ConfigArgFieldInfo(
        default, positional, short, metavar, group, const, hidden, config_section, **kwargs
    )


class GalliaBaseModel(BaseCommand, ABC):
    init_kwargs: dict[str, Any] | None = Field(None, hidden=True)
    _cli_group: str | None
    _config_section: str | None

    def __init__(self, **data: Any):
        init_kwargs = data.pop("init_kwargs", {})

        if init_kwargs is None:
            init_kwargs = {}

        init_kwargs.update(data)

        super().__init__(**init_kwargs)

    def __init_subclass__(
        cls,
        /,
        cli_group: str | None = None,
        config_section: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init_subclass__(**kwargs)

        cls._config_section = config_section
        cls._cli_group = cli_group

        for attribute, info in vars(cls).items():
            # Attribute specific annotation takes precedence
            if isinstance(info, ArgFieldInfo) and info.group is None:
                info.group = cli_group

            if isinstance(info, ConfigArgFieldInfo):
                # Attribute specific annotation takes precedence
                if info.config_section is None:
                    info.config_section = config_section

                # Add config to registry
                if info.config_section is not None:
                    config_attribute = (
                        f"{info.config_section}.{attribute}"
                        if info.config_section != ""
                        else attribute
                    )
                    default = "" if info.default is None else f" ({info.default})"
                    description = "" if info.description is None else info.description
                    type_annotation = cls.__annotations__[attribute]
                    type_hint = (
                        type_annotation.__origin__
                        if get_origin(type_annotation) is Annotated
                        else type_annotation
                    )  # (...).__origin__ is not equivalent to using get_origin(...)

                    if (origin := get_origin(type_hint)) is Union or origin is UnionType:
                        type_ = " | ".join(x.__name__ for x in get_args(type_hint) if x is not None)
                    else:
                        type_ = type_hint.__name__

                    registry[config_attribute] = f"{description} [{type_}]{default}"

    @classmethod
    def attributes_from_toml(cls, path: Path) -> dict[str, Any]:
        toml_config = tomllib.loads(path.read_text())
        return cls.attributes_from_config(Config(toml_config))

    @classmethod
    def attributes_from_config(cls, config: Config) -> dict[str, Any]:
        result = {}

        for name, info in cls.model_fields.items():
            if isinstance(info, ConfigArgFieldInfo):
                config_attribute = (
                    f"{info.config_section}.{name}" if info.config_section != "" else name
                )

                if (value := config.get_value(config_attribute)) is not None:
                    result[name] = value

        return result

    @classmethod
    def attributes_from_env(cls) -> dict[str, Any]:
        result = {}

        for name, info in cls.model_fields.items():
            if isinstance(info, ConfigArgFieldInfo):
                config_attribute = f"GALLIA_{name.upper()}"

                if (value := os.getenv(config_attribute)) is not None:
                    result[name] = value

        return result
