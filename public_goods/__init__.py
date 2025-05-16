from otree.api import * 
import json
import math
import random
from random import choices
from unidecode import unidecode  # type: ignore
from spanlp.palabrota import Palabrota  # type: ignore

# Local utilities
from sql_utils import (
    create_tables,
    insert_row,
    add_balance,
    get_points,
    get_action,
    filter_transactions,
    filter_history,
    get_last_transaction_status,
    total_transfers_per_player,
    check_corruption,
)
from treatment_config_loader import load_treatments_from_excel


# Initialize treatment configuration
TREATMENTS = load_treatments_from_excel()

# Create additional database tables (e.g., transactions, status)
create_tables()


class C(BaseConstants):
    NAME_IN_URL = 'interaccion'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 3 # NOTE: change if neccesary (round per treatment * num of treatments)
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
    # Comprehension questions displayed at first treatment
    comp_q1 = models.IntegerField(
        label="¿Cuántos puntos recibe el funcionario al inicio de cada ronda?",
        choices=[
            [1, '50 puntos'],
            [2, '100 puntos'],
            [3, '140 puntos'], # Correct 
            [4, '0 puntos'],
        ], 
        widget=widgets.RadioSelect
    )
    comp_q2 = models.IntegerField(
        label="¿Quién decide cuánto se contribuye al proyecto del grupo?",
        choices=[
            [1, 'La computadora'],
            [2, 'Cada ciudadano'], # Correct
            [3, 'El funcionario'],
            [4, 'Todos los participantes'],
        ], 
        widget=widgets.RadioSelect
    )
    comp_q3 = models.IntegerField(
        label="¿Qué sucede si un jugador no toma una decisión a tiempo?",
        choices=[
            [1, 'No pasa nada'],
            [2, 'Se elige un monto aleatorio entre 0 y 100'],
            [3, 'No recibe puntos en la ronda'],
            [4, 'No recibe puntos en la interacción pública de la ronda'], # Correct
        ],
        widget=widgets.RadioSelect,
    )
    comp_q4 = models.IntegerField(
        label="¿Qué factores afectan el pago final de un ciudadano?",
        choices=[
            [1, 'Su rol'],
            [2, 'Su dotación, su contribución y los recursos públicos recibidos'], # Correct
            [3, 'Solo la decisión del funcionario'],
            [4, 'Solo la contribución de los demás ciudadanos'],
        ], 
        widget=widgets.RadioSelect
    )

    # Comprehension question for BL1
    comp_bl1 = models.IntegerField(
        label="¿Cuál es la fórmula para calcular el pago de un ciudadano?",
        choices=[
            [1, 'Contribución total × Multiplicador'],
            [2, 'Dotación + Contribución + ( Recursos públicos / 3 )'],
            [3, 'Dotación - Contribución + ( Recursos públicos / 3 )'], # Correct
            [4, 'Se calcula al azar'],
        ], 
        widget=widgets.RadioSelect
    )

    # Comprehension question for BL2
    comp_bl2 = models.IntegerField(
        label="¿Quién decide cómo se distribuyen los recursos públicos generados?",
        choices=[
            [1, 'El funcionario'], # Correct
            [2, 'Los ciudadanos'], 
            [3, 'Se reparten por igual'], 
            [4, 'Se reparten al azar'],
        ], 
        widget=widgets.RadioSelect
    )

    # Comprehension question for T1
    comp_t1 = models.IntegerField(
        label="¿Qué tipo de interacción ocurre además de la pública?",
        choices=[
            [1, 'Votación'],
            [2, 'Interacción privada'], # Correct
            [3, 'Interacción controlada'], 
            [4, 'No hay otra interacción'],
        ], 
        widget=widgets.RadioSelect
    )

    # Comprehension question for T2
    comp_t2 = models.IntegerField(
        label="¿Los ciudadanos pueden enviar puntos directamente al funcionario?",
        choices=[
            [1, 'Sí'], # Correct
            [2, 'No'],
        ], 
        widget=widgets.RadioSelect
    )

    # Comprehension question for T3
    comp_t3 = models.IntegerField(
        label="¿Cuántos puntos recibe el ciudadano 1 al inicio de cada ronda?",
        choices=[
            [1, '50 puntos'],
            [2, '100 puntos'],
            [3, '120 puntos'], # Correct
            [4, '140 puntos'],
        ], 
        widget=widgets.RadioSelect
    )

    # Comprehension question for T4
    comp_t4 = models.IntegerField(
        label="¿Cuál es el valor del multiplicador?",
        choices=[
            [1, '0,8'],
            [2, '2,0'],
            [3, '2,5'],
            [4, 'Se determina al azar'], # Correct
        ], 
        widget=widgets.RadioSelect
    )

    # Comprehension question for T6
    comp_t6 = models.IntegerField(
        label="¿Cuándo podrás ser auditado?",
        choices=[
            [1, 'Después de que los ciudadanos contribuyen al proyecto del grupo'], 
            [2, 'Después de que el funcionario decide cómo distribuir los recursos públicos totales'], # Correct
            [3, 'Antes de la interacción privada'],
            [4, 'En este bloque no hay auditorías'],
        ], 
        widget=widgets.RadioSelect
    )

    # Comprehension question for T7
    comp_t7 = models.IntegerField(
        label="¿Podrás ver la interacción privada de los otros ciudadanos con el funcionario?",
        choices=[
            [1, 'Sí'], # Correct
            [2, 'No'],
        ], 
        widget=widgets.RadioSelect
    )

    # Error fields
    num_failed_attempts = models.IntegerField(initial=0)
    errors_per_attempt = models.LongStringField()
    # Stores a JSON string representing a list of dicts.
    # Each dict corresponds to one failed comprehension attempt and contains
    # question names as keys and the incorrect answers the participant gave as values.
    # Example:
    # [
    #     {"comp_q1": 1, "comp_q4": 3}, # First failed attempt
    #     {"comp_q4": 1},               # Second failed attempt
    # ]
    
    # Game variables
    initial_points = models.IntegerField() # Endowment received at the start of each round
    current_points = models.IntegerField() # Current point balance after actions
    actual_allocation = models.FloatField() # Amount the citizen actually received
    timeout_penalty = models.BooleanField(initial=False) # True if the player timed out during a decision
    corruption_audit = models.BooleanField() # True if the player is selected for audit
    corruption_punishment = models.BooleanField(blank=True) # True if punished for corruption
    
    # Decision variable
    contribution_points = models.IntegerField(blank=True)


