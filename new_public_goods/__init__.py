from otree.api import *
from sql_utils import create_tables, insert_row, add_balance, get_points, get_action, filter_transactions, filter_history, get_last_transaction_status, total_transfers_per_player, check_corruption
from random import choices
import random
import math

# Para la reu:
# Confirmar lo de los pagos negativos y nuevos casos sobre T5

# Todos los trats entre el funcionario y ciudadano
# Solo T7 que tenga múltiples columnas

# Priorizar:
# 2. T3
# 3. T7


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
    pass

class Group(BaseGroup):
    multiplier = models.FloatField(initial=0)
    total_initial_points = models.IntegerField(initial=0)
    total_contribution = models.IntegerField()
    total_allocation = models.FloatField() # = total_contribution * multiplier
    default_allocation = models.FloatField() # total_allocation / 3
    allocation1 = models.FloatField(blank=True, label='¿Cuál es la cantidad de recursos que quieres distribuir al Ciudadano 1?')
    allocation2 = models.FloatField(blank=True, label='¿Cuál es la cantidad de recursos que quieres distribuir al Ciudadano 2?')
    allocation3 = models.FloatField(blank=True, label='¿Cuál es la cantidad de recursos que quieres distribuir al Ciudadano 3?')

class Player(BasePlayer):
    initial_points = models.IntegerField()
    current_points = models.IntegerField()
    contribution_points = models.IntegerField(blank=True)
    actual_allocation = models.FloatField()
    timeout_penalty = models.BooleanField(initial=False) # True for apply penalty
    corruption_audit = models.BooleanField() # True if get audit
    corruption_punishment = models.BooleanField(blank=True) # True if did corrupt action


# FUNCTIONS
def creating_session(subsession):
    # Retrieve configuration values
    session_config = subsession.session.config
    officer_endowment = session_config['officer_endowment']
    c1_endowment = session_config['c1_endowment']
    heterogenous_citizens = session_config['heterogenous_citizens']
    audit_prob = session_config['audit_probability']

    for player in subsession.get_players():
        player.participant.segment = 1  # Initialize segment value to 1
        player.initial_points = C.CITIZEN_ENDOWMENT if player.id_in_group != 4 else officer_endowment # Store initial points
        if heterogenous_citizens and player.id_in_group == 1: # Apply heterogeneous endowment only for Citizen 1 if enabled
            player.initial_points = c1_endowment
        player.current_points = player.initial_points # Initialize current points
        player.group.total_initial_points += player.initial_points  # Update total points per group
        player.corruption_audit = choices([True, False], weights=[audit_prob, 1 - audit_prob])[0]
        print(f'True if player will be audit: {player.corruption_audit}')

def public_good_default_raw_gain(group):
    players = [p for p in group.get_players() if p.id_in_group != 4] # Exclude player with id 4 (P.O.)
    group.total_contribution = sum(p.field_maybe_none('contribution_points') or 0 for p in players)
    group.total_allocation = group.total_contribution * group.multiplier
    group.default_allocation = round(group.total_allocation / (C.PLAYERS_PER_GROUP - 1), 1) # Round to 1 decimal

def store_actual_allocation(group):
    allocations = [group.field_maybe_none('allocation1'), group.field_maybe_none('allocation2'), group.field_maybe_none('allocation3')]
    players = [p for p in group.get_players() if p.id_in_group != 4]  # Exclude the Public Officer
    
    # Count missing allocations
    missing_indices = [i for i, value in enumerate(allocations) if value is None]
    total_allocated = sum(value for value in allocations if value is not None)

    # If all three values exist but do NOT sum to total_allocation
    if len(missing_indices) == 0 and (abs(total_allocated - group.total_allocation) > 0.1):
        print(f"Incorrect total allocation! Given: {total_allocated}, Expected: {group.total_allocation}")
        for other in players:
            other.actual_allocation = group.default_allocation
        return  # Exit early after correcting values

    # Handling Missing Values
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

