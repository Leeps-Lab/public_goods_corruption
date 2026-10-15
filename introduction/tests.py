from otree.api import Bot
from . import GeneralInstructions


class PlayerBot(Bot):
    def play_round(self):
        yield GeneralInstructions, dict(is_mobile=False)