class Message(ExtraModel):
    """
    Stores messages between players in a group.

    The `name` field indicates the message type:
    - 'Player': message written by a participant.
    - 'TransferInfo': system-generated message when a transfer is made.
    """
    group = models.Link(Group)
    channel = models.CharField(max_length=255)
    sender = models.Link(Player)
    recipient = models.Link(Player)
    text = models.StringField()
    text_unfiltered = models.StringField()
    name = models.StringField(choices=['Player', 'TransferInfo'])
    
    def to_dict(self):
        """
        Serializes the message instance to a dictionary format.

        Returns:
            dict: Contains channel name, sender and recipient IDs, text, and message type.
        """
        return {
            'channel': self.channel,
            'sender': self.sender.id_in_group,
            'recipient': self.recipient.id_in_group,
            'text': self.text,
            'name': self.name,
        }


# FUNCTIONS
def creating_session(subsession):
    """
    Initializes key variables when the session is created:
    - Assigns players' initial points based on their role and treatment
    - Sets participant fields like segment, treatment round, and session payoff
    - Randomly assigns audits based on session config
    - Sets the group's total initial points
    - Sets the group's multiplier (fixed or random)
    """
    
    # Retrieve session-level configuration
    officer_endowment = subsession.session.config['officer_endowment']
    c1_endowment = subsession.session.config['c1_endowment']
    audit_prob = subsession.session.config['audit_probability']

    subsession.group_randomly(fixed_id_in_group=True)

    for player in subsession.get_players():
        # Initialize participant-level fields
        player.participant.treatment_round = 1
        player.participant.segment = 1
        player.participant.treatment = player.session.config['treatment_order'][player.participant.segment - 1]
        player.participant.session_payoff = 0
        
        # Assign initial points based on role
        player.initial_points = C.CITIZEN_ENDOWMENT if player.role != C.OFFICER_ROLE else officer_endowment

        # Heterogeneous endowment for citizen 1 (if applicable)
        if TREATMENTS[player.participant.treatment].heterogenous_citizens and player.id_in_group == 1:
            player.initial_points = c1_endowment

        player.current_points = player.initial_points

        # Determine if player will be audited (if audits are randomized)
        if TREATMENTS[player.participant.treatment].random_audits:
            player.corruption_audit = choices([True, False], weights=[audit_prob, 1 - audit_prob])[0]
            print(f'{player.role} will be audit in round {player.round_number}: {player.corruption_audit}')
        
        # Print current treatment
        if subsession.round_number == 1 and player == subsession.get_players()[0]:
            print(f'Treatment playing: {player.participant.treatment}')
        
        # Initialize group-level fields
        player.group.total_initial_points += player.initial_points
        player.group.multiplier = player.session.config['multiplier']


