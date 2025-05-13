from otree.api import *
from sql_utils import create_tables, insert_row, add_balance, get_points, get_action, filter_transactions, filter_history, get_last_transaction_status, total_transfers_per_player, check_corruption
from treatment_config_loader import load_treatments_from_excel
from spanlp.palabrota import Palabrota # type: ignore
from unidecode import unidecode # type: ignore
from random import choices
import random
import math


# Create treatments dictionary
TREATMENTS = load_treatments_from_excel()

# Creates additional tables
create_tables()

class C(BaseConstants):
    NAME_IN_URL = 'interaccion'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 4 # NOTE: change if neccesary (round per treatment * num of treatments)
    CITIZEN_ENDOWMENT = 100 # Defaul initial endowment for citizens
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
    equitative_allocation = models.FloatField() # = total_allocation / 3
    
    # Decision variables: For treatments where Officer decides the allocation
    allocation1 = models.FloatField( # Allocation for Citizen 1
        blank=True, 
        label='¿Cuál es la cantidad de recursos que quieres distribuir al Ciudadano 1?'
    )
    allocation2 = models.FloatField( # Allocation for Citizen 2
        blank=True, 
        label='¿Cuál es la cantidad de recursos que quieres distribuir al Ciudadano 2?'
    )
    allocation3 = models.FloatField( # Allocation for Citizen 3
        blank=True, 
        label='¿Cuál es la cantidad de recursos que quieres distribuir al Ciudadano 3?'
    )

class Player(BasePlayer):
    # Comprehension questions
    comp_q1 = models.IntegerField(
        label="¿Cuántos puntos recibe cada ciudadano al inicio de cada ronda?",
        choices=[
            [1, '50 puntos'], 
            [2, '100 puntos'], # Correct
            [3, '140 puntos'], 
            [4, '0 puntos'],
        ], 
        widget=widgets.RadioSelect
    )
    comp_q2 = models.IntegerField(
        label="¿Cuál es la fórmula para calcular el pago de un ciudadano?",
        choices=[
            [1, 'Se calcula al azar'], 
            [2, 'Contribución total × Multiplicador'], 
            [3, 'Dotación + Contribución + Recursos públicos'], 
            [4, 'Dotación - Contribución + Recursos públicos'], # Correct
        ], 
        widget=widgets.RadioSelect
    )
    comp_q3 = models.IntegerField(
        label="¿Quién decide cómo se distribuyen los recursos públicos generados?",
        choices=[
            [1, 'El funcionario'], # Correct for BL2 y T2 - T7
            [2, 'Los ciudadanos'],
            [3, 'Se reparten por igual'], # Correct for BL1 y T1
            [4, 'Se reparten al azar'],
        ],
        widget=widgets.RadioSelect,
    )
    comp_q4 = models.IntegerField(
        label="¿Los ciudadanos pueden enviar puntos directamente al funcionario?",
        choices=[
            [1, 'Sí'], # Correct for T1 - T7
            [2, 'No'], # Correct for BL1 y BL2
        ], 
        widget=widgets.RadioSelect
    )
    # Only for T6
    comp_q5 = models.IntegerField(
        label="¿Durante cada ronda, cuándo podrás ser auditado?",
        choices=[
            [1, 'Después de que los ciudadanos contribuyen al proyecto del grupo'], 
            [2, 'Después de que el funcionario decide cómo distribuir los recursos públicos totales'],
            [3, 'Antes de la interacción con los participantes'],
            [4, 'En este bloque no hay auditorías'],
        ], 
        widget=widgets.RadioSelect
    )
    
    # Game variables
    initial_points = models.IntegerField() # Initial endowment per round
    current_points = models.IntegerField()
    actual_allocation = models.FloatField() # The actual allocation the citizen receives
    timeout_penalty = models.BooleanField(initial=False) # True when timeout occurs | False if it didn't happen
    corruption_audit = models.BooleanField() # True if player gets audit | False if player will not be audit
    corruption_punishment = models.BooleanField(blank=True) # True if player did corrupt action | False if they didn't
    
    # Decision variable
    contribution_points = models.IntegerField(blank=True)

