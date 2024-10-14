# SPDX-FileCopyrightText: AISEC Pentesting Team
#
# SPDX-License-Identifier: Apache-2.0
import argparse
import os
import sys
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from importlib.metadata import version as meta_version
from pprint import pprint
from types import UnionType
from typing import Any, Never

import argcomplete
from pydantic import BaseModel, Field, create_model
from pydantic_argparse import ArgumentParser
from pydantic_argparse import BaseCommand as PydanticBaseCommand

from gallia import exitcodes
from gallia.command import BaseCommand
from gallia.command.base import BaseCommandConfig
from gallia.command.config import registry
from gallia.config import Config, load_config_file
from gallia.log import Loglevel, setup_logging
from gallia.plugins.plugin import CommandTree, load_commands, load_plugins
from gallia.utils import get_log_level

setup_logging(Loglevel.DEBUG)


defaults = dict[type, dict[str, Any]]
_CLASS_ATTR = "_dynamic_gallia_command_class_reference"
model_counter: int = 0


def _create_parser_from_command(
    command: type[BaseCommand], config: Config, extra_defaults: defaults
) -> tuple[type[PydanticBaseCommand], defaults]:
    config_attributes = command.CONFIG_TYPE.attributes_from_config(config)
    env_attributes = command.CONFIG_TYPE.attributes_from_env()
    config_attributes.update(env_attributes)
    extra_defaults[command.CONFIG_TYPE] = config_attributes
    setattr(command.CONFIG_TYPE, _CLASS_ATTR, command)

    return command.CONFIG_TYPE, extra_defaults


def _create_parser_from_tree(
    command_tree: CommandTree,
    config: Config,
    extra_defaults: defaults,
) -> tuple[type[PydanticBaseCommand], defaults]:
    global model_counter
    model_name = f"_dynamic_gallia_hierarchy_model_{model_counter}"
    model_counter += 1
    args: MutableMapping[str, tuple[type | UnionType, Any]] = {}

    for key, value in command_tree.subtree.items():
        if isinstance(value, CommandTree):
            model_type, extra_defaults = _create_parser_from_tree(value, config, extra_defaults)
            description = value.description
        else:
            model_type, extra_defaults = _create_parser_from_command(value, config, extra_defaults)
            description = value.SHORT_HELP

        args[key] = (model_type | None, Field(None, description=description))

    return create_model(model_name, __base__=PydanticBaseCommand, **args), extra_defaults  # type: ignore[call-overload]


def create_parser(
    commands: type[BaseCommand] | MutableMapping[str, CommandTree | type[BaseCommand]],
) -> ArgumentParser:
    """Creates an argument parser out of the given command hierarchy.
    For accessing the command after parsing, see get_command().
    See parse_and_run() for an easy-to-use one call alternative.

    :param commands: A hierarchy of commands.
    :return The argument parser for the given commands.
    """

    config, _ = load_config_file()

    if isinstance(commands, Mapping):
        command_tree = CommandTree("", subtree=commands)
        model, extra_defaults = _create_parser_from_tree(command_tree, config, {})
    else:
        model, extra_defaults = _create_parser_from_command(commands, config, {})

    return ArgumentParser(model=model, extra_defaults=extra_defaults)


def get_command(config: BaseModel) -> BaseCommand:
    """Retrieve the command out of the config returned by an argument parser as created by create_parser().

    :param config:
    :return: The command initiated with the given config.
    """

    return getattr(config, _CLASS_ATTR)(config)