def public_good_default_gross_gain(group):
    """
    Computes the equitable allocation of public resources for each citizen in the group.
    
    This function:
    - Excludes the public official
    - Calculates the total contribution and total allocation
    - Stores the equal share in `group.equitative_allocation`
    
    Formula:
        (total_contribution × multiplier) / number_of_citizens
    """
    
    players = [p for p in group.get_players() if p.role != C.OFFICER_ROLE] # Exclude the official
    group.total_contribution = sum(p.field_maybe_none('contribution_points') or 0 for p in players)
    group.total_allocation = group.total_contribution * group.multiplier
    group.equitative_allocation = round(group.total_allocation / (C.PLAYERS_PER_GROUP - 1), 1)


def store_actual_allocation(group):
    """
    Validates and applies the allocation of public resources decided by the Public Officer.

    This function:
    - Checks if the officer's allocations are valid (i.e., they sum to the total public resources).
    - If all values are present but incorrect, assigns the default equal allocation to all citizens.
    - If one or more allocations are missing (e.g., due to timeout), distributes the remaining
      resources among the citizens with missing values.

    This function should be executed **only** in treatments where the Public Officer chooses how
    to distribute public resources.
    """
    
    # Retrieve officer-defined allocations and filter only citizens
    allocations = [
        group.field_maybe_none('allocation1'), 
        group.field_maybe_none('allocation2'), 
        group.field_maybe_none('allocation3'),
    ]
    
    citizens = [p for p in group.get_players() if p.role != C.OFFICER_ROLE]
    
    # Identify which values are missing
    missing_indices = [i for i, value in enumerate(allocations) if value is None]
    total_allocated = sum(value for value in allocations if value is not None)
    total_expected = group.total_allocation

    # Case 1: All allocations exist, but sum is incorrect → fallback to default
    if len(missing_indices) == 0 and abs(total_allocated - total_expected) > 0.1:
        print(f"Officer allocations incorrect! Given: {total_allocated}, Expected: {total_expected}")
        for citizen in citizens:
            citizen.actual_allocation = group.equitative_allocation
        return

    # Calculate remaining allocation if there are missing values
    total_remaining = total_expected - total_allocated
    
    # Case 2: All 3 allocations are missing → assign equal default
    if len(missing_indices) == 3:
        for citizen in citizens:
            citizen.actual_allocation = group.equitative_allocation

    # Case 3: Two allocations are missing → divide remaining equally
    elif len(missing_indices) == 2:
        allocation_value = round(total_remaining / 2, 1)
        for i, citizen in enumerate(citizens):
            citizen.actual_allocation = (
                allocation_value if i in missing_indices else allocations[i]
            )

    # Case 4: One allocation is missing → assign the remaining to that one
    elif len(missing_indices) == 1:
        for i, citizen in enumerate(citizens):
            citizen.actual_allocation = (
                total_remaining if i == missing_indices[0] else allocations[i]
            )

    # Case 5: No allocations are missing and the sum is valid → assign as is
    else:
        for i, citizen in enumerate(citizens):
            citizen.actual_allocation = allocations[i]


