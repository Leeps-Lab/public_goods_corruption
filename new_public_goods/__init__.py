from otree.api import *


class C(BaseConstants):
    NAME_IN_URL = 'interacción'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 3 
    ENDOWMENT = 500
    MULTIPLICATION_FACTOR = 0.5
    CITIZEN1_ROLE = 'Ciudadano 1'
    CITIZEN2_ROLE = 'Ciudadano 2'
    CITIZEN3_ROLE = 'Ciudadano 3'
    OFFICER_ROLE = 'Funcionario'


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass

def make_field():
    return models.IntegerField(blank=True, min=1)

class Player(BasePlayer):
    current_points = models.IntegerField(initial=C.ENDOWMENT)
    contribution_points = models.IntegerField(min=0)

    # offer1 = make_field()
    # offer2 = make_field()
    # offer3 = make_field()
    # offer4 = make_field()

    # request1 = make_field()
    # request2 = make_field()
    # request3 = make_field()
    # request4= make_field()


# FUNCTIONS
def creating_session(subsession):
    subsession.group_randomly(fixed_id_in_group=True)
    for player in subsession.get_players():
        player.participant.segment = 1


# PAGES
class Instructions(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1


class Interaction(Page):
    # timeout_seconds = 180
    form_model = 'player'

    # Display formfield 'contribution_points' only to citizens
    @staticmethod
    def get_form_fields(player):
        if player.role != 'Funcionario':
            return ['contribution_points']

    @staticmethod
    def vars_for_template(player):
        others = player.get_others_in_group()
    
        others_info = [
            {
                "id": other.id_in_group,
                "role": other.role,
                "channel": f"{min(player.id_in_group, other.id_in_group)}{max(player.id_in_group, other.id_in_group)}"
            }
            for other in others
        ]

        return dict(
            segment=player.participant.segment,
            others=others_info,
        )

    @staticmethod
    def live_method(player, data):
        pass
    
    # Ending the last round of the segment, update segment value
    @staticmethod
    def before_next_page(player, timeout_happened):
        if player.round_number == C.NUM_ROUNDS:
            player.participant.segment += 1


page_sequence = [Instructions, Interaction]