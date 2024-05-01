from otree.api import *
import json

#Configuracion del archivo csv: 
import csv
archivo_csv = 'config.csv'
datos = []
with open(archivo_csv, newline='') as csvfile:
    lector_csv = csv.DictReader(csvfile)
    for fila in lector_csv:
        datos.append(fila)

# Acceder a los valores
segments = int(datos[0]['segments'])
periods_per_segment = int(datos[0]['periods_per_segment'])
left_endowment = datos[0]['left_endowment']
right_endowment = datos[0]['right_endowment']
multiplication_factor = datos[0]['multiplication_factor']
private_interaction = datos[0]['private_interaction']
equal_asigment = datos[0]['equal_asigment']
contribucion = 0

# Imprimir los valores
print(f'Segments: {segments}')
print(f'Periods per Segment: {periods_per_segment}')
print(f'Left Endowment: {left_endowment}')
print(f'Right Endowment: {right_endowment}')
print(f'Multiplication Factor: {multiplication_factor}')
print(f'Private Interaction: {private_interaction}')
print(f'Equal Asigment: {equal_asigment}')









doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'public_goods_simple'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = segments
    ENDOWMENT = 100
    LEFT_ENDOWMENT = left_endowment
    RIGHT_ENDOWMENT = right_endowment
    



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
    
    '''
    def creating_session(self):
        players = self.get_players()
        for player in (players):
                player.rol = '22'
    '''
    pass


class Group(BaseGroup):

    pass


class Player(BasePlayer):
    BasePlayer.payoff = C.ENDOWMENT
    endowment_izquierda = models.IntegerField(initial=C.LEFT_ENDOWMENT)
    endowment_derecha = models.IntegerField(initial=C.RIGHT_ENDOWMENT)
    transferencia_neta = models.IntegerField(initial=0)
    transferencia_enviada = models.IntegerField(initial=0)
    lista_de_resultados = models.LongStringField(initial="")
    _lista_de_resultados = models.StringField()
    contribucion_ciudadano = models.IntegerField(initial=0)
    asignacion_servicios_publicos = models.IntegerField(initial=0)
    periodo = models.IntegerField(initial=0)

    @property
    def lista_de_resultados(self):
        _lista_de_resultados = self.field_maybe_none('_lista_de_resultados')
        if _lista_de_resultados is None:
            return []
        else:
            return json.loads(_lista_de_resultados)

    @lista_de_resultados.setter
    def lista_de_resultados(self, value):
        self._lista_de_resultados = json.dumps(value)

    pass


# PAGES
class InitPage(Page):
    pass


class Bargain(Page):

    
    endowment_izquierda = C.LEFT_ENDOWMENT;
    endowment_derecha = C.RIGHT_ENDOWMENT;

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

        ejem en el js: liveSend({'emisor': parseInt(emisor), 'receptor': parseInt(receptor),  'operacion':'negociar_puntos', 'sub_operacion': 'solicitar_puntos','puntos': 44});

        -'operacion'. 'actualizar_puntuacion'
                        'contribucion_ciudadano'
                        'asignacion_de_servicios_publicos'
                        'transferencia_enviada'
                        'transferencia_recibida'
                        'periodo'
                       

        
        '''
        if(data['operacion'] == 'proyecto_comun'):
            if(data['sub_operacion'] == 'ciudadano_envia_puntos'):
                print("ciudadano envia ", data['puntos'], "puntos")

                pass
            elif(data['sub_operacion'] == 'funcionario_envia_puntos'):
                pass
            pass
        
            
            
        if(data['operacion'] == 'actualizar_puntuacion'):
            print("round_number: ",player.round_number)
            if (player.round_number != 1):
                print("historial de la ronda ", player.round_number," : ",player.in_round(player.round_number - 1).lista_de_resultados)
            else:
                print('round_number = 1, por lo que no hay historial')

            

            player.asignacion_servicios_publicos = int(data['asignacion_de_servicios_publicos'])
            player.contribucion_ciudadano = int(data['contribucion_ciudadano'])
            #player.lista_de_resultados = player.lista_de_resultados
            lista = player.lista_de_resultados
            #player.lista_de_resultados = lista
            print(player.lista_de_resultados)
            lista.append(data)
            
            player.lista_de_resultados = lista
            print(len(player.lista_de_resultados))
            return 0
        if(data['sub_operacion'] == 'enviar_puntos_respuesta'):
            
            print("actualizar puntos: " + str(data['puntos']))
        
        return {data['receptor']: data}
    pass


class FirstWaitPage(WaitPage):
    
    @staticmethod
    def after_all_players_arrive(group: Group):
        for p in group.get_players():
            p.periodo = 1
    
    pass

class ResultsWaitPage(WaitPage):
    
    @staticmethod
    def after_all_players_arrive(group: Group):
        for p in group.get_players():
            p.periodo = p.periodo +1
    
    pass


class Results(Page):
    pass

class EndPage(Page):
    pass


#sequence = [InitPage]
sequence = [FirstWaitPage]
for i in range(periods_per_segment):
    sequence.append(Bargain)
    #sequence.append(Results)
    sequence.append(ResultsWaitPage)


#sequence.append(EndPage)

page_sequence = sequence

