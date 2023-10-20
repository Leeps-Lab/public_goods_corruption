from otree.api import *


doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'public_goods_simple'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    ENDOWMENT = 100
    



class Subsession(BaseSubsession):
    '''
    def creating_session(self):
        players = self.get_players()
        num_players = len(players)
        for player in players:
            if player.id_in_group == num_players:
                player.participant.vars['rol'] = 'Funcionario'
            else:
                player.participant.vars['rol'] = 'Ciudadano ' + str(player.id_in_group)
                '''
    
    def creating_session(self):
        players = self.get_players()
        for player in (players):
                player.rol = '22'
    
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    BasePlayer.payoff = C.ENDOWMENT
    endowment_izquierda = models.IntegerField(initial=C.ENDOWMENT)
    endowment_derecha = models.IntegerField(initial=C.ENDOWMENT)
    transferencia_neta = models.IntegerField(initial=0)

    pass


# PAGES
class Bargain(Page):

    
    endowment_izquierda = C.ENDOWMENT;
    endowment_derecha = C.ENDOWMENT;

    @staticmethod
    

    @staticmethod
    def vars_for_template(player):

        numero_de_participantes = player.session.num_participants
        lista_de_ciudadanos_y_nicknames = [] # de 1 n, donde n es el numero de ciudadanos
        lista_de_participantes = [] # de 1 a n-1, donde n es el numero de ciudadanos

        for i in range(1, numero_de_participantes):
            if(i == numero_de_participantes):
                nickname = "Funcionario"
            else:
                nickname = "Ciudadano " + str(i)
            nuevo_diccionario = {"id": i, "nickname": nickname}
            lista_de_ciudadanos_y_nicknames.append(nuevo_diccionario)
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

        nicknames = []
        for i in range(1, numero_de_participantes+1):
            if(i == numero_de_participantes):
                nickname = "Funcionario"
            else:
                nickname = "Ciudadano " + str(i)
            nuevo_diccionario = {"id": i, "nickname": nickname}
            nicknames.append(nuevo_diccionario)
        #puntos iniciales de participantes:
        #puntos = []
        #for i in range(1,numero_de_participantes):
        #    nuevo_diccionario = {"user1": i, "user2": j, "nombre_canal_chat": str(i)+str(j)}
        


        return dict(
            id_de_funcionario = id_de_funcionario,
            lista_de_ciudadanos_y_nicknames = lista_de_ciudadanos_y_nicknames,
            lista_de_participantes = lista_de_participantes,
            chat_grupos = chat_grupos,
            nicknames = nicknames,
            #endowment_izquierda = player.endowment_izquierda,
            #endowment_derecha = player.endowment_izquierda,
        )


    


    @staticmethod
    def live_method(player, data):
        

        # estructura al enviar datos con live send:
        '''
        -'emisor': emisor (int), 
        -'receptor': receptor (int),  
        -'operacion':'negociar_puntos',        
            -'sub_operacion': 'enviar_puntos',
                            -'puntos' : (int)
            -'sub_operacion':'enviar_puntos_respuesta'    
                            -'respuesta' : 'si'
                            -'respuesta' : 'no'        
            -'sub_operacion'. 'cancelar_enviar_puntos'
            -'sub_operacion'. 'solicitar_puntos'
                            -'puntos' : (int)
            -'sub_operacion'. 'solicitar_puntos_respuesta'
                            -'respuesta' : 'si'
                            -'respuesta' : 'no' 
            -'sub_operacion'. 'cancelar_solicitar_puntos'

        -'operacion'. 'proyecto_comun'
            -'sub_operacion': 'ciudadano_envia_puntos'
                            - 'puntos' : (int)
            -'sub_operacion': 'funcionario_envia_puntos'
                            - 'puntos' : (int)

        ejem: liveSend({'emisor': parseInt(emisor), 'receptor': parseInt(receptor),  'operacion':'negociar_puntos', 'sub_operacion': 'solicitar_puntos','puntos': 44});
        '''


        if(data['sub_operacion'] == 'enviar_puntos_respuesta'):
            print("actualizar puntos: " + str(data['puntos']))
        
        return {data['receptor']: data}
    pass


class ResultsWaitPage(WaitPage):
    pass


class Results(Page):
    pass


page_sequence = [Bargain, ResultsWaitPage, Results]