def parse_and_run(
    commands: type[BaseCommand] | MutableMapping[str, CommandTree | type[BaseCommand]],
    auto_complete: bool = True,
    setup_log: bool = True,
    top_level_options: Mapping[str, Callable[[], None]] | None = None,
) -> Never:
    """Creates an argument parser out of the given command hierarchy and runs the command with its argument.
    This function never returns.
    A set of commands is simply generated by a dict with command name as key and a Command object as value.
    For a full hierarchy of commands CommandTrees can be used.

    :param commands: A hierarchy of commands.
    :param auto_complete: Turns auto-complete functionality on.
    :param setup_log: Setup logging according to the parameters in the parsed config.
    :param top_level_options: Optional top-level actions, such as "--version", given by a mapping of arguments and
                              functions. The program redirects control to the given function, once the program is
                              called with the corresponding argument and terminates after it returns.
    """

    parser = create_parser(commands)

    def make_f(c: Callable[[], None]) -> Callable[[Any], None]:
        def f(_: Any) -> None:
            c()

        return f

    if top_level_options is not None:
        for name, func in top_level_options.items():

            class Action(argparse.Action):
                f = make_f(func)

                def __call__(
                    self,
                    parser: argparse.ArgumentParser,
                    namespace: argparse.Namespace,
                    values: str | Sequence[Any] | None,
                    option_string: str | None = None,
                ) -> None:
                    self.f()
                    sys.exit(exitcodes.OK)

            parser.add_argument(
                name if name.startswith("-") else f"--{name}", nargs=0, action=Action
            )

    if auto_complete:
        argcomplete.autocomplete(parser)

    _, config = parser.parse_typed_args()

    assert isinstance(config, BaseCommandConfig)

    if setup_log:
        setup_logging(
            level=get_log_level(config.verbose),
            no_volatile_info=config.no_volatile_info,
        )

    sys.exit(get_command(config).entry_point())


def main() -> None:
    gallia_commands = load_commands()
    parse_and_run(
        gallia_commands,
        top_level_options={
            "version": version,
            "show-plugins": show_plugins,
            "show-config": show_config,
            "template": template,
        },
    )


def version() -> None:
    print(f"gallia {meta_version('gallia')}")


def _walk_commands(
    commands: Mapping[str, CommandTree | type[BaseCommand]], level: int = 0
) -> tuple[str, int]:
    command_str = ""
    command_ctr = 0

    for name, command in commands.items():
        command_str += f"{'  ' * (level + 2)}{name}"

        if isinstance(command, CommandTree):
            command_str += "\n"

            sub_command_str, sub_command_ctr = _walk_commands(command.subtree, level + 1)
            command_ctr += sub_command_ctr
            command_str += sub_command_str
        else:
            command_ctr += 1
            command_str += f": {command.__module__}.{command.__name__}\n"

    return command_str, command_ctr


def show_plugins() -> None:
    plugins = load_plugins()

    print(f"There are currently {len(plugins)} plugins installed:")

    for plugin in plugins:
        print()
        print(plugin.name())

        ecus = plugin.ecus()
        print(f"  ECUs ({len(ecus)}):")

        for ecu in ecus:
            print(f"    {ecu.OEM}: {ecu.__module__}.{ecu.__name__}")

        transports = plugin.transports()
        print(f"\n  Transports ({len(transports)}):")

        for transport in transports:
            print(f"    {transport.SCHEME}: {transport.__module__}.{transport.__name__}")

        commands = plugin.commands()
        command_str, command_ctr = _walk_commands(commands)

        print(f"\n  Commands ({command_ctr}):")
        print(command_str)


def show_config() -> None:
    if (p := os.getenv("GALLIA_CONFIG")) is not None:
        print(f"path to config set by env variable: {p}", file=sys.stderr)

    config, config_path = load_config_file()

    if config_path is not None:
        print(f"loaded config: {config_path}", file=sys.stderr)
        pprint(config)
    else:
        print("no config available", file=sys.stderr)
        sys.exit(exitcodes.CONFIG)


def template() -> None:
    groups: dict[str, dict[str, str]] = {}

    for key, value in registry.items():
        tmp = key.split(".")
        group = ".".join(tmp[:-1])
        attribute = tmp[-1]

        if group not in groups:
            groups[group] = {}

        groups[group][attribute] = value

    first = True

    for group in sorted(groups):
        if not first:
            print()

        first = False

        if group != "":
            print(f"# [{group}]")

        for attribute in sorted(groups[group]):
            print(f"# {attribute} = ... {groups[group][attribute]}")


if __name__ == "__main__":
    main()