class Message(ExtraModel):
    """
    Stores messages between players in a group.

    The `name` field indicates the message type:
    - 'Player': written by a participant.
    - 'TransferInfo': system-generated message about a transfer.
    """
    group = models.Link(Group)
    channel = models.CharField(max_length=255)
    sender = models.Link(Player)
    recipient = models.Link(Player)
    text = models.StringField()
    text_unfiltered = models.StringField()
    name = models.StringField(choices=['Player', 'TransferInfo'])


# FUNCTIONS
def creating_session(subsession):
    """
    When session is created:
    - The player's initial points is stored according to the treatment they are playing and their role
    - The player's segment and current points are initialized
    - The group's total points is stored according to the sum of all player's initial points
    - Asing to the `corruption_audit` player variable a boolean value according to the `audit_probability` session config
    """
    
    # Retrieve configuration values
    officer_endowment = subsession.session.config['officer_endowment']
    c1_endowment = subsession.session.config['c1_endowment']
    audit_prob = subsession.session.config['audit_probability']

    subsession.group_randomly(fixed_id_in_group=True)

    for player in subsession.get_players():
        # Initializing participants fields
        player.participant.treatment_round = 1
        player.participant.segment = 1
        player.participant.treatment = player.session.config['treatment_order'][player.participant.segment - 1]
        player.participant.session_payoff = 0
        
        # Initializing points
        player.initial_points = C.CITIZEN_ENDOWMENT if player.id_in_group != 4 else officer_endowment
        player.current_points = player.initial_points

        # Updating variables by treatments
        if TREATMENTS[player.participant.treatment].heterogenous_citizens and player.id_in_group == 1:
            player.initial_points = c1_endowment
        if TREATMENTS[player.participant.treatment].random_multiplier:
            player.group.multiplier = random.choice([1.5, 2.5])
        else:
            player.group.multiplier = player.session.config['multiplier']
        if TREATMENTS[player.participant.treatment].random_audits:
            player.corruption_audit = choices([True, False], weights=[audit_prob, 1 - audit_prob])[0]
            print(f'{player.role} will be audit in round {player.round_number}: {player.corruption_audit}')
        
        # Print first treatment to play
        if subsession.round_number == 1 and player == subsession.get_players()[0]:
            print(f'Treatment playing: {player.participant.treatment}')
        
        player.group.total_initial_points += player.initial_points # Update total points per group


# TODO: convertir a método de Message y actualizar cuando se llama esta función
def to_dict(msg: Message):
    return dict(channel=msg.channel, sender=msg.sender.id_in_group, recipient=msg.recipient.id_in_group, text=msg.text, name=msg.name)


# TODO: Cambiar public_good_default_raw_gain por public_good_default_gross_gain
def public_good_default_raw_gain(group):
    """
    Get the equitative resources distribution for each citizen per group, then stores 
    the value in the `equitative_allocation` group variable.
    
    The formula used is: `(total_contribution * multiplier) / 3`
    """
    
    players = [p for p in group.get_players() if p.id_in_group != 4] # Exclude player with id 4 (P.O.)
    group.total_contribution = sum(p.field_maybe_none('contribution_points') or 0 for p in players)
    group.total_allocation = group.total_contribution * group.multiplier
    group.equitative_allocation = round(group.total_allocation / (C.PLAYERS_PER_GROUP - 1), 1) # Round to 1 decimal