def apply_corruption_penalty(group):
    """
    Determines if citizens engaged in corrupt transactions and applies penalties accordingly.

    A citizen is flagged as corrupt if:
    1. They gave more to the officer than they received.
    2. Their actual allocation exceeds the equitative allocation by more than 0.1 points.

    Punishments are applied as follows:
    - If a corrupt citizen is audited, `player.corruption_punishment` is set to True.
    - If the officer is audited and at least one citizen is corrupt, the officer is punished.

    This function should only be executed in Treatment 6, where audits and penalties apply.
    """

    # Use player 1 to access shared group/participant info
    p1 = group.get_player_by_id(1)
    group_data = {
        'segment': p1.participant.segment,
        'round': p1.participant.treatment_round,
        'session_code': p1.session.code,
        'group_id': p1.group_id
    }

    # Retrieve corruption transaction data from external checker
    corruption_info = check_corruption(group_data)
    print(f'Corruption info: {corruption_info}') # Debug print

    # Store corruption results separately
    any_citizen_corrupt = False # Track whether at least one citizen is corrupt

    for player in group.get_players():
        if player.role == C.OFFICER_ROLE:  # Skip the officer for now
            continue

        # Extract citizen transfer data
        data = corruption_info.get(player.id_in_group, {
            'transfers_from_citizen_to_officer': 0, 
            'transfers_from_officer_to_citizen': 0
        })

        # Check both bribery and retribution conditions
        gave_more_than_received = (
            data['transfers_from_citizen_to_officer'] > data['transfers_from_officer_to_citizen']
        )
        got_more_than_equal_share = (
            player.actual_allocation - player.group.equitative_allocation > 0.1
        )

        is_corrupt = gave_more_than_received and got_more_than_equal_share

        # If audited and corrupt, apply punishment
        if player.corruption_audit:
            player.corruption_punishment = is_corrupt

        if is_corrupt:
            any_citizen_corrupt = True

    # Officer punishment: only if audited and any citizen was corrupt
    officer = group.get_player_by_id(4)
    if officer.corruption_audit:
        officer.corruption_punishment = any_citizen_corrupt


