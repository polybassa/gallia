# SPDX-FileCopyrightText: Hayden Richards
#
# SPDX-License-Identifier: MIT

"""Parses Enum Pydantic Fields to Command-Line Arguments.

The `enum` module contains the `should_parse` function, which checks whether
this module should be used to parse the field, as well as the `parse_field`
function, which parses enum `pydantic` model fields to `ArgumentParser`
command-line arguments.
"""

import argparse
import enum

from pydantic_argparse.utils.pydantic import PydanticField

from .utils import SupportsAddArgument
from ..utils.field import ArgFieldInfo


def should_parse(field: PydanticField) -> bool:
    """Checks whether the field should be parsed as an `enum`.

    Args:
        field (PydanticField): Field to check.

    Returns:
        bool: Whether the field should be parsed as an `enum`.
    """
    # Check and Return
    return field.is_a(enum.Enum)


def parse_field(
    parser: SupportsAddArgument,
    field: PydanticField,
) -> None:
    """Adds enum pydantic field to argument parser.

    Args:
        parser (argparse.ArgumentParser): Argument parser to add to.
        field (PydanticField): Field to be added to parser.
    """
    # Extract Enum
    enum_type = field.get_type()[0]

    # Determine Argument Properties
    metavar = enum_type.__name__

    if isinstance(field.info, ArgFieldInfo) and field.info.metavar is not None:
        metavar = field.info.metavar

    action = argparse._StoreAction

    # Add Enum Field
    parser.add_argument(
        *field.arg_names(),
        action=action,
        help=field.description(),
        metavar=metavar,
        **field.arg_required(),
        **field.arg_default(),
        **field.arg_const(),
        **field.arg_dest(),
    )
