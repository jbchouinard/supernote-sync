from pydantic_settings import CliApp

from snsync.config import ServiceConfig
from snsync.service import run


class CliConfig(ServiceConfig, cli_prog_name="supernote-sync", cli_kebab_case=True):
    def cli_cmd(self):
        run(self)


def main():
    CliApp.run(CliConfig)


if __name__ == "__main__":
    main()
