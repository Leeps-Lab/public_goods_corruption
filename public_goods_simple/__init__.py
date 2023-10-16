from otree.api import *


doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'public_goods_simple'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    ENDOWMENT = 500


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    BasePlayer.payoff = C.ENDOWMENT
    pass


# PAGES
class Bargain(Page):
    
    @staticmethod
    def vars_for_template(player):

        numero_de_participantes = player.session.num_participants
        lista_de_ciudadanos = [] # de 1 n, donde n es el numero de ciudadanos
        lista_de_participantes = [] # de 1 a n-1, donde n es el numero de ciudadanos

        for i in range(1, numero_de_participantes):
            lista_de_ciudadanos.append(i)
        for i in range(1, numero_de_participantes+1):
            lista_de_participantes.append(i)



        #Esta parte es exclusiva del chat
        chat_grupos = []
        for i in range(1, numero_de_participantes+1):
            for j in range(1, numero_de_participantes+1):
                if (j > i):
                    grupo = []
                    grupo.append(i)
                    grupo.append(j)
                    nuevo_diccionario = {"user1": i, "user2": j, "nombre_canal_chat": str(i)+str(j)}
                    chat_grupos.append(nuevo_diccionario)


        id_de_funcionario = numero_de_participantes

        #puntos iniciales de participantes:
        #puntos = []
        #for i in range(1,numero_de_participantes):
        #    nuevo_diccionario = {"user1": i, "user2": j, "nombre_canal_chat": str(i)+str(j)}



        return dict(
            id_de_funcionario = id_de_funcionario,
            lista_de_ciudadanos = lista_de_ciudadanos,
            lista_de_participantes = lista_de_participantes,
            chat_grupos = chat_grupos,
        )


    


    @staticmethod
    def live_method(player, data):
        print('received',  data)
        #if(data['operacion'] == 'proyecto_comun'):
        #    data['monto_comun'] == data['monto_comun'] + data['puntos']
        return {data['receptor']: data}
    pass


class ResultsWaitPage(WaitPage):
    pass


class Results(Page):
    pass


page_sequence = [Bargain, ResultsWaitPage, Results]
