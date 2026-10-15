from otree.api import Bot
from . import Demographics, FinalQuestionnaire


class PlayerBot(Bot):
    def play_round(self):
        yield Demographics, dict(
            age=25,
            gender='Prefiero no contestar',
            zone_residence='Fuera de Lima',
            attended_university=False,
            previous_experiments=0,
            trust_public_officials=3,
            trust_government=3,
            fairness_importance=3,
        )
        yield FinalQuestionnaire, dict(instructions_clarity=4)