def store_actual_allocation(group):
    """
    Get the allocation the officer decided for each citizen and verifies if has a 
    valid value (in case there was a timeout and the values the officer wrote weren't 
    right).

    - If the total allocation don't sum the total public resources, the function 
    asings the default allocation to all citizens
    - If there is at least one missing, the function asigns the remaining public 
    resources between the citizens that don't have an allocation
    
    This funtion should be executed only in treatments when the Public Officer decides 
    how to distribute the public resources between the citizens.
    """
    
    allocations = [group.field_maybe_none('allocation1'), group.field_maybe_none('allocation2'), group.field_maybe_none('allocation3')]
    players = [p for p in group.get_players() if p.id_in_group != 4] # Get only the citizens
    
    # Count total allocation and missing allocations
    missing_indices = [i for i, value in enumerate(allocations) if value is None]
    total_allocated = sum(value for value in allocations if value is not None)

    # If all three values exist but do NOT sum to total_allocation
    if len(missing_indices) == 0 and ((total_allocated - group.total_allocation) > 0.1):
        print(f"Incorrect total allocation! Given: {total_allocated}, Expected: {group.total_allocation}")
        for other in players:
            other.actual_allocation = group.equitative_allocation
        return # Exit early after correcting values

    # Handling Missing Values
    total_remaining = group.total_allocation - total_allocated
    
    if len(missing_indices) == 3:
        # If all 3 are missing, distribute equally
        allocation_value = group.equitative_allocation
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
    Determine if citizens engaged in corrupt transactions and applies punishment if necessary.
    
    - Citizens (players 1, 2, 3) are flagged if they receive/give transfers to the officer.
    - A citizen is considered corrupt if:
        1. Net transfers to the officer are positive (they gave more than what they received).
        2. Their actual allocation exceeds the equitative allocation by more than 0.1 points.
    - If a citizen is also audited, store corruption status in `player.corruption_punishment`.
    - If the officer is audited, check if at least one citizen is corrupt and store result.

    This funtion should be executed only in treatment 6, when there are random audits and 
    punishment for corruption behavior.
    """

    # Choose an arbitrary player to extract group info
    p1 = group.get_player_by_id(1)

    group_data = {
        'segment': p1.participant.segment,
        'round': p1.participant.treatment_round,
        'session_code': p1.session.code,
        'group_id': p1.group_id
    }

    # Retrieve corruption transaction details
    corruption_info = check_corruption(group_data)
    print(f'corruption_info: {corruption_info}')  # Debugging info

    # Store corruption results separately
    corruption_results = {}
    any_citizen_corrupt = False  # Track if any citizen is corrupt

    # Validate if corruption took place for citizens
    for player in group.get_players():
        if player.id_in_group != 4:  # Skip officer (player 4)

            # Get corruption values for this player
            citizen_data = corruption_info.get(player.id_in_group, {'transfers_from_citizen_to_officer': 0, 'transfers_from_officer_to_citizen': 0})

            # Determine if the player is corrupt
            citizen_bribery = (
                citizen_data['transfers_from_citizen_to_officer'] 
                - citizen_data['transfers_from_officer_to_citizen'] > 0
            )
            officer_retribution = ((player.actual_allocation - player.group.equitative_allocation) > 0.1)
            corrupt = citizen_bribery and officer_retribution

            # Store in a separate results dictionary
            corruption_results[player.id_in_group] = {'corrupt': corrupt}

            # Track if at least one citizen is corrupt
            if corrupt:
                any_citizen_corrupt = True

            # If player is audited, store corruption status in player.corruption_punishment
            if player.corruption_audit:
                player.corruption_punishment = corrupt

    # Validate if corruption took place for officers
    funcionario = group.get_player_by_id(4) # TODO: cambiar a inglés
    if funcionario.corruption_audit:
        funcionario.corruption_punishment = any_citizen_corrupt


# NOTE: revision code desde aquí
def set_payoffs(player):
    """
    Set the player's payoffs, which is the sum of the `public_interaction_payoff` and 
    the `private_interaction_payoff`.
    - `private_interaction_payoff`: Is the total transfers given minus the total transfers 
    given
    - `public_interaction_payoff`: For the citizens, is the initial endowment minus their 
    contribution to the public project plus the actual allocation they received. If they 
    made a timeout in the contribution page, they get 0 public payoff. For the public officer, 
    is only initial endowment. If they made a timeout in the allocation page (if applicable), 
    they get 0 public payoff.
    - If they are also playing the audit treatment (T6), and get punished for corruption 
    behavior, the receive 0 total payoff.

    :return Public interaction payoff: The actual public payoff, with the timeout punishment applied.
    :return Private interaction payoff: The actual private payoff, with the timeout punishment applied.
    """
    
    total_transfers = total_transfers_per_player({
        'session_code': player.session.code,
        'segment': player.participant.segment,
        'round': player.participant.treatment_round,
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

    # Get the total payoff at the end of the segment
    player.participant.session_payoff += player.payoff

    return public_interaction_payoff, private_interaction_payoff


def insert_history(group):
    """
    Inserts a new history row in the history table.
    """
    for player in group.get_players():
        # Get public and private payoffs
        public_payoff, private_payoff = set_payoffs(player)

        # Retrieve total transfers per player
        total_transfers = total_transfers_per_player({
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'round': player.participant.treatment_round,
            'participant_code': player.participant.code,
        }) 

        # Determine player's endowment
        history_data = {
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'round': player.participant.treatment_round,
            'participant_code': player.participant.code,
            'endowment': player.initial_points,
            'contribution': player.field_maybe_none('contribution_points'),
            'public_good_raw_gain': player.actual_allocation if player.id_in_group != 4 else None,
            'public_interaction_payoff': public_payoff,
            'total_transfers_received': total_transfers.get('transfers_received', 0),
            'total_transfers_given': total_transfers.get('transfers_given', 0),
            'private_interaction_payoff': private_payoff,
            'payment': float(player.payoff),
            'timeout_penalty': player.timeout_penalty,
            'corruption_punishment': player.field_maybe_none('corruption_punishment') if player.field_maybe_none('corruption_punishment') is not None else False,
        }
        insert_row(data=history_data, table='history')
    

# PAGES
class Instructions(Page):
    form_model = 'player'
    form_fields = ['comp_q1', 'comp_q2']

    @staticmethod
    def is_displayed(player):
        return player.participant.treatment_round == 1
    
    def error_message(player, values):
        solutions = dict(
            comp_q1=2,  # 100 puntos
            comp_q2=4,  # Dotación - Contribución + Recursos públicos
        )

        errors = {}
        for field, correct in solutions.items():
            if values[field] != correct:
                errors[field] = 'Respuesta incorrecta.'

        if errors:
            return errors
    

class FirstWaitPage(WaitPage):
    pass


class Interaction(Page):
    # timeout_seconds = 60 * 3
    form_model = 'player'

    @staticmethod
    def get_form_fields(player):
        if player.role != C.OFFICER_ROLE: # Display formfield `contribution_points` only to citizens
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
                "channel": f"{player.participant.segment}{player.participant.treatment_round}{player.group_id}{min(player.id_in_group, other.id_in_group)}{max(player.id_in_group, other.id_in_group)}",
            }
            for other in ordered_others
        ]

        # Generate additional citizen-officer chat channels (for citizens only)
        additional_chats = []
        if (TREATMENTS[player.participant.treatment].officer_interactions_public) == False and (player.role != "Funcionario"):
            other_citizens = [cit for cit in other_players if cit.id_in_group != player.id_in_group]
            additional_chats = [
                {
                    "id_in_group": f"{other_citizen.id_in_group}",
                    "role": f"Chat entre {other_citizen.role} y Funcionario",
                    "channel": f"{player.participant.segment}{player.participant.treatment_round}{player.group_id}{other_citizen.id_in_group}4",
                }
                for other_citizen in other_citizens
            ]
            print(f'other_citizens: {additional_chats}, I am player: {player.id_in_group}')

        history = filter_history({
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'participant_code': player.participant.code,
        })

        # Instructions variables
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
            # Interaction variables
            others=others_info,
            history=history,
            private_interaction=TREATMENTS[player.participant.treatment].private_interaction,
            officer_interactions_public=TREATMENTS[player.participant.treatment].officer_interactions_public,
            chat_only_officer=player.session.config['chat_only_officer'],
            additional_channels=additional_chats if TREATMENTS[player.participant.treatment].officer_interactions_public else [],
            # Instructions variables
            num_treatments=num_treatments,
            num_rounds=num_rounds,
            tot_num_rounds=tot_num_rounds,
            tot_session_time=tot_session_time,
            time_unit=time_unit,
        )

    @staticmethod
    def js_vars(player): # Sendign the sequential_decision session config to the frontend
        return dict(
            secuential_decision=player.session.config['sequential_decision'],
            officer_interactions_public=TREATMENTS[player.participant.treatment].officer_interactions_public,
            player_role=player.role,
            my_id=player.id_in_group,
            other_ids=[p.id_in_group for p in player.get_others_in_group()]
        )

    @staticmethod
    def live_method(player, data):

        def handle_contribution(contribution_points):
            """
            Validate and process contribution points.

            :param contribution_points: The points the citizen contributed to the public project.
            :return: Return a dictionary with two arguments when the points are valid: `contributionPointsValid`, a Boolean that indicates the points are valid, and `contributionPoints`, which stores the valid points the citizen decided to contribute to the public project.
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
            Handle reloading the page if the player has already contributed

            :return: Returns a dictionary with three arguments when the player has contributed: `update', which indicates that the player has reloaded the page, `contributionPointsReload', which indicates that the player has already contributed to the project, and `contributionPoints', which indicates the points the player has sent. If the player has no contribution, then the return value is an empty dictionary.
            """
            contribution_points = player.field_maybe_none('contribution_points')
            if player.role != C.OFFICER_ROLE and contribution_points:
                return dict(update=True, contributionPointsReload=True, contributionPoints=contribution_points)
            return {}
        
        def new_transaction():
            """
            Log a new transaction in the transactions table and its status in the status table.
            Activates when the initiator clicks "offer" or "request".

            :return Transaction ID: 
            """
            transaction_data = {
                'session_code': player.session.code,
                'segment': player.participant.segment,
                'round': player.participant.treatment_round,
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

            # Save the transaction and get the transaction ID
            transaction_id = insert_row(data=transaction_data, table='transactions')

            status_data = {
                'transaction_id': transaction_id,
                'status': 'Iniciado',
            }
            insert_row(data=status_data, table='status')

            return transaction_id

        def closing_transaction(status, transaction_id):
            """
            Log the clausure of a transaction in the status table and update the current points in transactions table.
            Activates when the receiver clicks "yes" or "no", or the initiator cancels the transaction.

            :param status: The latest transaction's status (acepted, declined or canceled)
            :param transaction_id: The ID of the transaction
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
        group = player.group
        my_id = player.id_in_group
        initiator_id = data.get('initiatorId')
        receiver_id = data.get('receiverId')
        value = data.get('value')
        action = data.get('action')

        # Contribution to the shared project
        if data_type == 'contributionPoints':
            return {my_id: handle_contribution(value)}
        
        # Initialize transaction between participants (offer or request)
        elif data_type == 'initiatingTransaction':
            transaction_id = new_transaction()

            print(f'action: {action}')

            channel = f'{min(initiator_id, receiver_id)}{max(initiator_id, receiver_id)}'
            action_label = 'ofreció' if action == 'Ofrece' else 'solicitó'
            unit_label = 'punto' if value == 1 else 'puntos'
            
            msg = Message.create(
                group=group,
                sender=group.get_player_by_id(initiator_id),
                recipient=group.get_player_by_id(receiver_id),
                channel=channel,
                text=f'{player.role} {action_label} {value} {unit_label}.',
                name='TransferInfo',
            )

            if 'Ofrece' in action:
                if value <= player.current_points:
                    return {
                        initiator_id: {
                            'offerPoints': True, 
                            'initiator': True, 
                            'receiver': False, 
                            'offerValue': value, 
                            'myId': initiator_id, 
                            'otherId': receiver_id, 
                            'transactionId':transaction_id,
                            'chat': [to_dict(msg)], # Chat variable
                        },
                        receiver_id: {
                            'offerPoints': True, 
                            'initiator': False, 
                            'receiver': True, 
                            'offerValue': value, 
                            'myId': receiver_id, 
                            'otherId': initiator_id, 
                            'transactionId': transaction_id,
                            'chat': [to_dict(msg)], # Chat variable

                        },
                    }
                else:
                    return {
                        initiator_id: {
                            'offerPoints': False, 
                            'error': "No puedes ofrecer más puntos de los que tienes disponibles."
                        }
                    }
            
            elif 'Solicita' in action:
                if value <= group.total_initial_points:
                    return {
                            initiator_id: {
                                'requestPoints': True, 
                                'initiator': True, 
                                'receiver': False, 
                                'requestValue': value, 
                                'myId': initiator_id, 
                                'otherId': receiver_id, 
                                'transactionId': transaction_id,
                                'chat': [to_dict(msg)], # Chat variable
                            },
                            receiver_id: {
                                'requestPoints': True, 
                                'initiator': False, 
                                'receiver': True, 
                                'requestValue': value, 
                                'myId': receiver_id, 
                                'otherId': initiator_id, 
                                'transactionId': transaction_id,
                                'chat': [to_dict(msg)], # Chat variable
                            },
                        }
                else:
                    return {
                        initiator_id: {
                            'requestPoints': False, 
                            'initiator': True
                        }
                    } 
        
        # Close transaction between participants (accept or cancel)
        elif data_type == 'closingTransaction':
            status = data['status']
            transaction_id = data['transactionId']

            initiator = group.get_player_by_id(initiator_id)
            receiver = group.get_player_by_id(receiver_id)

            points = get_points(transaction_id)
            action = get_action(transaction_id)

            print(f'initiator: {initiator}')
            print(f'receiver: {receiver}')
            print(f'status: {status}')
            print(f'transaction_id: {transaction_id}')

            closing_transaction(status, transaction_id)

            channel = f'{min(initiator_id, receiver_id)}{max(initiator_id, receiver_id)}'
            action_label = 'oferta' if action == 'Ofrece' else 'solicitud'
            if status == 'Cancelado':
                status_label = 'canceló'
            elif status == 'Rechazado':
                status_label = 'rechazó'
            else:
                status_label = 'aceptó'
            
            msg = Message.create(
                group=group,
                sender=group.get_player_by_id(initiator_id),
                recipient=group.get_player_by_id(receiver_id),
                channel=channel,
                text=f'{player.role} {status_label} la {action_label}.',
                name='TransferInfo',
            )

            if status == 'Cancelado':
                return {
                    initiator_id: {'cancelAction': True, 'otherId': receiver_id, 'chat': [to_dict(msg)]},
                    receiver_id: {'cancelAction': True, 'otherId': initiator_id, 'chat': [to_dict(msg)]},
                }    

            elif status == 'Rechazado':
                filter_transactions_i = filter_transactions({
                    'participant_code': initiator.participant.code,
                    'round': initiator.participant.treatment_round,
                    'segment': initiator.participant.segment,
                    'session_code': initiator.session.code,
                })
                filter_transactions_r = filter_transactions({
                    'participant_code': receiver.participant.code,
                    'round': receiver.participant.treatment_round,
                    'segment': receiver.participant.segment,
                    'session_code': receiver.session.code,
                })

                return {
                    initiator_id: {
                        'update': True, 
                        'updateTransactions': True, 
                        'transactions': filter_transactions_i, 
                        'otherId': receiver_id, 
                        'reload': False,
                        'chat': [to_dict(msg)],
                    },
                    receiver_id: {
                        'update': True, 
                        'updateTransactions': True, 
                        'transactions': filter_transactions_r,
                        'otherId': initiator_id, 
                        'reload': False,
                        'chat': [to_dict(msg)],
                    },
                }
            
            elif status == 'Aceptado':
                # Apply the transaction
                if action == 'Ofrece':
                    initiator.current_points -= points
                    receiver.current_points += points
                else: # Solicita
                    if points <= receiver.current_points:
                        initiator.current_points += points
                        receiver.current_points -= points
                    else:
                        return {receiver: {
                            'requestPoints':False, 
                            'initiator': False
                        }
                    }

                filter_transactions_i = filter_transactions({
                    'participant_code': initiator.participant.code,
                    'round': initiator.participant.treatment_round,
                    'segment': initiator.participant.segment,
                    'session_code': initiator.session.code,
                })
                filter_transactions_r = filter_transactions({
                    'participant_code': receiver.participant.code,
                    'round': receiver.participant.treatment_round,
                    'segment': receiver.participant.segment,
                    'session_code': receiver.session.code,
                })
                return {
                    receiver_id: {
                        'updateTransactions': True, 
                        'transactions': filter_transactions_r, 
                        'otherId': initiator_id, 
                        'reload': False, 
                        'update': True,
                        'chat': [to_dict(msg)],
                    },
                    initiator_id: {
                        'updateTransactions': True, 
                        'transactions': filter_transactions_i, 
                        'otherId': receiver_id, 
                        'reload': False, 
                        'update':True,
                        'chat': [to_dict(msg)],
                    }
                }
        
        # When player reloads their page
        elif data_type == 'reloadPage':
            last_transaction = get_last_transaction_status(
                participant_code=player.participant.code,
                treatment_round=player.participant.treatment_round,
                segment=player.participant.segment,
                session_code=player.session.code
            )

            # Fetch the filtered transactions
            transactions_data = filter_transactions({
                'participant_code': player.participant.code,
                'round': player.participant.treatment_round,
                'segment': player.participant.segment,
                'session_code': player.session.code,
            })

            reload = reload_contribution()

            # If the last transaction is still in process, send offer/request buttons again and filtered transactions
            if last_transaction:
                transaction_id = last_transaction['transactionId']
                initiator_id = last_transaction['initiatorId']
                receiver_id = last_transaction['receiverId']
                action = last_transaction['action']
                value = last_transaction['value']

                # Construct common response data
                response_data = {
                    'updateTransactions': True,
                    'transactions': transactions_data,  # Sending filtered transactions
                    'update': True,
                    'transactionId': transaction_id
                }

                if action == 'Ofrece':
                    reload.update(dict(
                            offerPoints=True,
                            initiator=player.id_in_group == initiator_id,
                            receiver=player.id_in_group == receiver_id,
                            offerValue=value,
                            myId=player.id_in_group,
                            otherId=receiver_id if player.id_in_group == initiator_id else initiator_id,
                            **response_data  # Merging transaction data
                        ))
                    return {
                        player.id_in_group: reload,
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
                    reload.update(dict(
                            requestPoints=True,
                            initiator=player.id_in_group == initiator_id,
                            receiver=player.id_in_group == receiver_id,
                            requestValue=value,
                            myId=player.id_in_group,
                            otherId=receiver_id if player.id_in_group == initiator_id else initiator_id,
                            **response_data  # Merging transaction data
                        ))
                    return {
                        player.id_in_group: reload,
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

            if transactions_data: # If it is not empty
                reload.update({
                    'updateTransactions':True, 
                    'transactions':transactions_data, 
                    'update': True
                })
                return {player.id_in_group: reload}
            
            return {player.id_in_group: reload}
        
        elif 'text' in data and 'recipient' in data:
            recipient_id = data['recipient']

            channel = f'{min(my_id, recipient_id)}{max(my_id, recipient_id)}'

            print(f'recipient_id: {recipient_id}')
            print(f'channel: {channel}')
            print(f'group.get_player_by_id(my_id): {group.get_player_by_id(my_id)}')
            print(f'group.get_player_by_id(recipient_id): {group.get_player_by_id(recipient_id)}')
            
            text_unfiltered = data['text']
            ascii_text = unidecode(text_unfiltered)

            palabrota = Palabrota()

            if palabrota.contains_palabrota(ascii_text):
                # Split both texts into words
                original_words = text_unfiltered.split()
                ascii_words = ascii_text.split()

                censored_output = []

                for original_word, ascii_word in zip(original_words, ascii_words):
                    if palabrota.contains_palabrota(ascii_word):
                        # Replace the original word with censored version (same length, using symbols)
                        censored_output.append(''.join(['*' for _ in original_word]))
                    else:
                        censored_output.append(original_word)

                text_filtered = ' '.join(censored_output)
            else:
                text_filtered = text_unfiltered

            msg = Message.create(
                group=group,
                sender=group.get_player_by_id(my_id),
                recipient=group.get_player_by_id(recipient_id),
                channel=channel,
                text=text_filtered,
                text_unfiltered=text_unfiltered,
                name='Player',
            )

            return {
                my_id: [to_dict(msg)],
                recipient_id: [to_dict(msg)]
            }
        
        return {
            my_id: [
                to_dict(msg)
                for msg in Message.filter(group=group)
                if msg.sender and msg.recipient and my_id in [msg.sender.id_in_group, msg.recipient.id_in_group]
            ]
        }


    @staticmethod
    def before_next_page(player, timeout_happened):
        if timeout_happened and player.id_in_group != 4: # Apply timeout penalty only to citizens
            player.timeout_penalty = True 


class SecondWaitPage(WaitPage):
    template_name = 'public_goods/MyWaitPage.html'
    body_text = 'Esperando a que los demás participantes tomen sus decisiones...'

    @staticmethod
    def vars_for_template(player):
        history = filter_history({
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'participant_code': player.participant.code,
        })

        return dict(
            segment=player.participant.segment,
            history=history,
            private_interaction=TREATMENTS[player.participant.treatment].private_interaction,
            random_audits=TREATMENTS[player.participant.treatment].random_audits,
        )
    
    @staticmethod
    def after_all_players_arrive(group):
        public_good_default_raw_gain(group)


class ResourceAllocation(Page):
    # timeout_seconds = 60 * 1.5
    form_model = 'group'
    form_fields = ['allocation1', 'allocation2', 'allocation3']

    @staticmethod
    def is_displayed(player):
        if TREATMENTS[player.participant.treatment].resource_allocation == True:
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
        }) 

        # Instructions variables
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
            # Page varibles
            history=history,
            private_interaction=TREATMENTS[player.participant.treatment].private_interaction,
            # Instructions variables
            num_treatments=num_treatments,
            num_rounds=num_rounds,
            tot_num_rounds=tot_num_rounds,
            tot_session_time=tot_session_time,
            time_unit=time_unit,
        )
    
    @staticmethod
    def live_method(player, data):
        print(f'Received data: {data}')  # Debugging output

        # Ensure 'data' is valid
        if not isinstance(data, dict) or 'value' not in data:
            print("Error: 'value' key missing in received data")
            return  # Prevent further execution

        calculator_history_data = {
            'session_code': player.session.code,
            'segment': getattr(player.participant, 'segment', 'Unknown'),  # Prevent attribute error
            'round': player.participant.treatment_round,
            'participant_code': player.participant.code,
            'operation': data.get('value', ''),  # Ensure this exists
        }

        try:
            insert_row(data=calculator_history_data, table='calculator_history')
        except Exception as e:
            print(f"Error inserting calc history: {e}")  # Log error
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.timeout_penalty = True if timeout_happened else False
    

