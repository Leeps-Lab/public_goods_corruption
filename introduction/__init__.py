from otree.api import *

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

page_sequence = [GeneralInstructions]