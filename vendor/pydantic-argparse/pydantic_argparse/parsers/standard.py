# SPDX-FileCopyrightText: Hayden Richards
#
# SPDX-License-Identifier: MIT

"""Parses Standard Pydantic Fields to Command-Line Arguments.

The `standard` module contains the `parse_field` function, which parses
standard `pydantic` model fields to `ArgumentParser` command-line arguments.

Unlike the other `parser` modules, the `standard` module does not contain a
`should_parse` function. This is because it is the fallback case, where fields
that do not match any other types and require no special handling are parsed.
"""

import argparse

from pydantic_argparse.utils.pydantic import PydanticField

from .utils import SupportsAddArgument


def parse_field(
    parser: SupportsAddArgument,
    field: PydanticField,
) -> None:
    """Adds standard pydantic field to argument parser.

    Args:
        parser (argparse.ArgumentParser): Argument parser to add to.
        field (PydanticField): Field to be added to parser.
    """
    # Add Standard Field
    parser.add_argument(
        *field.arg_names(),
        action=argparse._StoreAction,
        help=field.description(),
        metavar=field.metavar(),
        **field.arg_required(),
        **field.arg_default(),
        **field.arg_const(),
        **field.arg_dest(),
    )
