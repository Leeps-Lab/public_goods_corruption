from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'pago'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    pass


# PAGES
class FinalPayoff(Page):
    @staticmethod
    def vars_for_template(player):
        def format_currency(value):
            return "S/ {:,.2f}".format(value).replace(',', 'X').replace('.', ',').replace('X', ' ')
        
        return dict(
            total_points=player.participant.session_payoff,
            participation_fee=format_currency(player.session.config['participation_fee']),
            additional_fee=format_currency(float(player.participant.session_payoff) / player.session.config['exchange_rate']),
            total_payoff=format_currency(player.session.config['participation_fee'] + (float(player.participant.session_payoff) / player.session.config['exchange_rate'])),
        )
    

page_sequence = [FinalPayoff]