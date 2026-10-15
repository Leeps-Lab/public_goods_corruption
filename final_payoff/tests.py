from otree.api import Bot


class PlayerBot(Bot):
    def play_round(self):
        # FinalPayoff is the last screen and has no button: participants stay
        # on it, so there is nothing to submit.
        return
