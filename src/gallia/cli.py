# SPDX-FileCopyrightText: AISEC Pentesting Team
#
# SPDX-License-Identifier: Apache-2.0


import sys
from types import UnionType
from typing import Any, Never

import argcomplete
from pydantic import BaseModel, Field, create_model
from pydantic_argparse import ArgumentParser
from pydantic_argparse import BaseCommand as PydanticBaseCommand

from gallia.command import BaseCommand
from gallia.config import Config, load_config_file
from gallia.log import Loglevel, setup_logging
from gallia.plugins.plugin import Command, CommandTree, load_commands

setup_logging(Loglevel.DEBUG)


defaults = dict[type, dict[str, Any]]
_CLASS_ATTR = "_dynamic_gallia_command_class_reference"
model_counter: int = 0


def _create_parser_from_command(
    command: Command, config: Config, extra_defaults: defaults
) -> tuple[type[PydanticBaseCommand], defaults]:
    config_attributes = command.config.attributes_from_config(config)
    env_attributes = command.config.attributes_from_env()
    config_attributes.update(env_attributes)
    extra_defaults[command.config] = config_attributes
    setattr(command.config, _CLASS_ATTR, command.command)

    return command.config, extra_defaults


def _create_parser_from_tree(
    command_tree: CommandTree,
    config: Config,
    extra_defaults: defaults,
) -> tuple[type[PydanticBaseCommand], defaults]:
    global model_counter
    model_counter += 1
    args: dict[str, tuple[type | UnionType, Field]] = {}

    for key, value in command_tree.subtree.items():
        if isinstance(value, Command):
            model_type, extra_defaults = _create_parser_from_command(value, config, extra_defaults)
        else:
            model_type, extra_defaults = _create_parser_from_tree(value, config, extra_defaults)

        args[key] = (model_type | None, Field(None, description=value.description))

    return (
        create_model(
            f"_dynamic_gallia_hierarchy_model_{model_counter}", __base__=PydanticBaseCommand, **args
        ),
        extra_defaults,
    )


def create_parser(commands: Command | dict[str, CommandTree | Command]) -> ArgumentParser:
    """Creates an argument parser out of the given command hierarchy.
    For accessing the command after parsing, see get_command().
    See parse_and_run() for an easy-to-use one call alternative.

    :param commands: A hierarchy of commands.
    :return The argument parser for the given commands.
    """

    config, _ = load_config_file()

    if isinstance(commands, Command):
        model, extra_defaults = _create_parser_from_command(commands, config, {})
    else:
        command_tree = CommandTree("", subtree=commands)
        model, extra_defaults = _create_parser_from_tree(command_tree, config, {})

    return ArgumentParser(model=model, extra_defaults=extra_defaults)


def get_command(config: BaseModel) -> BaseCommand:
    """Retrieve the command out of the config returned by an argument parser as created by create_parser().

    :param config:
    :return: The command initiated with the given config.
    """

    return getattr(config, _CLASS_ATTR)(config)


def parse_and_run(
    commands: Command | dict[str, CommandTree | Command], auto_complete: bool = True
) -> Never:
    """Creates an argument parser out of the given command hierarchy and runs the command with its argument.
    This function never returns.
    A set of commands is simply generated by a dict with command name as key and a Command object as value.
    For a full hierarchy of commands CommandTrees can be used.

    :param commands: A hierarchy of commands.
    :param auto_complete: Turns auto-complete functionality on.
    """

    parser = create_parser(commands)

    if auto_complete:
        argcomplete.autocomplete(parser)

    _, config = parser.parse_typed_args()
    sys.exit(get_command(config).entry_point())


def main() -> None:
    gallia_commands = load_commands()
    parse_and_run(gallia_commands)


if __name__ == "__main__":
    main()
