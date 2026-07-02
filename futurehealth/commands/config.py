import classyclick

from .cli import CLI


class Config(classyclick.helpers.ConfigBaseCommand, CLI.Command):
    """Show or edit the current CLI configuration"""
