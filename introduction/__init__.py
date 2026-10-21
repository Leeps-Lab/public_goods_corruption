from otree.api import *

from session_timing import session_timing

class C(BaseConstants):
    NAME_IN_URL = 'introducción'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    is_mobile = models.BooleanField()


# PAGES
class GeneralInstructions(Page):
    form_model = 'player'
    form_fields = ['is_mobile']

    def error_message(player, values):
        if values['is_mobile']:
            return "Este experimento solo permite el uso de navegadores desde laptop o computadoras, no dispositivos móbiles o tablets."
        
    def vars_for_template(player):
        return dict(
            **session_timing(player.session.config),
            participation_fee_text='S/ {:.2f}'.format(player.session.config['participation_fee']).replace('.', ','),
        )

page_sequence = [GeneralInstructions]