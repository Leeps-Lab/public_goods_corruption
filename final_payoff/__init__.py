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
    additional_fee = models.FloatField()


# PAGES
class FinalPayoff(Page):
    @staticmethod
    def vars_for_template(player):
        def format_currency(value):
            return "S/ {:,.2f}".format(value).replace(',', 'X').replace('.', ',').replace('X', ' ')

        # Variable pay = average points per round / exchange rate
        config = player.session.config
        tot_num_rounds = len(config['treatment_order']) * config['num_rounds']
        mean_points = float(player.participant.session_payoff) / tot_num_rounds
        player.additional_fee = mean_points / config['exchange_rate']

        return dict(
            participant_label=player.participant.label,
            mean_points=f'{mean_points:.1f}'.replace('.', ','),
            participation_fee=format_currency(player.session.config['participation_fee']),
            additional_fee=format_currency(player.additional_fee),
            total_payoff=format_currency(player.session.config['participation_fee'] + player.additional_fee),
        )
    

page_sequence = [FinalPayoff]