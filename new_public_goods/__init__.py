from otree.api import *
from sql_utils import create_tables, insert_row, add_balance, get_points, get_action, filter_transactions, filter_history, get_last_transaction_status, total_transfers_per_player
import math
import random

# Reu 14/02
# Buscar 'confirmar'
# Preguntar por T3, T5 y T7

# TODO: describir problema + pseudocódigo de solución en GITHUB del issue del timeout

# TODO: T4: T2 con pantalla adicional -> cuando (ciudadano_i le ofrece al funcionario o funcionario solicita a ciudadano_i y acepta, EN NETO es positivo) y el funcionario le da más que el promedio, que se detecte con 20% (configurable), el castigo es quitarle el 50% de lo que ganan en total a ambos
# Considerar:
# - A nivel de transacción (funcionario podría perder todo el dinero)
# - EN NETO es positivo: transferencias del ciudadano_i al funcionario
# - dar más que 0.1 puntos se considera corrupción
# - Funcionario puede escribir hasta 1 decimal
# TODO: si ciudadanos no contribuyen o funcionario no decide repartición en T4, no se le paga esa ronda (pago = 0)
# TODO: revisar lenguaje de exp de bienes públicos para nombre de columnas en tablas
# TODO: excluir participantes que estén en celular o tablet
# TODO: librería python en es para evitar lenguaje obsceno

create_tables() # Creates additional tables

class C(BaseConstants):
    NAME_IN_URL = 'interaccion'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 3
    CITIZEN_ENDOWMENT = 500
    CITIZEN1_ROLE = 'Ciudadano 1'
    CITIZEN2_ROLE = 'Ciudadano 2'
    CITIZEN3_ROLE = 'Ciudadano 3'
    OFFICER_ROLE = 'Funcionario'

class Subsession(BaseSubsession):
    officer_endowment = models.IntegerField()

class Group(BaseGroup):
    multiplier = models.FloatField(initial=0)
    total_initial_points = models.IntegerField(initial=0)
    total_contribution = models.IntegerField()
    total_allocation = models.FloatField() # = total_contribution * multiplier
    default_allocation = models.FloatField() # total_allocation / 3
    allocation1 = models.FloatField(label='¿Cuál es la cantidad de recursos que quieres distribuir al Ciudadano 1?')
    allocation2 = models.FloatField(label='¿Cuál es la cantidad de recursos que quieres distribuir al Ciudadano 2?')
    allocation3 = models.FloatField(label='¿Cuál es la cantidad de recursos que quieres distribuir al Ciudadano 3?')

class Player(BasePlayer):
    current_points = models.IntegerField()
    contribution_points = models.IntegerField(blank=True)
    actual_allocation = models.FloatField()
    timeout_penalty = models.BooleanField() # True for apply penalty


# FUNCTIONS
def creating_session(subsession):
    subsession.officer_endowment = subsession.session.config['officer_endowment']
    for player in subsession.get_players():
        player.participant.segment = 1  # Initialize segment value to 1
        player.current_points = C.CITIZEN_ENDOWMENT if player.id_in_group != 4 else subsession.officer_endowment # Initialize current points
        player.group.total_initial_points += player.current_points  # Update total points per group

def public_good_default_raw_gain(group):
    players = [p for p in group.get_players() if p.id_in_group != 4] # Exclude player with id 4 (P.O.)
    group.total_contribution = sum(p.field_maybe_none('contribution_points') or 0 for p in players)
    group.total_allocation = group.total_contribution * group.multiplier
    group.default_allocation = round(group.total_allocation / (C.PLAYERS_PER_GROUP - 1), 1) # Round to 1 decimal