class ThirdWaitPage(WaitPage):
    template_name = 'public_goods/MyWaitPage.html'
    body_text = 'Esperando a que los demás participantes tomen sus decisiones...'

    @staticmethod
    def vars_for_template(player):
        history = filter_history({
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'participant_code': player.participant.code,
        })

        return dict(
            segment=player.participant.segment,
            history=history,
            private_interaction=TREATMENTS[player.participant.treatment].private_interaction,
            random_audits=TREATMENTS[player.participant.treatment].random_audits,
        )
    
    @staticmethod
    def after_all_players_arrive(group):
        store_actual_allocation(group)
        insert_history(group)
        # Get the treatment info from one of the group's players
        player = group.get_players()[0]
        if TREATMENTS[player.participant.treatment].random_audits:
            apply_corruption_penalty(group)


class Results(Page):
    # timeout_seconds = 20

    @staticmethod
    def vars_for_template(player):
        history = filter_history({
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'participant_code': player.participant.code,
        })

        return dict(
            segment=player.participant.segment,
            history=history,
            private_interaction=TREATMENTS[player.participant.treatment].private_interaction,
            random_audits=TREATMENTS[player.participant.treatment].random_audits,
            corruption_audit=player.field_maybe_none('corruption_audit'),
        )
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        """
        Ending the last round of the segment, update segment value
        """
        if (player.participant.treatment_round * player.participant.segment) == C.NUM_ROUNDS:
            return
        if (player.participant.treatment_round % player.session.config['num_rounds']) == 0:
            player.participant.segment += 1
            player.participant.treatment_round = 1
            player.participant.treatment = player.session.config['treatment_order'][player.participant.segment - 1]
        else:
            player.participant.treatment_round += 1
        
        print(f"treatment_round: {player.participant.treatment_round}")


page_sequence = [Instructions, FirstWaitPage, Interaction, SecondWaitPage, ResourceAllocation, ThirdWaitPage, Results]