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

#Functions


# PAGES

class Instructions(Page):
    endowment_izquierda = C.LEFT_ENDOWMENT
    @staticmethod
    def vars_for_template(player):
        endowment_izquierda = C.LEFT_ENDOWMENT
        return dict(
            app_name = player.session.config.get('name'),
            endowment_izquierda = endowment_izquierda,
        )

    

class RoleAssign(Page):
    pass


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
        
        exchange_point_betwen_players = player.session.config.get('exchange_point_betwen_players', False)
        equitable_distribution_of_officials_to_citizens = player.session.config.get('equitable_distribution_of_officials_to_citizens',False)
        endowment_comun = player.session.config.get('endowment_comun',False)
        return dict(
            id_de_funcionario = id_de_funcionario,
            lista_de_ciudadanos_y_nicknames = lista_de_ciudadanos_y_nicknames,
            lista_de_participantes = lista_de_participantes,
            chat_grupos = chat_grupos,
            nicknames = nicknames,
            exchange_point_betwen_players = exchange_point_betwen_players,
            equitable_distribution_of_officials_to_citizens=equitable_distribution_of_officials_to_citizens,
            endowment_comun = endowment_comun,
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
        -'operacion': 'igualar_endowment_comun'
            -'igualar_lado': 'izquierda'
                            - 'endowment_derecha' : (int)
            -'sub_operacion': 'enviar_puntos_respuesta'
                            - 'endowment_derecha' : (int)
            -'sub_operacion': 'solicitar_puntos_respuesta'
                            - 'endowment_derecha' : (int)
    
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
                endowment_comun = player.session.config.get('endowment_comun',False)
                if(endowment_comun):
                    endowment_izquierda_actualizado = player.endowment_izquierda - int(data['puntos'])
                    print("Tienen un endowment comun: "+ str(endowment_izquierda_actualizado))
                    player.endowment_izquierda = endowment_izquierda_actualizado
                    player.endowment_derecha = endowment_izquierda_actualizado

                pass
            elif(data['sub_operacion'] == 'funcionario_envia_puntos'):
                pass
            pass
        
        if(data['operacion']=='igualar_endowment_comun'):
            print("igualar_endowment")
            puntos_a_actualizar = data['endowment_derecha']
            print("puntos a actualizar endowment izquierda: " + str(puntos_a_actualizar))
            print("emisor: " + str(data['emisor']))
            player.endowment_derecha = data['endowment_derecha']
            player.endowment_izquierda = player.endowment_derecha
            endowment_comun = player.session.config.get('endowment_comun',False)
            if (endowment_comun):
                player.endowment_izquierda = player.endowment_derecha
                print("player.endowment_derecha" + str(player.endowment_derecha))
                return {data['emisor']:{'operacion':'actualizar_endowment_izquierda', 'endowment_izquierda_actualizado':player.endowment_derecha}}
            return 0
            #return 0            
        # Esta parte se llama cuando se pasa a la siguiente pagina    
        if(data['operacion'] == 'actualizar_puntuacion'):
            print("round_number: ",player.round_number)
            if (player.round_number != 1):
                print("historial de la ronda ", player.round_number," : ",player.in_round(player.round_number - 1).lista_de_resultados)
            else:
                print('round_number = 1, por lo que no hay historial')

            

            player.asignacion_servicios_publicos = int(data['asignacion_de_servicios_publicos'])
            player.contribucion_ciudadano = int(data['contribucion_ciudadano'])
            
            lista = player.lista_de_resultados
            
            print(player.lista_de_resultados)
            lista.append(data)
            #print("actualizar_puntuacion_: "+ data)
            player.lista_de_resultados = lista
            print(len(player.lista_de_resultados))
            return 0
        if(data['sub_operacion'] == 'enviar_puntos_respuesta'):
            print("actualizar puntos: " + str(data['puntos']))

        if(data['sub_operacion'] == 'solicitar_puntos_respuesta'):
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
    left_endowment = int(datos[0]['left_endowment'])
    right_endowment = int(datos[0]['right_endowment'])
    @staticmethod 
    def after_all_players_arrive(group: Group):
        for p in group.get_players():
            p.periodo = p.periodo +1
            p.endowment_izquierda = int(left_endowment)
            p.endowment_derecha = int(right_endowment)
    
    pass


class Results(Page):
    pass

class EndPage(Page):
    pass


#sequence = [InitPage]
sequence = [FirstWaitPage]
sequence.append(Instructions)
sequence.append(RoleAssign)
for i in range(periods_per_segment):
    sequence.append(Bargain)
    #sequence.append(Results)
    sequence.append(ResultsWaitPage)


#sequence.append(EndPage)

page_sequence = sequence

