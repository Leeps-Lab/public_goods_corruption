from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'final'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    understanding = models.LongStringField(
        blank=True,
        label='¿Qué entendiste de las instrucciones?',
    )
    doubts = models.LongStringField(
        blank=True,
        label='¿Qué dudas tuviste durante la sesión?',
    )
    suggestions = models.LongStringField(
        blank=True,
        label='¿Qué sugerencias tienes para mejorar la claridad de las instrucciones o la experiencia del juego?',
    )


# PAGES
class FinalQuestionnaire(Page):
    form_model = 'player'
    form_fields = ['understanding', 'doubts', 'suggestions']


page_sequence = [FinalQuestionnaire]