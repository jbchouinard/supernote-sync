from loguru import logger
from pydantic_settings import BaseSettings, CliApp, CliSubCommand, get_subcommand

from snsync.config import LoggingConfig, ServiceConfig, SupernoteConfig
from snsync.service import list_files, run_check, run_forever, run_once, setup_logging
from snsync.supernote import SupernoteClientError


class LsCommand(SupernoteConfig, LoggingConfig):
    """List files on the Supernote device."""

    def run(self):
        list_files(self)


class CheckCommand(ServiceConfig):
    """Show file sync status."""

    def run(self):
        run_check(self)


class RunCommand(ServiceConfig):
    """Run file sync once then exit."""

    def run(self):
        run_once(self)


class StartCommand(ServiceConfig):
    """Run file sync until stopped."""

    def run(self):
        run_forever(self)


class Commands(
    BaseSettings,
    cli_prog_name="supernote-sync",
    cli_kebab_case=True,
    cli_use_class_docs_for_groups=True,
    cli_implicit_flags=True,
):
    ls: CliSubCommand[LsCommand]
    check: CliSubCommand[CheckCommand]
    run: CliSubCommand[RunCommand]
    start: CliSubCommand[StartCommand]

    def cli_cmd(self):
        command = get_subcommand(self)
        setup_logging(command)
        try:
            command.run()
        except SupernoteClientError as e:
            logger.error("Error connecting to device: {}", e)


def main():
    CliApp.run(Commands)


if __name__ == "__main__":
    main()
