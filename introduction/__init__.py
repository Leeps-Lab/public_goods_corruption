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
        
    def vars_for_template(player):
        num_treatments = len(player.session.config['treatment_order'])
        num_rounds = player.session.config['num_rounds']
        tot_num_rounds = num_treatments * num_rounds
        avg_round_time = 4
        tot_session_time = tot_num_rounds * avg_round_time
        if tot_session_time < 60:
            time_unit = 'minutos'
        else:
            tot_session_time = round((tot_num_rounds * avg_round_time) / 60, 1)
            time_unit = 'horas'
        return dict(
            num_treatments=num_treatments,
            num_rounds=num_rounds,
            tot_num_rounds=tot_num_rounds,
            tot_session_time=tot_session_time,
            time_unit=time_unit
        )

page_sequence = [GeneralInstructions]