def apply_corruption_penalty(group):
    """
    Determines if citizens engaged in corrupt transactions and applies punishment if necessary.
    
    - Citizens (players 1, 2, 3) are flagged if they receive/give transfers to the funcionario.
    - A citizen is marked corrupt if:
        1. Net transfers to the funcionario are positive.
        2. Their actual allocation exceeds the default allocation by more than 0.1.
    - If a citizen is audited, store corruption status in `player.corruption_punishment`.
    - If the funcionario is audited, check if at least one citizen is corrupt and store result.

    :param group: An oTree group object.
    :return: Dictionary with corruption assessment for each citizen.
    """

    # Choose an arbitrary player to extract group info
    p1 = group.get_player_by_id(1)

    group_data = {
        'segment': p1.participant.segment,
        'round': p1.round_number,
        'session_code': p1.session.code,
        'group_id': p1.group_id
    }

    # Retrieve corruption transaction details
    corruption_info = check_corruption(group_data)
    print(f'corruption_info: {corruption_info}')  # Debugging info

    # Store corruption results separately
    corruption_results = {}
    any_citizen_corrupt = False  # Track if any citizen is corrupt

    for player in group.get_players():
        if player.id_in_group != 4:  # Skip funcionario (player 4)

            # Get corruption values for this player
            citizen_data = corruption_info.get(player.id_in_group, {'transfers_from_citizen_to_officer': 0, 'transfers_from_officer_to_citizen': 0})

            # Determine if the player is corrupt
            citizen_bribery = (
                citizen_data['transfers_from_citizen_to_officer'] 
                - citizen_data['transfers_from_officer_to_citizen'] > 0
            )
            officer_retribution = (abs(player.actual_allocation - player.group.default_allocation) > 0.1)
            corrupt = citizen_bribery and officer_retribution

            # Store in a separate results dictionary
            corruption_results[player.id_in_group] = {'corrupt': corrupt}

            # Track if at least one citizen is corrupt
            if corrupt:
                any_citizen_corrupt = True

            # If player is audited, store corruption status in player.corruption_punishment
            if player.corruption_audit:
                player.corruption_punishment = corrupt

    # Assign corruption punishment for funcionario (player 4)
    funcionario = group.get_player_by_id(4)
    if funcionario.corruption_audit:
        funcionario.corruption_punishment = any_citizen_corrupt


def set_payoffs(player):
    total_transfers = total_transfers_per_player({
        'session_code': player.session.code,
        'segment': player.participant.segment,
        'round': player.round_number,
        'participant_code': player.participant.code,
    }) 

    private_interaction_payoff = (
        total_transfers.get('transfers_received', 0)
        - total_transfers.get('transfers_given', 0)
    )

    if player.id_in_group != 4:  # If player is citizen
        public_interaction_payoff = (
            player.initial_points
            - (player.field_maybe_none('contribution_points') or 0) 
            + player.actual_allocation
        ) * (1 - player.timeout_penalty)
    else:  # If player is Officer
        public_interaction_payoff = player.initial_points * (1 - player.timeout_penalty)

    player.payoff = (
        (public_interaction_payoff + private_interaction_payoff) 
        * (1 - (player.field_maybe_none('corruption_punishment') or 0))
        )
    return public_interaction_payoff, private_interaction_payoff