def store_actual_allocation(group):
    # Confirmar: si completó los 3 con valores que no suman el total e hizo timeout?, alt1: actual_allocation que sea la repartición equitativa para los 3?, al2: cambiar al último?
    # Confirmar: si completó los 3 valores que sí suman e hizo timeout no considerar ese timeout?, alt1: valot de timeout_penalty regresar a False, alt2: igual aplicar castigo?
    allocations = [group.field_maybe_none('allocation1'), group.field_maybe_none('allocation2'), group.field_maybe_none('allocation3')]
    players = [p for p in group.get_players() if p.id_in_group != 4]  # Exclude the Public Officer
    
    # Count missing allocations
    missing_indices = [i for i, value in enumerate(allocations) if value is None]
    total_allocated = sum(value for value in allocations if value is not None)
    total_remaining = group.total_allocation - total_allocated
    
    if len(missing_indices) == 3:
        # If all 3 are missing, distribute equally
        allocation_value = group.default_allocation
        for other in players:
            other.actual_allocation = allocation_value
    elif len(missing_indices) == 2:
        # If 2 are missing, divide remaining equally
        allocation_value = round(total_remaining / 2, 1)
        for i, other in enumerate(players):
            if i in missing_indices:
                other.actual_allocation = allocation_value
            else:
                other.actual_allocation = allocations[i]
    elif len(missing_indices) == 1:
        # If 1 is missing, assign remaining points
        for i, other in enumerate(players):
            if i == missing_indices[0]:
                other.actual_allocation = total_remaining
            else:
                other.actual_allocation = allocations[i]
    else:
        # If none are missing, assign as is
        for i, other in enumerate(players):
            other.actual_allocation = allocations[i]

def set_payoffs(player):
    total_transfers = total_transfers_per_player({
        'session_code': player.session.code,
        'segment': player.participant.segment,
        'round': player.round_number,
        'participant_code': player.participant.code,
    }) 
    if player.id_in_group != 4: # If citizen
        player.payoff = (
            C.CITIZEN_ENDOWMENT
            - (player.field_maybe_none('contribution_points') or 0) 
            - total_transfers.get('transfers_given', 0) 
            + total_transfers.get('transfers_received', 0)
            + (player.actual_allocation * (1 - 0.5 * player.timeout_penalty)) # Apply 50% penalty of public share (confirmar si era 50% o 100%)
        )
    else: # If Officer
        player.payoff = (
            (player.subsession.officer_endowment * (1 - 0.5 * player.timeout_penalty)) # Apply 50% penalty of endowment (confirmar si era 50% o 100%)
            - total_transfers.get('transfers_given', 0) 
            + total_transfers.get('transfers_received', 0)
        )

def insert_history(group):
    for player in group.get_players():
        set_payoffs(player)
        total_transfers = total_transfers_per_player({
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'round': player.round_number,
            'participant_code': player.participant.code,
        }) 
        # TODO: (confirmar) añadir col de penalidad por timeout (mostrar siempre) y punishment por ser descubierto (mostrar solo en T6)?
        history_data = {
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'round': player.round_number,
            'participant_code': player.participant.code,
            'endowment': C.CITIZEN_ENDOWMENT if player.id_in_group != 4 else player.subsession.officer_endowment,
            'contribution': player.field_maybe_none('contribution_points'),
            'public_good_raw_gain': player.actual_allocation if player.id_in_group != 4 else None, # TODO: change
            'total_transfers_received': total_transfers.get('transfers_received', 0),
            'total_transfers_given': total_transfers.get('transfers_given', 0),
            'payment': float(player.payoff)
        }
        print(f"history data: {history_data}")
        insert_row(data=history_data, table='history')
    

# PAGES
class Instructions(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1
    

class FirstWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group):
        """ Set multiplier value per groups and per rounds """
        if group.session.config['random_multiplier']:
            group.multiplier = random.choice([1.5, 2.5])  # Assign the random multiplier to the group
        else:
            group.multiplier = group.session.config['multiplier']  # Use fixed multiplier


