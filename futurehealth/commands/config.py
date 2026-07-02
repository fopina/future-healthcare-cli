import classyclick

from .cli import CLI


class Config(classyclick.helpers.ConfigBaseCommand, CLI.Command):
    """Show or edit the current CLI configuration"""

    MASKED_FIELDS = (*classyclick.helpers.ConfigBaseCommand.MASKED_FIELDS, 'openai_api_key')