# NOTE: revision code desde aquí
def set_payoffs(player):
    """
    Computes and sets the player's total payoff based on public and private interactions.

    Payoff structure:
    - `private_interaction_payoff`: Total transfers received minus total transfers given.
    - `public_interaction_payoff`:
        - For citizens: endowment - contribution + allocation.
        - For officers: endowment only.
        - If the player timed out in the relevant stage, this is 0.
    - If the player is punished for corruption (in T6), total payoff is set to 0.

    Returns:
        tuple: (public_interaction_payoff, private_interaction_payoff)
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

    timeout = player.timeout_penalty
    
    if player.role != C.OFFICER_ROLE: # Citizen
        contribution = player.field_maybe_none('contribution_points') or 0
        public_interaction_payoff = (
            player.initial_points - contribution + player.actual_allocation
        ) * (1 - timeout)
    else: # Officer
        public_interaction_payoff = player.initial_points * (1 - timeout)

    corruption_penalty = player.field_maybe_none('corruption_punishment') or 0
    player.payoff = (public_interaction_payoff + private_interaction_payoff) * (1 - corruption_penalty)

    # Accumulate in session-level payoff
    player.participant.session_payoff += player.payoff

    return public_interaction_payoff, private_interaction_payoff


def handle_contribution(player, contribution_points):
    """
    Validates and processes a citizen's contribution to the public project.

    Parameters:
        player (Player): The player making the contribution.
        contribution_points (int): The number of points the citizen intends to contribute.

    Returns:
        dict: A dictionary with:
            - 'contributionPointsValid' (bool): Whether the contribution is valid.
            - 'contributionPoints' (int, optional): The valid contribution amount, if applicable.
            - 'error' (str, optional): An error message if the contribution is invalid.
    """
    
    if player.role == C.OFFICER_ROLE:
        return {}
    
    if not isinstance(contribution_points, int) or math.isnan(contribution_points):
        return {
            'contributionPointsValid': False, 
            'error': "Por favor, ingresa un número válido."
        }
    
    if contribution_points < 0:
        return {
            'contributionPointsValid': False, 
            'error': "No puedes ingresar una cantidad negativa."
        }
    
    if contribution_points > player.current_points:
        return {
            'contributionPointsValid': False, 
            'error': "No puedes contribuir más puntos de los que tienes disponibles."
        }
    
    # Valid contribution
    player.current_points -= contribution_points
    player.contribution_points = contribution_points
    
    return {
        'contributionPointsValid': True, 
        'contributionPoints': contribution_points
    }


def reload_contribution(player):
    """
    Return a reload response if the citizen has already submitted a contribution.

    Returns:
        dict: 
        - If the player is a citizen and has already contributed:
            - update (bool): True
            - contributionPointsReload (bool): True
            - contributionPoints (int): The contributed amount
        - Otherwise: An empty dictionary
    """

    contribution_points = player.field_maybe_none('contribution_points')
    if player.role != C.OFFICER_ROLE and contribution_points:
        return {
            'update': True, 
            'contributionPointsReload': True, 
            'contributionPoints': contribution_points,
        }
    
    return {}


def new_transaction(player, data):
    """
    Create a new transaction record and log its initial status.

    Triggered when the initiator clicks "offer" or "request".

    Args:
        player (Player): The player initiating the transaction.
        data (dict): Contains initiatorId, receiverId, action, value.

    Returns:
        int: The ID of the newly created transaction.
    """

    group = player.group

    transaction_data = {
        'session_code': player.session.code,
        'segment': player.participant.segment,
        'round': player.participant.treatment_round,
        'group_id': player.group_id,
        'initiator_code': group.get_player_by_id(data['initiatorId']).participant.code,
        'receiver_code': group.get_player_by_id(data['receiverId']).participant.code,
        'initiator_id': data['initiatorId'],
        'receiver_id': data['receiverId'],
        'action': data['action'],
        'points': data['value'],
        'initiator_initial_endowment': player.current_points,
        'receiver_initial_endowment': group.get_player_by_id(data['receiverId']).current_points,
    }

    transaction_id = insert_row(data=transaction_data, table='transactions')

    insert_row(data={
        'transaction_id': transaction_id,
        'status': 'Iniciado',
    }, table='status')

    return transaction_id


def closing_transaction(player, data, status, transaction_id):
    """
    Finalizes a transaction by saving its closing status and current balances.

    Triggered when the receiver accepts/rejects the transaction,
    or when the initiator cancels it.

    Args:
        player (Player): The player triggering the closure.
        data (dict): Must include 'initiatorId' and 'receiverId'.
        status (str): One of 'Aceptado', 'Rechazado', or 'Cancelado'.
        transaction_id (int): The transaction being closed.
    """
    
    initiator = player.group.get_player_by_id(data['initiatorId'])
    receiver = player.group.get_player_by_id(data['receiverId'])

    add_balance(data={
        'transaction_id': transaction_id,
        'initiator_balance': initiator.current_points,
        'receiver_balance': receiver.current_points,
    })

    insert_row(data={
        'transaction_id': transaction_id,
        'status': status,
    }, table='status')


def insert_history(group):
    """
    Inserts a new row in the history table for each player in the group,
    recording their endowment, contributions, transfers, payoffs, and penalties.
    """

    for player in group.get_players():
        public_payoff, private_payoff = set_payoffs(player)

        transfers = total_transfers_per_player({
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'round': player.participant.treatment_round,
            'participant_code': player.participant.code,
        }) 

        history_data = {
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'round': player.participant.treatment_round,
            'participant_code': player.participant.code,
            'endowment': player.initial_points,
            'contribution': player.field_maybe_none('contribution_points'),
            'public_good_gross_gain': player.actual_allocation if player.id_in_group != 4 else None,
            'public_interaction_payoff': public_payoff,
            'total_transfers_received': transfers.get('transfers_received', 0),
            'total_transfers_given': transfers.get('transfers_given', 0),
            'private_interaction_payoff': private_payoff,
            'payment': float(player.payoff),
            'timeout_penalty': player.timeout_penalty,
            'corruption_punishment': player.field_maybe_none('corruption_punishment') or False,
        }

        insert_row(data=history_data, table='history')


# PAGES
class Instructions(Page):
    form_model = 'player'

    @staticmethod
    def is_displayed(player):
        return player.participant.treatment_round == 1

    @staticmethod
    def get_form_fields(player):
        fields = []

        if player.participant.segment == 1:
            # General comprehension questions
            fields += ['comp_q1', 'comp_q2', 'comp_q3', 'comp_q4']

        # Treatment-specific question
        treatment_fields = {
            'BL1': 'comp_bl1',
            'BL2': 'comp_bl2',
            'T1': 'comp_t1',
            'T2': 'comp_t2',
            'T3': 'comp_t3',
            'T4': 'comp_t4',
            'T6': 'comp_t6',
            'T7': 'comp_t7',
        }
        treatment = player.participant.treatment
        if treatment in treatment_fields:
            fields.append(treatment_fields[treatment])
        
        return fields
    
    @staticmethod
    def error_message(player, values):
        solutions = {
            'comp_q1': 3, 'comp_q2': 2, 'comp_q3': 4, 'comp_q4': 2,
            'comp_bl1': 3, 'comp_bl2': 1, 'comp_t1': 2, 'comp_t2': 1,
            'comp_t3': 3, 'comp_t4': 4, 'comp_t6': 2, 'comp_t7': 1,
        }

        # Identify incorrect answers
        incorrect = {
            field: answer
            for field, answer in values.items()
            if field in solutions and answer != solutions[field]
        }

        if incorrect:
            player.num_failed_attempts += 1

            # Load and append failed attempts
            previous = json.loads(player.field_maybe_none('errors_per_attempt') or '[]')
            previous.append(incorrect)
            player.errors_per_attempt = json.dumps(previous)

            print(f'Number of failed attempts: {player.num_failed_attempts}')
            print(f'Errors per attempt: {player.errors_per_attempt}')

            return {field: 'Respuesta incorrecta.' for field in incorrect}


class FirstWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group):
        player = group.get_players()[0]
        if TREATMENTS[player.participant.treatment].random_multiplier:
            group.multiplier = random.choice([1.5, 2.5])


class Interaction(Page):
    timeout_seconds = 60 * 3
    form_model = 'player'

    @staticmethod
    def get_form_fields(player):
        return ['contribution_points'] if player.role != C.OFFICER_ROLE else []

    @staticmethod
    def vars_for_template(player):
        # Identify other players in group
        others = player.get_others_in_group()
        officer = next((p for p in others if p.role == "Funcionario"), None)
        citizens = [p for p in others if p.role != "Funcionario"]

        # Order: officer first (if exists), then other players
        ordered_others = ([officer] if officer else []) + citizens

        # Generate direct chat channels
        others_info = [
            {
                "id_in_group": other.id_in_group,
                "role": other.role,
                "channel": (
                    f"{player.participant.segment}"
                    f"{player.participant.treatment_round}"
                    f"{player.group_id}"
                    f"{min(player.id_in_group, other.id_in_group)}"
                    f"{max(player.id_in_group, other.id_in_group)}"
                ),
            }
            for other in ordered_others
        ]

        # Generate additional citizen-officer channels (only shown to citizens)
        additional_chats = []
        treatment_cfg = TREATMENTS[player.participant.treatment]
        if treatment_cfg.officer_interactions_public and player.role != "Funcionario":
            other_citizens = [c for c in citizens if c.id_in_group != player.id_in_group]
            additional_chats = [
                {
                    "id_in_group": f"{other_citizen.id_in_group}",
                    "role": f"Chat entre {other_citizen.role} y Funcionario",
                    "channel": (
                        f"{player.participant.segment}"
                        f"{player.participant.treatment_round}"
                        f"{player.group_id}"
                        f"{other_citizen.id_in_group}4"
                    ),
                }
                for other_citizen in other_citizens
            ]
            print(f'other_citizens: {additional_chats}, I am player: {player.id_in_group}')

        history = filter_history({
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'participant_code': player.participant.code,
        })

        # Instruction timing variables
        num_treatments = len(player.session.config['treatment_order'])
        num_rounds = player.session.config['num_rounds']
        tot_num_rounds = num_treatments * num_rounds

        avg_round_time = 4 # minutes per round
        total_minutes = tot_num_rounds * avg_round_time

        if total_minutes < 60:
            tot_session_time = total_minutes
            time_unit = 'minutos'
        else:
            tot_session_time = round(total_minutes / 60, 1)
            time_unit = 'horas'

        return {
            # Interaction variables
            'others': others_info,
            'history': history,
            'private_interaction': treatment_cfg.private_interaction,
            'officer_interactions_public': treatment_cfg.officer_interactions_public,
            'chat_only_officer': player.session.config['chat_only_officer'],
            'additional_channels': additional_chats if treatment_cfg.officer_interactions_public else [],
            
            # Instructions variables
            'num_treatments': num_treatments,
            'num_rounds': num_rounds,
            'tot_num_rounds': tot_num_rounds,
            'tot_session_time': tot_session_time,
            'time_unit': time_unit,
        }

    @staticmethod
    def js_vars(player):
        return {
            'secuential_decision': player.session.config['sequential_decision'],
            'private_interaction_duration': player.session.config['private_interaction_duration'],
            'public_interaction_activation': player.session.config['public_interaction_activation'],
            'officer_interactions_public': TREATMENTS[player.participant.treatment].officer_interactions_public,
            'player_role': player.role,
            'my_id': player.id_in_group,
            'other_ids': [p.id_in_group for p in player.get_others_in_group()],
        }

    @staticmethod
    def live_method(player, data):
        data_type = data.get('type')
        group = player.group
        my_id = player.id_in_group
        initiator_id = data.get('initiatorId')
        receiver_id = data.get('receiverId')
        value = data.get('value')
        action = data.get('action')

        # Contribution to the shared project
        if data_type == 'contributionPoints':
            return {my_id: handle_contribution(player, value)}
        
        # Initialize transaction between participants (offer or request)
        elif data_type == 'initiatingTransaction':
            transaction_id = new_transaction(player, data)

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
                            'chat': [msg.to_dict()], # Chat variable
                        },
                        receiver_id: {
                            'offerPoints': True, 
                            'initiator': False, 
                            'receiver': True, 
                            'offerValue': value, 
                            'myId': receiver_id, 
                            'otherId': initiator_id, 
                            'transactionId': transaction_id,
                            'chat': [msg.to_dict()], # Chat variable

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
                                'chat': [msg.to_dict()], # Chat variable
                            },
                            receiver_id: {
                                'requestPoints': True, 
                                'initiator': False, 
                                'receiver': True, 
                                'requestValue': value, 
                                'myId': receiver_id, 
                                'otherId': initiator_id, 
                                'transactionId': transaction_id,
                                'chat': [msg.to_dict()], # Chat variable
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
                closing_transaction(player, data, status, transaction_id)
                return {
                    initiator_id: {'cancelAction': True, 'otherId': receiver_id, 'chat': [msg.to_dict()]},
                    receiver_id: {'cancelAction': True, 'otherId': initiator_id, 'chat': [msg.to_dict()]},
                }    

            elif status == 'Rechazado':
                closing_transaction(player, data, status, transaction_id)

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
                        'chat': [msg.to_dict()],
                    },
                    receiver_id: {
                        'update': True, 
                        'updateTransactions': True, 
                        'transactions': filter_transactions_r,
                        'otherId': initiator_id, 
                        'reload': False,
                        'chat': [msg.to_dict()],
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
                closing_transaction(player, data, status, transaction_id)

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
                print(f'filter_transactions_i: {filter_transactions_i}')
                print(f'filter_transactions_r: {filter_transactions_r}')

                return {
                    receiver_id: {
                        'updateTransactions': True, 
                        'transactions': filter_transactions_r, 
                        'otherId': initiator_id, 
                        'reload': False, 
                        'update': True,
                        'chat': [msg.to_dict()],
                    },
                    initiator_id: {
                        'updateTransactions': True, 
                        'transactions': filter_transactions_i, 
                        'otherId': receiver_id, 
                        'reload': False, 
                        'update':True,
                        'chat': [msg.to_dict()],
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

            reload = reload_contribution(player)

            # If the last transaction is still in progress, resend offer/request with updated transactions
            if last_transaction:
                transaction_id = last_transaction['transactionId']
                initiator_id = last_transaction['initiatorId']
                receiver_id = last_transaction['receiverId']
                action = last_transaction['action']
                value = last_transaction['value']

                # Common fields to return to both participants
                response_data = {
                    'updateTransactions': True,
                    'transactions': transactions_data,
                    'update': True,
                    'transactionId': transaction_id,
                }

                is_initiator = player.id_in_group == initiator_id
                is_receiver = player.id_in_group == receiver_id
                other_id = receiver_id if is_initiator else initiator_id

                if action == 'Ofrece':
                    reload.update({
                            'offerPoints': True,
                            'initiator': is_initiator,
                            'receiver': is_receiver,
                            'offerValue': value,
                            'myId': player.id_in_group,
                            'otherId': other_id,
                            **response_data
                        })
                    return {
                        player.id_in_group: reload,
                        receiver_id: {
                            'offerPoints': True,
                            'initiator': False,
                            'receiver': True,
                            'offerValue': value,
                            'myId': receiver_id,
                            'otherId': initiator_id,
                            **response_data
                        }
                    }
                elif action == 'Solicita':
                    reload.update({
                            'requestPoints': True,
                            'initiator': is_initiator,
                            'receiver': is_receiver,
                            'requestValue': value,
                            'myId': player.id_in_group,
                            'otherId': other_id,
                            **response_data
                        })
                    return {
                        player.id_in_group: reload,
                        receiver_id: {
                            'requestPoints': True,
                            'initiator': False,
                            'receiver': True,
                            'requestValue': value,
                            'myId': receiver_id,
                            'otherId': initiator_id,
                            **response_data
                        }
                    }

            # If there are transactions, just send an update with those
            if transactions_data:
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
                my_id: [msg.to_dict()],
                recipient_id: [msg.to_dict()]
            }
        
        # Return all messages where the player is either the sender or recipient
        messages = [
            msg.to_dict()
            for msg in Message.filter(group=group)
            if msg.sender and msg.recipient
            and my_id in [msg.sender.id_in_group, msg.recipient.id_in_group]
        ]
        
        return {my_id: messages}

    @staticmethod
    def before_next_page(player, timeout_happened):
        if timeout_happened and player.role != C.OFFICER_ROLE:
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

        treatment_cfg = TREATMENTS[player.participant.treatment]

        return {
            'segment': player.participant.segment,
            'history': history,
            'private_interaction': treatment_cfg.private_interaction,
            'random_audits': treatment_cfg.random_audits,
        }
    
    @staticmethod
    def after_all_players_arrive(group):
        public_good_default_gross_gain(group)


class ResourceAllocation(Page):
    timeout_seconds = 60 * 1.5
    form_model = 'group'
    form_fields = ['allocation1', 'allocation2', 'allocation3']

    @staticmethod
    def is_displayed(player):
        return (
            TREATMENTS[player.participant.treatment].resource_allocation
            and player.id_in_group == 4
        )

    @staticmethod
    def js_vars(player):
        return {'total_allocation': player.group.total_allocation}

    @staticmethod
    def vars_for_template(player):
        history = filter_history({
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'participant_code': player.participant.code,
        }) 

        # Instruction timing variables
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

        return {
            'history': history,
            'private_interaction': TREATMENTS[player.participant.treatment].private_interaction,
            'num_treatments': num_treatments,
            'num_rounds': num_rounds,
            'tot_num_rounds': tot_num_rounds,
            'tot_session_time': tot_session_time,
            'time_unit': time_unit,
        }
    
    @staticmethod
    def live_method(player, data):
        print(f'Received data: {data}') # Debugging

        if not isinstance(data, dict) or 'value' not in data:
            print("Error: 'value' key missing in received data")
            return

        try:
            insert_row(data={
                'session_code': player.session.code,
                'segment': player.participant.segment,
                'round': player.participant.treatment_round,
                'participant_code': player.participant.code,
                'operation': data.get('value', ''),
            }, table='calculator_history')
        except Exception as e:
            print(f"Error inserting calculator history: {e}")
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.timeout_penalty = timeout_happened
    

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

        return {
            'segment': player.participant.segment,
            'history': history,
            'private_interaction': TREATMENTS[player.participant.treatment].private_interaction,
            'random_audits': TREATMENTS[player.participant.treatment].random_audits,
        }
    
    @staticmethod
    def after_all_players_arrive(group):
        store_actual_allocation(group)
        insert_history(group)
        # Get the treatment info from one of the group's players
        player = group.get_players()[0]
        if TREATMENTS[player.participant.treatment].random_audits:
            apply_corruption_penalty(group)


class Results(Page):
    timeout_seconds = 20

    @staticmethod
    def vars_for_template(player):
        history = filter_history({
            'session_code': player.session.code,
            'segment': player.participant.segment,
            'participant_code': player.participant.code,
        })

        treatment_cfg = TREATMENTS[player.participant.treatment]

        return {
            'segment': player.participant.segment,
            'history': history,
            'private_interaction': treatment_cfg.private_interaction,
            'random_audits': treatment_cfg.random_audits,
            'corruption_audit': player.field_maybe_none('corruption_audit'),
        }
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        round_number = player.participant.treatment_round
        segment = player.participant.segment
        total_rounds = C.NUM_ROUNDS
        rounds_per_segment = player.session.config['num_rounds']

        # If we're at the final round of the final segment, do nothing
        if round_number * segment == total_rounds:
            return
        
        # If at the end of a segment, increment segment and reset treatment round
        if round_number % rounds_per_segment == 0:
            player.participant.segment += 1
            player.participant.treatment_round = 1
            player.participant.treatment = player.session.config['treatment_order'][player.participant.segment - 1]
        else:
            player.participant.treatment_round += 1
        
        print(f"Next treatment round: {player.participant.treatment_round}")


page_sequence = [
    Instructions,           # General instructions and comprehension check
    FirstWaitPage,          # Wait for all to finish instructions
    Interaction,            # Public contribution and private interaction
    SecondWaitPage,         # Wait before allocation
    ResourceAllocation,     # Officer allocates (if treatment)
    ThirdWaitPage,          # Apply audits (if treatment) or penalties
    Results                 # Display outcomes
]