def insert_history(group):
    for player in group.get_players():
        # Get public and private payoffs
        public_payoff, private_payoff = set_payoffs(player)

        # Retrieve total transfers per player
        total_transfers = total_transfers_per_player({
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'round': player.round_number,
            'participant_code': player.participant.code,
        }) 

        # Determine player's endowment
        history_data = {
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'round': player.round_number,
            'participant_code': player.participant.code,
            'endowment': player.initial_points,
            'contribution': player.field_maybe_none('contribution_points'),
            'public_good_raw_gain': player.actual_allocation if player.id_in_group != 4 else None,
            'public_interaction_payoff': public_payoff,
            'total_transfers_received': total_transfers.get('transfers_received', 0),
            'total_transfers_given': total_transfers.get('transfers_given', 0),
            'private_interaction_payoff': private_payoff,
            'payment': float(player.payoff)
        }
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
        funcionario = next((other for other in others if other.role == "Funcionario"), None) # Extract 'Funcionario'
        other_players = [other for other in others if other.role != "Funcionario"] # Extract citizens

        ordered_others = ([funcionario] if funcionario else []) + other_players # Place 'Funcionario' first

        # Generate direct chat channels
        others_info = [
            {
                "id_in_group": other.id_in_group,
                "role": other.role,
                "channel": f"{player.participant.segment}{player.round_number}{player.group_id}{min(player.id_in_group, other.id_in_group)}{max(player.id_in_group, other.id_in_group)}",
            }
            for other in ordered_others
        ]

        # Generate additional citizen-officer chat channels (for citizens only)
        additional_chats = []
        if player.session.config.get('officer_interactions_public', False) and player.role != "Funcionario":
            other_citizens = [cit for cit in other_players if cit.id_in_group != player.id_in_group]
            additional_chats = [
                {
                    "id_in_group": f"{other_citizen.id_in_group}-officer",
                    "role": f"Chat entre {other_citizen.role} y Funcionario",
                    "channel": f"{player.participant.segment}{player.round_number}{player.group_id}{other_citizen.id_in_group}4",
                }
                for other_citizen in other_citizens
            ]
            print(f'other_citizens: {additional_chats}, I am player: {player.id_in_group}')

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
            officer_interactions_public=player.session.config['officer_interactions_public'],
            additional_channels=additional_chats if player.session.config['officer_interactions_public'] else [],
        )

    @staticmethod
    def js_vars(player): # Sendign the sequential_decision session config to the frontend
        return dict(
            secuential_decision=player.session.config['sequential_decision'],
            officer_interactions_public=player.session.config['officer_interactions_public'],
        )

    @staticmethod
    def live_method(player, data):

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
                'group_id': player.group_id,
                'initiator_code': player.group.get_player_by_id(data['initiatorId']).participant.code,
                'receiver_code': player.group.get_player_by_id(data['receiverId']).participant.code,
                'initiator_id': data['initiatorId'],
                'receiver_id': data['receiverId'],
                'action': data['action'],
                'points': data['value'],
                'initiator_initial_endowment': player.current_points,
                'receiver_initial_endowment': player.group.get_player_by_id(data['receiverId']).current_points,
            }

            transaction_id = insert_row(data=transaction_data, table='transactions') # Save the transaction and get the transaction ID

            status_data = {
                'transaction_id': transaction_id,
                'status': 'Iniciado',
            }
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
            add_balance(data=balance_data)

            status_data = {
                'transaction_id': transaction_id,
                'status': status,
            }
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

            reload = reload_contribution()

            if transactions_data: # If it is not empty
                reload.update({'updateTransactions':True, 'transactions':transactions_data, 'update': True})
                return {player.id_in_group: reload}
            
            return {player.id_in_group: reload}
        
    @staticmethod
    def before_next_page(player, timeout_happened):
        if timeout_happened and player.id_in_group != 4: # Apply timeout penalty only to citizens
            player.timeout_penalty = True 
        
        if player.round_number == C.NUM_ROUNDS: # Ending the last round of the segment, update segment value
            player.participant.segment += 1


class SecondWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group):
        public_good_default_raw_gain(group)


class ResourceAllocation(Page):
    timeout_seconds = 60 * 1.5
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
    

class ThirdWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group):
        store_actual_allocation(group)
        apply_corruption_penalty(group)
        insert_history(group)


class RandomAudit(Page):
    timeout_seconds = 60

    @staticmethod
    def is_displayed(player):
        if player.session.config['random_audits'] == True:
            return player.corruption_audit == True
    
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


page_sequence = [Instructions, FirstWaitPage, Interaction, SecondWaitPage, ResourceAllocation, ThirdWaitPage, RandomAudit]