class Interaction(Page):
    timeout_seconds = 60 * 3
    form_model = 'player'

    @staticmethod
    def get_form_fields(player):
        if player.role != C.OFFICER_ROLE: # Display formfield 'contribution_points' only to citizens
            return ['contribution_points']

    @staticmethod
    def vars_for_template(player):
        others = player.get_others_in_group()
        funcionario = next((other for other in others if other.role == "Funcionario"), None) # Extract only 'Funcionario'
        other_players = [other for other in others if other.role != "Funcionario"] # Extract remaining players
        ordered_others = ([funcionario] if funcionario else []) + other_players # Generate list with 'Funcionario' first

        others_info = [
            {
                "id_in_group": other.id_in_group,
                "role": other.role,
                "channel": f"{player.participant.segment}{player.round_number}{min(player.id_in_group, other.id_in_group)}{max(player.id_in_group, other.id_in_group)}"
            }
            for other in ordered_others
        ]

        history = filter_history({
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'participant_code': player.participant.code,
        }) if player.round_number > 1 else []

        return dict(
            segment=player.participant.segment,
            others=others_info,
            history=history,
            private_interaction=player.session.config['private_interaction'],
        )

    @staticmethod
    def js_vars(player): # Sendign the sequential_decision session config to the frontend
        return dict(secuential_decision=player.session.config['sequential_decision'])

    @staticmethod
    def live_method(player, data):
        print(f"data: {data}")

        def handle_contribution(contribution_points):
            """
            Validate and process contribution points
            """
            if player.role != C.OFFICER_ROLE:
                if not isinstance(contribution_points, int) or math.isnan(contribution_points):
                    return dict(contributionPointsValid=False, error="Por favor, ingresa un número válido.")
                if contribution_points < 0:
                    return dict(contributionPointsValid=False, error="No puedes ingresar una cantidad negativa.")
                if contribution_points > player.current_points:
                    return dict(contributionPointsValid=False, error="No puedes contribuir más puntos de los que tienes disponibles.")
                
                # If valid, process contribution
                player.current_points -= contribution_points
                player.contribution_points = contribution_points
                return dict(contributionPointsValid=True, contributionPoints=contribution_points)

        def reload_contribution():
            """
            Handle reloading page when already contributed
            """
            contribution_points = player.field_maybe_none('contribution_points')
            if player.role != C.OFFICER_ROLE and contribution_points:
                print('hizo reload y había contribuido')
                return dict(update=True, contributionPointsReload=True, contributionPoints=contribution_points)
            return {}
        
        def new_transaction():
            """
            Log the initial transaction in the transactions table and its status in the status table.
            Activates when the initiator clicks "offer" or "request".
            """
            transaction_data = {
                'session_code': player.session.code,
                'segment': player.participant.segment,
                'round': player.group.round_number,
                'initiator_code': player.group.get_player_by_id(data['initiatorId']).participant.code,
                'receiver_code': player.group.get_player_by_id(data['receiverId']).participant.code,
                'initiator_id': data['initiatorId'],
                'receiver_id': data['receiverId'],
                'action': data['action'],
                'points': data['value'],
                'initiator_initial_endowment': player.current_points,
                'receiver_initial_endowment': player.group.get_player_by_id(data['receiverId']).current_points,
            }
            print(f'transaction data: {transaction_data}')

            transaction_id = insert_row(data=transaction_data, table='transactions') # Save the transaction and get the transaction ID

            status_data = {
                'transaction_id': transaction_id,
                'status': 'Iniciado',
            }
            print(f'status data:{status_data}')
            insert_row(data=status_data, table='status')

            return transaction_id

        def closing_transaction(status, transaction_id):
            """
            Log the clausure of a transaction in the status table and update total in transactions table.
            Activates when the receiver clicks "yes" or "no", or the initiator cancels the transaction.
            """
            balance_data = {
                'transaction_id': transaction_id,
                'initiator_balance': player.group.get_player_by_id(data['initiatorId']).current_points,
                'receiver_balance': player.group.get_player_by_id(data['receiverId']).current_points,
            }
            print(f'Balance data: {balance_data}')
            add_balance(data=balance_data)

            status_data = {
                'transaction_id': transaction_id,
                'status': status,
            }
            print(status_data)
            insert_row(data=status_data, table='status')

        data_type = data.get('type')

        # When contributing to the common project
        if data_type == 'contributionPoints':
            return {player.id_in_group: handle_contribution(data['value'])}
        
        # When offering/requesting points to another player (as a initiator)
        elif data_type == 'initiatingTransaction':
            transaction_id = new_transaction()

            if 'Ofrece' in data['action']:
                offer_points = data.get('value')
                if offer_points <= player.current_points:
                    return {
                        player.id_in_group: dict(offerPoints=True, initiator=True, receiver=False, offerValue=data.get('value'), myId=data.get('initiatorId'), otherId=data.get('receiverId'), transactionId=transaction_id),
                        data.get('receiverId'): dict(offerPoints=True, initiator=False, receiver=True, offerValue=data.get('value'), myId=data.get('receiverId'), otherId=data.get('initiatorId'), transactionId=transaction_id),
                    }
                else:
                    return {player.id_in_group: dict(offerPoints=False, error="No puedes ofrecer más puntos de los que tienes disponibles.")} 
            elif 'Solicita' in data['action']:
                if data.get('value') <= player.group.total_initial_points:
                    return {
                            player.id_in_group: dict(requestPoints=True, initiator=True, receiver=False, requestValue=data.get('value'), myId=data.get('initiatorId'), otherId=data.get('receiverId'), transactionId=transaction_id),
                            data.get('receiverId'): dict(requestPoints=True, initiator=False, receiver=True, requestValue=data.get('value'), myId=data.get('receiverId'), otherId=data.get('initiatorId'), transactionId=transaction_id),
                        }
                else:
                    return {player.id_in_group: dict(requestPoints=False, initiator=True)} 
        
        # When accepting/canceling points to another player (as a receiver) or canceling transaction (as initiator)
        elif data_type == 'closingTransaction':
            if data['status'] == 'Cancelado':
                closing_transaction(data['status'], data['transactionId'])
                return {player.id_in_group: dict(cancelAction=True, otherId=data['receiverId']),
                        data['receiverId']: dict(cancelAction=True, otherId=player.id_in_group)}    

            elif data['status'] == 'Rechazado':
                closing_transaction(data['status'], data['transactionId'])
                print(f"initiator: {data['transactionId']}")
                print(f"receiver: {data['receiverId']}")
                initiator = player.group.get_player_by_id(data['initiatorId'])
                receiver = player.group.get_player_by_id(data['receiverId'])
                filter_transactions_i = filter_transactions({
                    'participant_code': initiator.participant.code,
                    'round': initiator.round_number,
                    'segment': initiator.participant.segment,
                    'session_code': initiator.session.code,
                })
                filter_transactions_r = filter_transactions({
                    'participant_code': receiver.participant.code,
                    'round': receiver.round_number,
                    'segment': receiver.participant.segment,
                    'session_code': receiver.session.code,
                })
                print(f"filter transactions initiator: {filter_transactions_i}")
                print(f"filter transactions receiver: {filter_transactions_r}")
                return {
                    player.id_in_group: dict(update=True, updateTransactions=True, transactions=filter_transactions_r, otherId=data['initiatorId'], reload=False),
                    data['initiatorId']: dict(update=True, updateTransactions=True, transactions=filter_transactions_i, otherId=data['receiverId'], reload=False),
                }
            
            elif data['status'] == 'Aceptado':
                other_player = player.group.get_player_by_id(data['initiatorId'])
                points = get_points(data['transactionId'])
                action = get_action(data['transactionId'])
                if action == 'Ofrece':
                    other_player.current_points -= points
                    player.current_points += points
                else:
                    if points <= player.current_points:
                        other_player.current_points += points
                        player.current_points -= points
                    else:
                        return {player.id_in_group: dict(requestPoints=False, initiator=False)} 
                
                closing_transaction(data['status'], data['transactionId'])
                initiator = player.group.get_player_by_id(data['initiatorId'])
                receiver = player.group.get_player_by_id(data['receiverId'])
                filter_transactions_i = filter_transactions({
                    'participant_code': initiator.participant.code,
                    'round': initiator.round_number,
                    'segment': initiator.participant.segment,
                    'session_code': initiator.session.code,
                })
                filter_transactions_r = filter_transactions({
                    'participant_code': receiver.participant.code,
                    'round': receiver.round_number,
                    'segment': receiver.participant.segment,
                    'session_code': receiver.session.code,
                })
                return {
                    player.id_in_group: dict(updateTransactions=True, transactions=filter_transactions_r, otherId=data['initiatorId'], reload=False, update=True),
                    data['initiatorId']: dict(updateTransactions=True, transactions=filter_transactions_i, otherId=data['receiverId'], reload=False, update=True)
                }
        
        # When player reloads their page
        elif data_type == 'reloadPage':
            # Get the last transaction of the player in the current session, round, and segment
            last_transaction = get_last_transaction_status(
                participant_code=player.participant.code,
                round_number=player.round_number,
                segment=player.participant.segment,
                session_code=player.session.code
            ) 

            # If the last transaction is still in process, send offer/request buttons again and filtered transactions
            if last_transaction:
                transaction_id = last_transaction['transactionId']
                initiator_id = last_transaction['initiatorId']
                receiver_id = last_transaction['receiverId']
                action = last_transaction['action']
                value = last_transaction['value']

                # Fetch the filtered transactions
                transactions_data = filter_transactions({
                    'participant_code': player.participant.code,
                    'round': player.round_number,
                    'segment': player.participant.segment,
                    'session_code': player.session.code,
                })

                # Debugging
                print("Transactions while reloading (with active transaction):", transactions_data)

                # Construct common response data
                response_data = {
                    'updateTransactions': True,
                    'transactions': transactions_data,  # Sending filtered transactions
                    'update': True,
                    'transactionId': transaction_id
                }

                if action == 'Ofrece':
                    return {
                        player.id_in_group: dict(
                            offerPoints=True,
                            initiator=player.id_in_group == initiator_id,
                            receiver=player.id_in_group == receiver_id,
                            offerValue=value,
                            myId=player.id_in_group,
                            otherId=receiver_id if player.id_in_group == initiator_id else initiator_id,
                            **response_data  # Merging transaction data
                        ),
                        receiver_id: dict(
                            offerPoints=True,
                            initiator=False,
                            receiver=True,
                            offerValue=value,
                            myId=receiver_id,
                            otherId=initiator_id,
                            **response_data  # Merging transaction data
                        )
                    }
                elif action == 'Solicita':
                    return {
                        player.id_in_group: dict(
                            requestPoints=True,
                            initiator=player.id_in_group == initiator_id,
                            receiver=player.id_in_group == receiver_id,
                            requestValue=value,
                            myId=player.id_in_group,
                            otherId=receiver_id if player.id_in_group == initiator_id else initiator_id,
                            **response_data  # Merging transaction data
                        ),
                        receiver_id: dict(
                            requestPoints=True,
                            initiator=False,
                            receiver=True,
                            requestValue=value,
                            myId=receiver_id,
                            otherId=initiator_id,
                            **response_data  # Merging transaction data
                        )
                    }

            transactions_data = filter_transactions({
                'participant_code': player.participant.code,
                'round': player.round_number,
                'segment': player.participant.segment,
                'session_code': player.session.code,
            })
            print(transactions_data)

            reload = reload_contribution()
            print(reload)

            if transactions_data: # If it is not empty
                reload.update({'updateTransactions':True, 'transactions':transactions_data, 'update': True})
                return {player.id_in_group: reload}
            
            return {player.id_in_group: reload}
        
    @staticmethod
    def before_next_page(player, timeout_happened):
        if timeout_happened and player.id_in_group != 4: # Apply timeout penalty only to citizens
            player.timeout_penalty = True 
        else: 
            player.timeout_penalty = False
        
        if player.round_number == C.NUM_ROUNDS: # Ending the last round of the segment, update segment value
            player.participant.segment += 1


class MiddleWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group):
        public_good_default_raw_gain(group)


class ResourceAllocation(Page):
    timeout_seconds = 60
    form_model = 'group'
    form_fields = ['allocation1', 'allocation2', 'allocation3']

    @staticmethod
    def is_displayed(player):
        if player.session.config['resource_allocation'] == True:
            return player.id_in_group == 4

    @staticmethod
    def js_vars(player):
        return dict(total_allocation=player.group.total_allocation)

    @staticmethod
    def vars_for_template(player):
        history = filter_history({
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'participant_code': player.participant.code,
        }) if player.round_number > 1 else []

        return dict(
            segment=player.participant.segment,
            history=history,
            private_interaction=player.session.config['private_interaction'],
        )
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.timeout_penalty = True if timeout_happened else False
    

class LastWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group):
        store_actual_allocation(group)
        insert_history(group)


page_sequence = [Instructions, FirstWaitPage, Interaction, MiddleWaitPage, ResourceAllocation, LastWaitPage]