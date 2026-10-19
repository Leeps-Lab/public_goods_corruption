from otree.api import *  # type: ignore
import json
import math
import random
from random import choices

# Local utilities
from sql_utils import (
    create_tables,
    insert_row,
    open_transaction,
    close_transaction,
    get_transaction,
    filter_transactions,
    filter_history,
    get_last_transaction_status,
    get_open_transactions,
    start_interaction,
    record_contribution_time,
    end_interaction,
    check_corruption,
    register_session,
    history_display_row,
)
from treatment_config_loader import load_treatments_from_excel


# Initialize treatment configuration
TREATMENTS = load_treatments_from_excel()

# Create additional database tables (e.g., transactions, status)
create_tables()


class C(BaseConstants):
    NAME_IN_URL = 'interaccion'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 12 # NOTE: Change if neccesary (round per treatment * num of treatments)
    CITIZEN_ENDOWMENT = 100 # Defaul initial endowment for citizens
    CITIZEN1_ROLE = 'Ciudadano 1'
    CITIZEN2_ROLE = 'Ciudadano 2'
    CITIZEN3_ROLE = 'Ciudadano 3'
    OFFICER_ROLE = 'Funcionario'
    OFFICER_ID = 4 # id_in_group of the officer
    COMPREHENSION_ANSWERS = {
        'comp_q1': 4, 'comp_q2': 2, 'comp_q3': 4, 'comp_q4': 2,
        'comp_bl1': 3, 'comp_bl2': 1, 'comp_t1': 2, 'comp_t2': 1,
        'comp_t3': 4, 'comp_t4': 4, 'comp_t6': 2, 'comp_t7': 1,
        'comp_private_payoff': 1,
    }


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
        label='¿Cuál es la cantidad de recursos que quieres asignar al Ciudadano 1?'
    )
    allocation2 = models.FloatField( # Allocation for Citizen 2
        blank=True, 
        label='¿Cuál es la cantidad de recursos que quieres asignar al Ciudadano 2?'
    )
    allocation3 = models.FloatField( # Allocation for Citizen 3
        blank=True, 
        label='¿Cuál es la cantidad de recursos que quieres asignar al Ciudadano 3?'
    )


class Player(BasePlayer):
    # Comprehension questions displayed at first treatment
    comp_q1 = models.IntegerField(
        label="¿Cuántos puntos recibe el funcionario al inicio de cada ronda?",
        choices=[
            [1, '50 puntos'],
            [2, '100 puntos'],
            [3, '140 puntos'],
            [4, '0 puntos'], # Correct
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
        label="¿Qué sucede si un ciudadano no envía su contribución a tiempo?",
        # Option 3 used to be 'No recibe puntos en la ronda', which is also true in treatments
        # without private interaction (BL1, BL2); replaced by a clearly wrong option. Codes unchanged.
        choices=[
            [1, 'No pasa nada'],
            [2, 'Se elige un monto aleatorio entre 0 y 100'],
            [3, 'Se le asigna la contribución promedio del grupo'],
            [4, 'Su pago de la interacción pública en esa ronda es 0 puntos'], # Correct
        ],
        widget=widgets.RadioSelect,
    )
    comp_q4 = models.IntegerField(
        label="¿Qué factores afectan el pago de un ciudadano en cada ronda?",
        widget=widgets.RadioSelect
    ) # Choices depend on the treatment, see comp_q4_choices()

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
        label="¿Cuál es la dotación inicial del ciudadano 1 en cada ronda?",
        choices=[
            [1, '100 puntos'],
            [2, '120 puntos'],
            [3, '140 puntos'],
            [4, '150 puntos'], # Correct
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

    # Comprehension question for treatments with private interaction (T1, T2, T3, T4, T6, T7)
    comp_private_payoff = models.IntegerField(
        label="Los puntos que envías o recibes en la interacción privada, ¿afectan tu pago final de la ronda?",
        choices=[
            [1, 'Sí, se suman o restan directamente de mi pago total'], # Correct
            [2, 'No, mi pago solo depende de la interacción pública'],
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
    reserved_points = models.IntegerField(initial=0) # current_points minus still-pending Ofrece commitments;
    # this is what new offers are checked against, so a player can never offer more than they can truly cover.
    # Kept in lockstep with current_points on every OTHER balance change (contribution, receiving points,
    # paying an accepted Solicita) so it stays accurate; only settlement of one's own reserved Ofrece
    # leaves it untouched, since that amount was already subtracted from it at initiation time.
    round_transfers_received = models.IntegerField(initial=0) # Total points received via accepted private
    # transactions this round. Tracked live here (instead of re-derived from a separate SQL query at
    # round-end) so set_payoffs()/insert_history() never depend on a fresh database connection succeeding.
    round_transfers_given = models.IntegerField(initial=0) # Total points given via accepted private
    # transactions this round. See round_transfers_received.
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
    - 'SystemInfo': system-generated notice not tied to a transfer (e.g. the
      other player moved on to the next stage).
    """
    group = models.Link(Group)
    channel = models.StringField(max_length=255)
    sender = models.Link(Player)
    recipient = models.Link(Player)
    text = models.StringField()
    text_unfiltered = models.StringField()
    name = models.StringField(choices=['Player', 'TransferInfo', 'SystemInfo'])
    
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
def comp_q4_choices(player):
    """Option 2 (correct) mentions private transfers only in treatments that have them. Codes are the same in all treatments."""
    if TREATMENTS[player.participant.treatment].private_interaction:
        correct = 'Su dotación, su contribución, los recursos públicos recibidos y lo que envía o recibe en la interacción privada'
    else:
        correct = 'Su dotación, su contribución y los recursos públicos recibidos'
    return [
        [1, 'Su rol'],
        [2, correct], # Correct
        [3, 'Solo la decisión del funcionario'],
        [4, 'Solo la contribución de los demás ciudadanos'],
    ]


def creating_session(subsession):
    """
    Initializes key variables when the session is created:
    - Assigns players' initial points based on their role and treatment
    - Sets participant fields like segment, treatment round, and session payoff
    - Randomly assigns audits based on session config
    - Sets the group's total initial points
    - Sets the group's multiplier (fixed)
    """
    if subsession.round_number == 1:
        session = subsession.session
        register_session({
            'session_code': session.code,
            'config_name': session.config['name'],
            'label': session.label,
            'is_demo': session.is_demo,
            'num_participants': session.num_participants,
            'treatment_order': json.dumps(session.config['treatment_order']),
            'rounds_per_treatment': session.config['num_rounds'],
        })
    elif subsession.round_number > 1 and ((subsession.round_number - 1) % subsession.session.config['num_rounds'] == 0):
        subsession.group_randomly(fixed_id_in_group=True)
    else:
        subsession.group_like_round(subsession.round_number - 1)

    # Retrieve session-level configuration
    audit_prob = subsession.session.config['audit_probability']

    for player in subsession.get_players():
        # Initialize participant-level fields
        player.participant.treatment_round = 1
        player.participant.segment = 1
        player.participant.treatment = player.session.config['treatment_order'][player.participant.segment - 1]
        player.participant.session_payoff = 0
        
        # Determine if player will be audited (if audits are randomized)
        if TREATMENTS[player.participant.treatment].random_audits:
            player.corruption_audit = choices([True, False], weights=[audit_prob, 1 - audit_prob])[0]

        # Initialize group-level fields
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
    officer = group.get_player_by_id(C.OFFICER_ID)
    if officer.corruption_audit:
        officer.corruption_punishment = any_citizen_corrupt


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
    
    private_interaction_payoff = (
        player.round_transfers_received - player.round_transfers_given
    )

    timeout = player.timeout_penalty
    
    if player.role != C.OFFICER_ROLE: # Citizen
        if timeout and player.field_maybe_none('contribution_points') is None:
            public_interaction_payoff = 0
        else:
            contribution = player.field_maybe_none('contribution_points') or 0
            public_interaction_payoff = (
                player.initial_points - contribution + player.actual_allocation
            )
    else:
        public_interaction_payoff = player.initial_points * (1 - timeout)

    corruption_penalty = player.field_maybe_none('corruption_punishment') or 0
    player.payoff = (public_interaction_payoff + private_interaction_payoff) * (1 - corruption_penalty)

    # Accumulate in session-level payoff
    player.participant.session_payoff += player.payoff

    return public_interaction_payoff, private_interaction_payoff


def handle_contribution(player, contribution_points):
    """
    Validates and processes a citizen's contribution to the public project, and sends
    a validation message to the frontend.

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

    # Already contributed (e.g. "Enviar puntos" confirmed twice before the first
    # reply arrived): answer with the stored contribution instead of charging again.
    contributed = player.field_maybe_none('contribution_points')
    if contributed is not None:
        return {
            'contributionPointsValid': True,
            'contributionPoints': contributed,
            'reservedPoints': player.reserved_points,
        }

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
    
    if contribution_points > player.reserved_points:
        return {
            'contributionPointsValid': False,
            'error': "No puedes contribuir más puntos de los que tienes disponibles."
        }

    # Valid contribution
    player.current_points -= contribution_points
    player.reserved_points -= contribution_points
    player.contribution_points = contribution_points
    record_contribution_time(interaction_keys(player))

    return {
        'contributionPointsValid': True,
        'contributionPoints': contribution_points,
        'reservedPoints': player.reserved_points,
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
    if player.role != C.OFFICER_ROLE and contribution_points is not None:
        return {
            'update': True, 
            'contributionPointsReload': True, 
            'contributionPoints': contribution_points,
        }
    
    return {}


# TODO: añadir que una transacción es una fila en la tabla de transactions
def round_keys(player):
    """
    Identifiers shared by every game_data row written during this player's
    round, so each row can be joined back to the oTree export (and to the other
    game_data tables) without relying on oTree's own database surviving.
    """

    return {
        'session_code': player.session.code,
        'segment': player.participant.segment,
        'round': player.participant.treatment_round,
        'round_number': player.round_number,
        'treatment': player.participant.treatment,
        'group_id': player.group_id,
        'group_id_in_subsession': player.group.id_in_subsession,
    }


def interaction_keys(player):
    """The columns identifying the player's row in 'game_data.interaction_times'."""

    return {
        **round_keys(player),
        'participant_code': player.participant.code,
        'id_in_group': player.id_in_group,
    }


def create_message(group, sender_id, recipient_id, text, name, text_unfiltered=None, transaction_id=None):
    """
    Create a chat message and mirror it into 'game_data.messages', since oTree's
    Message table is wiped by `otree resetdb`.

    Returns:
        Message: The created oTree message.
    """

    sender = group.get_player_by_id(sender_id)
    recipient = group.get_player_by_id(recipient_id)
    channel = f'{min(sender_id, recipient_id)}{max(sender_id, recipient_id)}'

    msg = Message.create(
        group=group,
        sender=sender,
        recipient=recipient,
        channel=channel,
        text=text,
        text_unfiltered=text_unfiltered,
        name=name,
    )

    insert_row(data={
        **round_keys(sender),
        'channel': channel,
        'sender_code': sender.participant.code,
        'recipient_code': recipient.participant.code,
        'sender_id': sender_id,
        'recipient_id': recipient_id,
        'name': name,
        'text': text,
        'transaction_id': transaction_id,
    }, table='messages')

    return msg


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
        **round_keys(player),
        'initiator_code': group.get_player_by_id(data['initiatorId']).participant.code,
        'receiver_code': group.get_player_by_id(data['receiverId']).participant.code,
        'initiator_id': data['initiatorId'],
        'receiver_id': data['receiverId'],
        'action': data['action'],
        'points': data['value'],
        'initiator_initial_endowment': player.current_points,
        'receiver_initial_endowment': group.get_player_by_id(data['receiverId']).current_points,
    }

    return open_transaction(transaction_data)


def closing_transaction(initiator, receiver, status, transaction_id):
    """
    Saves how a transaction ended, with both players' balances at that moment.

    Args:
        initiator (Player): The player who made the offer/request.
        receiver (Player): The player it was made to.
        status (str): One of 'Aceptado', 'Rechazado', 'Cancelado' or 'Fallido'.
        transaction_id (int): The transaction being closed.
    """

    close_transaction(
        transaction_id,
        status,
        initiator_balance=initiator.current_points,
        receiver_balance=receiver.current_points,
    )


def get_cached_history(player):
    """
    Returns the participant's round-by-round history for the current segment.

    `history` (via filter_history()) is queried identically by five different
    pages every round (Interaction, SecondWaitPage, ResourceAllocation,
    ThirdWaitPage, Results), but the underlying rows only change once per
    round, when insert_history() runs. Caching it in participant.vars — kept
    up to date by insert_history() appending each new round directly — avoids
    re-querying the same unchanged rows from SQL on every page load. The SQL
    table stays the durable source of truth; this is only a per-session cache
    over it, refreshed from SQL if it's ever missing or stale for the segment.
    """

    segment = player.participant.segment
    cache = player.participant.vars.get('history_cache')

    if cache is None or cache.get('segment') != segment:
        rows = filter_history({
            'session_code': player.session.code,
            'segment': segment,
            'participant_code': player.participant.code,
        })
        cache = {'segment': segment, 'rows': rows}
        player.participant.vars['history_cache'] = cache

    return cache['rows']


def insert_history(group):
    """
    Inserts a new row in the history table for each player in the group,
    recording their endowment, contributions, transfers, payoffs, and penalties.
    """

    for player in group.get_players():
        public_payoff, private_payoff = set_payoffs(player)

        history_data = {
            **round_keys(player),
            'participant_code': player.participant.code,
            'id_in_group': player.id_in_group,
            'endowment': player.initial_points,
            'contribution': player.field_maybe_none('contribution_points'),
            'total_public_goods': player.group.total_allocation,
            'public_good_gross_gain': player.actual_allocation if player.id_in_group != C.OFFICER_ID else None,
            'public_interaction_payoff': public_payoff,
            'total_transfers_received': player.round_transfers_received,
            'total_transfers_given': player.round_transfers_given,
            'private_interaction_payoff': private_payoff,
            'payment': float(player.payoff),
            'timeout_penalty': player.timeout_penalty,
            'corruption_punishment': player.field_maybe_none('corruption_punishment') or False,
        }

        # Warm/fetch the cache BEFORE inserting the new row: if the cache is
        # cold, get_cached_history() falls back to SQL, and this round's row
        # must not already be in the database when it does that fallback
        # fetch, or the append below would duplicate it.
        cache = get_cached_history(player)

        insert_row(data=history_data, table='history')

        # Keep the per-participant cache in lockstep with what was just
        # written, so later pages this round don't have to re-query SQL.
        cache.append(history_display_row(history_data))


def fmt_points(value):
    """Formats a number the Spanish way: 1 decimal at most, comma separator (213.3 -> '213,3')."""
    value = round(value, 1)
    text = f'{value:.1f}'.rstrip('0').rstrip('.')
    return text.replace('.', ',')


def fmt_seconds(seconds):
    """Formats a duration in seconds as Spanish text (60 -> '1 minuto', 90 -> '90 segundos')."""
    if seconds % 60 == 0:
        minutes = seconds // 60
        return f'{minutes} minuto' if minutes == 1 else f'{minutes} minutos'
    return f'{seconds} segundos'


def block_changes(prev, curr, cfg, c1_endowment):
    """Plain-language list of the rule differences between two treatment configs (previous block -> this block)."""
    endowment = C.CITIZEN_ENDOWMENT
    multiplier = fmt_points(cfg['multiplier'])
    changes = []

    if curr.private_interaction != prev.private_interaction:
        if curr.private_interaction:
            changes.append(
                'Ahora hay interacción privada: los ciudadanos y el funcionario pueden conversar e intercambiar '
                'puntos en privado. Esos puntos se suman o restan al pago de la ronda.'
            )
        else:
            changes.append(
                'Ya no hay interacción privada: no hay chat ni intercambio de puntos. '
                'Por eso, en este bloque el pago del funcionario es 0 puntos en cada ronda.'
            )

    if curr.resource_allocation != prev.resource_allocation:
        if curr.resource_allocation:
            changes.append(
                'Ahora el funcionario decide cómo repartir los recursos públicos totales entre los tres ciudadanos '
                '(ya no se reparten automáticamente en partes iguales).'
            )
        else:
            changes.append(
                'Ahora los recursos públicos totales se reparten automáticamente en partes iguales entre los tres '
                'ciudadanos (el funcionario ya no decide el reparto).'
            )

    if curr.heterogenous_citizens != prev.heterogenous_citizens:
        if curr.heterogenous_citizens:
            changes.append(
                f'El ciudadano 1 ahora recibe {c1_endowment} puntos al inicio de cada ronda; '
                f'los ciudadanos 2 y 3 siguen recibiendo {endowment}.'
            )
        else:
            changes.append(f'Ahora todos los ciudadanos reciben {endowment} puntos al inicio de cada ronda.')

    if curr.random_multiplier != prev.random_multiplier:
        if curr.random_multiplier:
            changes.append(
                'El multiplicador ahora se sortea en cada ronda: vale 2,5 con probabilidad 2/3 y 1,5 con probabilidad 1/3. '
                'El funcionario ve el valor sorteado; los ciudadanos no lo ven cuando deciden su contribución.'
            )
        else:
            changes.append(f'El multiplicador ahora es fijo: {multiplier} en todas las rondas.')

    if curr.random_audits != prev.random_audits:
        if curr.random_audits:
            changes.append('Ahora hay auditorías al final de cada ronda (ver «Auditorías» en las reglas completas).')
        else:
            changes.append('Ya no hay auditorías.')

    if curr.officer_interactions_public != prev.officer_interactions_public:
        if curr.officer_interactions_public:
            changes.append(
                'Ahora cada ciudadano puede ver, sin poder escribir, el chat y las transferencias entre el funcionario '
                'y los otros dos ciudadanos. Todos los miembros del grupo saben esto.'
            )
        else:
            changes.append('Los chats y transferencias privadas vuelven a ser visibles solo para las dos personas involucradas.')

    return changes


def instructions_vars(player):
    """
    Variables for instructions_body.html. The worked examples are computed here
    (instead of hardcoded in the template) so they always match the session config
    (multiplier, Citizen 1 endowment, audit probability, timing).
    """

    cfg = player.session.config
    treatment = TREATMENTS[player.participant.treatment]
    endowment = C.CITIZEN_ENDOWMENT
    endowments = [cfg['c1_endowment'] if treatment.heterogenous_citizens else endowment, endowment, endowment]

    # T4 draws 1.5 or 2.5 (see FirstWaitPage), so each example uses one of the two values
    if treatment.random_multiplier:
        multipliers = [1.5, 2.5]
    else:
        multipliers = [cfg['multiplier'], cfg['multiplier']]

    def build_example(title, contributions, multiplier, shares, transfers=None):
        """
        One whole-group example: what each member did and what each one earns.
        `transfers` is a list of (sender, receiver, points) with 1-3 = citizens and 4 = officer;
        only used in treatments with private interaction.
        """
        total = sum(contributions) * multiplier
        allocations = [total * s for s in shares]
        transfers = (transfers or []) if treatment.private_interaction else []
        net = {i: 0 for i in range(1, 5)}
        for sender, receiver, points in transfers:
            net[sender] -= points
            net[receiver] += points

        def who(i, to=False):
            name = 'funcionario' if i == 4 else f'ciudadano {i}'
            return f'al {name}' if to else f'el {name}'

        facts = [
            f'El ciudadano 1 contribuye {contributions[0]} puntos, el ciudadano 2 contribuye '
            f'{contributions[1]} y el ciudadano 3 contribuye {contributions[2]}.'
        ]
        if treatment.random_multiplier:
            facts.append(f'En esta ronda, el multiplicador resulta ser {fmt_points(multiplier)}.')
        if treatment.resource_allocation:
            if len(set(shares)) == 1:
                facts.append(f'El funcionario asigna {fmt_points(allocations[0])} puntos a cada ciudadano.')
            else:
                facts.append(
                    f'El funcionario asigna {fmt_points(allocations[0])} puntos al ciudadano 1, '
                    f'{fmt_points(allocations[1])} al ciudadano 2 y {fmt_points(allocations[2])} al ciudadano 3.'
                )
        if treatment.private_interaction:
            if transfers:
                moves = [f'{who(a)} envía {p} puntos {who(b, to=True)}' for a, b, p in transfers]
                facts.append('En la interacción privada, ' + ' y '.join(moves) + '.')
            else:
                facts.append('En la interacción privada no se intercambian puntos.')

        def signed(value):
            if value < 0:
                return f'−{fmt_points(-value)}'
            return f'+{fmt_points(value)}' if value > 0 else '0'

        rows = []
        for i in range(3):
            pay = endowments[i] - contributions[i] + allocations[i] + net[i + 1]
            rows.append({
                'role': f'Ciudadano {i + 1}',
                'endowment': endowments[i],
                'contribution': f'−{contributions[i]}',
                'allocation': f'+{fmt_points(allocations[i])}',
                'private': signed(net[i + 1]),
                'pay': fmt_points(pay),
            })
        if treatment.private_interaction:
            rows.append({
                'role': 'Funcionario',
                'endowment': 0,
                'contribution': '—',
                'allocation': '—',
                'private': signed(net[4]),
                'pay': fmt_points(net[4]),
            })

        return {
            'title': title,
            'facts': facts,
            'total_expr': f'({" + ".join(str(c) for c in contributions)}) × {fmt_points(multiplier)}',
            'total': fmt_points(total),
            'rows': rows,
        }

    # Transfers sit in the equal-split example on purpose: no example pairs a transfer to the
    # officer with a larger allocation, so the examples don't hint at what "works"
    equal = [1 / 3] * 3
    # Only citizen -> officer: an officer -> citizen transfer read as a model of what officers do.
    transfers_a = [(1, 4, 20)]
    if treatment.resource_allocation:
        examples = [
            build_example('Ejemplo A', [20, 50, 80], multipliers[0], equal, transfers_a),
            build_example('Ejemplo B', [20, 50, 80], multipliers[1], [0.3, 0.5, 0.2]),
        ]
    else:
        examples = [
            build_example('Ejemplo A', [20, 50, 80], multipliers[0], equal, transfers_a),
            build_example('Ejemplo B', [100, 100, 100], multipliers[1], equal),
        ]

    sequential = cfg['sequential_decision'] and treatment.private_interaction

    # From block 2 on, list only what differs from the previous block, so participants
    # don't have to reread rules they already know (e.g. T1 -> T2 share most of them)
    segment = player.participant.segment
    changes = []
    if segment > 1:
        prev = TREATMENTS[cfg['treatment_order'][segment - 2]]
        changes = block_changes(prev, treatment, cfg, endowments[0])

    return {
        'ins': {
            'first_block': segment == 1,
            'changes': changes,
            'is_officer': player.role == C.OFFICER_ROLE,
            'private': treatment.private_interaction,
            'allocation': treatment.resource_allocation,
            'heterogeneous': treatment.heterogenous_citizens,
            'random_multiplier': treatment.random_multiplier,
            'audits': treatment.random_audits,
            'public_chats': treatment.officer_interactions_public,
            'chat_only_officer': cfg['chat_only_officer'],
            'sequential': sequential,
            'endowment': endowment,
            'c1_endowment': endowments[0],
            'multiplier': fmt_points(cfg['multiplier']),
            'audit_pct': fmt_points(cfg['audit_probability'] * 100),
            'stage_time': fmt_seconds(Interaction.timeout_seconds),
            'contribution_delay': fmt_seconds(cfg['public_interaction_activation']),
            'allocation_time': fmt_seconds(ResourceAllocation.timeout_seconds),
            'examples': examples,
        },
        # Used by the general instructions shown from the Interaction / ResourceAllocation pages
        'participation_fee_text': 'S/ {:.2f}'.format(cfg['participation_fee']).replace('.', ','),
    }


# LIVE INTERACTION
# Interaction.live_method() hands each message from the page to one of these.
# Each returns {id_in_group: data} for the players whose screens must update;
# the keys of `data` are read by liveRecv() in Interaction.html.

def round_transactions(player):
    """The player's finished transactions this round, as shown in their transactions table."""

    return filter_transactions({
        'participant_code': player.participant.code,
        'round': player.participant.treatment_round,
        'segment': player.participant.segment,
        'session_code': player.session.code,
    })


def pending_transaction_view(action, value, transaction_id, my_id, other_id, is_initiator):
    """
    What one side needs to show an offer/request still waiting for an answer:
    a "waiting" box with a cancel button for the initiator, or accept/reject
    buttons for the receiver.
    """

    kind = 'offer' if action == 'Ofrece' else 'request'
    return {
        f'{kind}Points': True,
        'initiator': is_initiator,
        'receiver': not is_initiator,
        f'{kind}Value': value,
        'myId': my_id,
        'otherId': other_id,
        'transactionId': transaction_id,
    }


def refused_transaction_view(action, other_id, error):
    """What the initiator needs when their offer/request is refused: the error, and their inputs enabled again."""

    kind = 'offer' if action == 'Ofrece' else 'request'
    return {f'{kind}Points': False, 'otherId': other_id, 'error': error}


def closed_transaction_view(player, other_id, msg, **extra):
    """
    What one side needs once a transaction is accepted, rejected or fails: its
    refreshed transactions table, the chat notice, and the inputs for
    `other_id` enabled again.
    """

    return {
        'update': True,
        'updateTransactions': True,
        'transactions': round_transactions(player),
        'otherId': other_id,
        'reload': False,
        'chat': [msg.to_dict()],
        **extra,
    }


def apply_transfer(initiator, receiver, action, points):
    """
    Moves the points of an accepted transaction. reserved_points follows every
    balance change except the payer settling their own 'Ofrece', which was
    already taken out of reserved_points when the offer was made.
    """

    payer, payee = (initiator, receiver) if action == 'Ofrece' else (receiver, initiator)

    payer.current_points -= points
    payer.round_transfers_given += points
    if action == 'Solicita':
        payer.reserved_points -= points

    payee.current_points += points
    payee.reserved_points += points
    payee.round_transfers_received += points


# Leaving the page. A player who clicks "Siguiente" (or whose timer runs out)
# can no longer answer, so their pending offers/requests are closed as
# 'Expirado' and the players they were interacting with are told, so they stop
# waiting on them. participant.interaction_left_round holds the round_number of
# the last Interaction page the player left.

LEFT_NOTICE = 'El {role} avanzó a la siguiente ronda.'


def has_left(player):
    return player.participant.vars.get('interaction_left_round') == player.round_number


def interaction_partners(player):
    """The players whose screen has a chat and offer/request box with `player`."""

    others = player.get_others_in_group()
    if player.session.config['chat_only_officer']:
        # Citizens only see the officer; the officer sees every citizen.
        return [p for p in others if C.OFFICER_ID in (p.id_in_group, player.id_in_group)]
    return others


def leave_interaction(player, end_reason):
    """
    Mark `player` as gone for this round, record when, and expire their pending
    transactions (releasing points reserved for a pending offer).

    Returns:
        list of int, or None if the player had already left: the id_in_group of
        the other side of every expired transaction.
    """

    if has_left(player):
        return None
    player.participant.interaction_left_round = player.round_number

    end_interaction(interaction_keys(player), end_reason)

    group = player.group
    expired_with = []
    for t in get_open_transactions(
        participant_code=player.participant.code,
        treatment_round=player.participant.treatment_round,
        segment=player.participant.segment,
        session_code=player.session.code,
    ):
        initiator = group.get_player_by_id(t['initiator_id'])
        receiver = group.get_player_by_id(t['receiver_id'])
        if t['action'] == 'Ofrece':
            initiator.reserved_points += t['points']
        closing_transaction(initiator, receiver, 'Expirado', t['transaction_id'])
        expired_with.append(receiver.id_in_group if initiator == player else initiator.id_in_group)
    return expired_with


def partner_left_view(other, error=None):
    """What a player needs to gray out the chat and offer/request box of `other`, who left."""

    view = {'partnerLeft': other.id_in_group, 'partnerLeftText': f'El {other.role} ya avanzó.'}
    if error:
        view['partnerLeftError'] = error
    return view


def on_leaving(player, data):
    """The player clicked "Siguiente": tell their partners before the page is submitted."""

    my_id = player.id_in_group
    if leave_interaction(player, 'Siguiente') is None:
        return {my_id: {'leftConfirmed': True}}

    responses = {}
    for other in interaction_partners(player):
        msg = create_message(
            player.group, my_id, other.id_in_group,
            text=LEFT_NOTICE.format(role=player.role),
            name='SystemInfo',
        )
        responses[other.id_in_group] = {
            **partner_left_view(player),
            'chat': [msg.to_dict()],
            'reservedPoints': other.reserved_points,
        }
    responses[my_id] = {'leftConfirmed': True}
    return responses


def on_contribution(player, data):
    return {player.id_in_group: handle_contribution(player, data.get('value'))}


def on_open_transaction(player, data):
    """`player` offers ('Ofrece') or requests ('Solicita') points from another group member."""

    group = player.group
    initiator_id, receiver_id = player.id_in_group, data.get('receiverId')
    action, value = data.get('action'), data.get('value')

    # The page only sends the player's own offers/requests to another member of
    # their group; anything else (e.g. typed into the browser console) is ignored.
    other_ids = [p.id_in_group for p in player.get_others_in_group()]
    if data.get('initiatorId') != initiator_id or receiver_id not in other_ids or action not in ('Ofrece', 'Solicita'):
        return None
    if type(value) is not int or value <= 0:
        return {initiator_id: refused_transaction_view(action, receiver_id, 'Por favor, ingresa una cantidad válida.')}

    receiver = group.get_player_by_id(receiver_id)

    if has_left(player):
        return None
    if has_left(receiver):
        # Not recorded: the receiver could never have seen it.
        return {initiator_id: {
            **refused_transaction_view(action, receiver_id, f'El {receiver.role} ya avanzó a la siguiente ronda.'),
            **partner_left_view(receiver),
        }}

    transaction_id = new_transaction(player, data)

    if transaction_id is None:
        # The database didn't record it, so it could never be accepted or
        # cancelled (and an offer would keep its points reserved): refuse it.
        return {initiator_id: refused_transaction_view(
            action, receiver_id, 'No se pudo enviar. Inténtalo de nuevo.'
        )}

    if action == 'Ofrece':
        allowed = value <= player.reserved_points
        error = 'No puedes ofrecer más puntos de los que tienes disponibles.'
    else:
        allowed = value <= group.total_initial_points
        error = 'No puedes solicitar más puntos de los que hay en tu grupo.'

    if not allowed:
        # Kept in the data as an attempt, but closed right away: an open
        # transaction would be restored on the receiver's screen by
        # get_last_transaction_status() at their next page reload. No chat
        # notice, since the receiver never saw this offer/request.
        closing_transaction(player, receiver, 'Fallido', transaction_id)
        return {initiator_id: refused_transaction_view(action, receiver_id, error)}

    if action == 'Ofrece':
        # Reserve the offered amount now, so a second offer can't be made
        # against points already promised here.
        player.reserved_points -= value

    action_label = 'ofreció' if action == 'Ofrece' else 'solicitó'
    unit_label = 'punto' if value == 1 else 'puntos'
    msg = create_message(
        group, initiator_id, receiver_id,
        text=f'El {player.role} {action_label} {value} {unit_label}.',
        name='TransferInfo',
        transaction_id=transaction_id,
    )

    initiator_view = {
        **pending_transaction_view(action, value, transaction_id, initiator_id, receiver_id, is_initiator=True),
        'chat': [msg.to_dict()],
    }
    if action == 'Ofrece':
        initiator_view['reservedPoints'] = player.reserved_points

    return {
        initiator_id: initiator_view,
        receiver_id: {
            **pending_transaction_view(action, value, transaction_id, receiver_id, initiator_id, is_initiator=False),
            'chat': [msg.to_dict()],
        },
    }


CLOSING_LABELS = {'Aceptado': 'aceptó', 'Rechazado': 'rechazó', 'Cancelado': 'canceló'}


def on_close_transaction(player, data):
    """
    The receiver accepts ('Aceptado') or rejects ('Rechazado') an open
    offer/request, or the initiator cancels it ('Cancelado').
    """

    group = player.group
    status, transaction_id = data.get('status'), data.get('transactionId')

    transaction = get_transaction(transaction_id)
    if (transaction is not None and transaction['status'] == 'Expirado'
            and transaction['group_id'] == player.group_id
            and player.id_in_group in (transaction['initiator_id'], transaction['receiver_id'])):
        # The other side left the page first (e.g. their timer ran out a moment
        # earlier); nothing moves, the box for them is grayed out.
        other_id = transaction['receiver_id'] if player.id_in_group == transaction['initiator_id'] else transaction['initiator_id']
        other = group.get_player_by_id(other_id)
        return {player.id_in_group: {
            **partner_left_view(other, error=f'El {other.role} ya avanzó a la siguiente ronda.'),
            'reservedPoints': player.reserved_points,
        }}

    if (status not in CLOSING_LABELS or transaction is None
            or transaction['group_id'] != player.group_id or transaction['status'] != 'Iniciado'):
        # Unknown, from another group or round, or already closed: a double
        # click, or both players clicking at once (e.g. "Aceptar" arriving just
        # after the initiator cancelled). The first click already updated both
        # screens; applying a second one would move the points again.
        return None

    # Who is who comes from the database, not from the page: only the
    # initiator can cancel, and only the receiver can accept or reject.
    initiator_id, receiver_id = transaction['initiator_id'], transaction['receiver_id']
    if player.id_in_group != (initiator_id if status == 'Cancelado' else receiver_id):
        return None

    points, action = transaction['points'], transaction['action']
    initiator = group.get_player_by_id(initiator_id)
    receiver = group.get_player_by_id(receiver_id)

    action_label = 'oferta' if action == 'Ofrece' else 'solicitud'

    # A 'Solicita' reserves nothing up front (the receiver, who pays, never
    # committed to it), so whether the receiver can pay is checked now, against
    # reserved_points: current_points may include points they already promised
    # in their own pending 'Ofrece'. Recorded as 'Fallido', not 'Rechazado',
    # so this system block can be told apart from a player's rejection.
    if status == 'Aceptado' and action == 'Solicita' and points > receiver.reserved_points:
        closing_transaction(initiator, receiver, 'Fallido', transaction_id)
        msg = create_message(
            group, initiator_id, receiver_id,
            text=f'El {receiver.role} no tenía suficientes puntos disponibles para completar la {action_label}.',
            name='TransferInfo',
            transaction_id=transaction_id,
        )
        return {
            # Only the payer gets a popup: it's their own balance.
            receiver_id: closed_transaction_view(
                receiver, initiator_id, msg, error='No tienes suficientes puntos disponibles.'
            ),
            initiator_id: closed_transaction_view(initiator, receiver_id, msg),
        }

    if status == 'Aceptado':
        apply_transfer(initiator, receiver, action, points)
    elif action == 'Ofrece':
        # Rejected or cancelled: release the points reserved for the offer.
        initiator.reserved_points += points

    closing_transaction(initiator, receiver, status, transaction_id)

    msg = create_message(
        group, initiator_id, receiver_id,
        text=f'El {player.role} {CLOSING_LABELS[status]} la {action_label}.',
        name='TransferInfo',
        transaction_id=transaction_id,
    )

    if status == 'Cancelado':
        return {
            initiator_id: {
                'cancelAction': True,
                'otherId': receiver_id,
                'chat': [msg.to_dict()],
                'reservedPoints': initiator.reserved_points,
            },
            receiver_id: {'cancelAction': True, 'otherId': initiator_id, 'chat': [msg.to_dict()]},
        }

    return {
        initiator_id: closed_transaction_view(
            initiator, receiver_id, msg, reservedPoints=initiator.reserved_points
        ),
        receiver_id: closed_transaction_view(
            receiver, initiator_id, msg, reservedPoints=receiver.reserved_points
        ),
    }


def on_reload(player, data):
    """
    The page was (re)loaded: restore the player's contribution, transactions
    table, and any offer/request of theirs still waiting for an answer.
    """

    my_id = player.id_in_group
    if has_left(player):
        # Their "Siguiente" was processed but the page didn't move on: finish it.
        return {my_id: {'leftConfirmed': True}}

    view = {**reload_contribution(player), 'reservedPoints': player.reserved_points}
    partners_left = [partner_left_view(p) for p in interaction_partners(player) if has_left(p)]
    if partners_left:
        view['partnersLeft'] = partners_left
    transactions = round_transactions(player)

    pending = get_last_transaction_status(
        participant_code=player.participant.code,
        treatment_round=player.participant.treatment_round,
        segment=player.participant.segment,
        session_code=player.session.code,
    )

    if not pending:
        if transactions:
            view.update(updateTransactions=True, transactions=transactions, update=True)
        return {my_id: view}

    action, value = pending['action'], pending['value']
    transaction_id = pending['transactionId']
    initiator_id, receiver_id = pending['initiatorId'], pending['receiverId']
    is_initiator = my_id == initiator_id
    other_id = receiver_id if is_initiator else initiator_id

    view.update(
        pending_transaction_view(action, value, transaction_id, my_id, other_id, is_initiator),
        updateTransactions=True,
        transactions=transactions,
        update=True,
        transactionId=transaction_id,
    )

    # The receiver's accept/reject buttons are sent again too. When the
    # receiver is the one reloading, their own entry (listed second) replaces it.
    receiver = player.group.get_player_by_id(receiver_id)
    return {
        receiver_id: {
            **pending_transaction_view(action, value, transaction_id, receiver_id, initiator_id, is_initiator=False),
            'reservedPoints': receiver.reserved_points,
            'updateTransactions': True,
            'transactions': round_transactions(receiver),
            'update': True,
        },
        my_id: view,
    }


def on_chat(player, data):
    my_id, recipient_id = player.id_in_group, data['recipient']
    if has_left(player):
        return None
    recipient = player.group.get_player_by_id(recipient_id)
    if has_left(recipient):
        return {my_id: partner_left_view(recipient, error=f'El {recipient.role} ya avanzó a la siguiente ronda.')}
    msg = create_message(
        player.group, my_id, recipient_id,
        text=data['text'],
        text_unfiltered=data['text'],
        name='Player',
    )
    return {my_id: [msg.to_dict()], recipient_id: [msg.to_dict()]}


def chat_history(player):
    """Every message the player sent or received this round."""

    my_id = player.id_in_group
    return {my_id: [
        msg.to_dict()
        for msg in Message.filter(group=player.group)
        if msg.sender and msg.recipient
        and my_id in (msg.sender.id_in_group, msg.recipient.id_in_group)
    ]}


LIVE_HANDLERS = {
    'contributionPoints': on_contribution,
    'initiatingTransaction': on_open_transaction,
    'closingTransaction': on_close_transaction,
    'reloadPage': on_reload,
    'leavingInteraction': on_leaving,
}


# PAGES
class Instructions(Page):
    form_model = 'player'

    @staticmethod
    def vars_for_template(player):
        return {
            **instructions_vars(player),
            'num_questions': len(Instructions.get_form_fields(player)),
        }

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

        # Treatments with a private interaction channel also get a question
        # checking that participants know private transfers affect their payoff.
        if treatment in ['T1', 'T2', 'T3', 'T4', 'T6', 'T7']:
            fields.append('comp_private_payoff')

        return fields

    @staticmethod
    def error_message(player, values):
        incorrect = {
            field: answer
            for field, answer in values.items()
            if field in C.COMPREHENSION_ANSWERS and answer != C.COMPREHENSION_ANSWERS[field]
        }

        if incorrect:
            player.num_failed_attempts += 1

            # Load and append failed attempts
            previous = json.loads(player.field_maybe_none('errors_per_attempt') or '[]')
            previous.append(incorrect)
            player.errors_per_attempt = json.dumps(previous)

            return {field: 'Respuesta incorrecta.' for field in incorrect}


class FirstWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group):
        players = group.get_players()
        player = group.get_players()[0]
        officer_endowment = group.subsession.session.config['officer_endowment']
        c1_endowment = group.subsession.session.config['c1_endowment']
        # Sets random multiplier
        if TREATMENTS[player.participant.treatment].random_multiplier:
            group.multiplier = random.choices([1.5, 2.5], weights=[1, 2])[0]
        
        for player in players:
            # Assign initial points based on role
            player.initial_points = C.CITIZEN_ENDOWMENT if player.role != C.OFFICER_ROLE else officer_endowment

            # Heterogeneous endowment for citizen 1 (if applicable)
            if TREATMENTS[player.participant.treatment].heterogenous_citizens and player.id_in_group == 1:
                player.initial_points = c1_endowment

            player.current_points = player.initial_points
            player.reserved_points = player.initial_points

            # Initialize group-level fields
            group.total_initial_points += player.initial_points

class Interaction(Page):
    timeout_seconds = 60 * 3
    timer_text = 'Tiempo restante:'
    form_model = 'player'

    @staticmethod
    def get_form_fields(player):
        # contribution_points is committed directly by handle_contribution() via
        # live_method, not through the page's own form submission — the input
        # that would back this field is never kept in sync with that committed
        # value (blank on reload), so declaring it here would let a plain form
        # submit silently overwrite the real value with blank/None.
        return []

    @staticmethod
    def vars_for_template(player):
        start_interaction(interaction_keys(player))

        # Identify other players in group
        others = player.get_others_in_group()
        officer = next((p for p in others if p.role == C.OFFICER_ROLE), None)
        citizens = [p for p in others if p.role != C.OFFICER_ROLE]

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
        if treatment_cfg.officer_interactions_public and player.role != C.OFFICER_ROLE:
            other_citizens = [c for c in citizens if c.id_in_group != player.id_in_group]
            additional_chats = [
                {
                    "id_in_group": f"{other_citizen.id_in_group}",
                    "role": f"Chat entre {other_citizen.role} y Funcionario",
                    "channel": (
                        f"{player.participant.segment}"
                        f"{player.participant.treatment_round}"
                        f"{player.group_id}"
                        f"{other_citizen.id_in_group}{C.OFFICER_ID}"
                    ),
                }
                for other_citizen in other_citizens
            ]

        history = get_cached_history(player)

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
            # Citizens chat first and can contribute only later (same condition as in Interaction.html's JS)
            'sequential_contribution': player.session.config['sequential_decision'] and treatment_cfg.private_interaction,
            'officer_interactions_public': treatment_cfg.officer_interactions_public,
            'chat_only_officer': player.session.config['chat_only_officer'],
            'additional_channels': additional_chats if treatment_cfg.officer_interactions_public else [],
            
            # Instructions variables
            'num_treatments': num_treatments,
            'num_rounds': num_rounds,
            'tot_num_rounds': tot_num_rounds,
            'tot_session_time': tot_session_time,
            'time_unit': time_unit,
            **instructions_vars(player),
        }

    @staticmethod
    def js_vars(player):
        return {
            'secuential_decision': player.session.config['sequential_decision'],
            'private_interaction_duration': player.session.config['private_interaction_duration'],
            'public_interaction_activation': player.session.config['public_interaction_activation'],
            'private_interaction': TREATMENTS[player.participant.treatment].private_interaction,
            'officer_interactions_public': TREATMENTS[player.participant.treatment].officer_interactions_public,
            'player_role': player.role,
            'my_id': player.id_in_group,
            'other_ids': [p.id_in_group for p in player.get_others_in_group()],
        }

    @staticmethod
    def live_method(player, data):
        handler = LIVE_HANDLERS.get(data.get('type'))
        if handler:
            return handler(player, data)

        if 'text' in data and 'recipient' in data:
            return on_chat(player, data)

        # The page sends an empty message on load to get its chat history.
        return chat_history(player)

    @staticmethod
    def before_next_page(player, timeout_happened):
        # Already done if the player clicked "Siguiente" (on_leaving); this
        # covers the timer running out, or the click's live message not arriving.
        leave_interaction(player, 'Tiempo agotado' if timeout_happened else 'Siguiente')

        if timeout_happened and (player.role != C.OFFICER_ROLE) and (player.field_maybe_none('contribution_points') is None):
            player.timeout_penalty = True 


class SecondWaitPage(WaitPage):
    template_name = 'public_goods/MyWaitPage.html'
    body_text = 'Esperando a que los demás participantes tomen sus decisiones...'

    @staticmethod
    def vars_for_template(player):
        history = get_cached_history(player)

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
    timeout_seconds = 60 * 2
    timer_text = 'Tiempo restante:'
    form_model = 'group'
    form_fields = ['allocation1', 'allocation2', 'allocation3']

    @staticmethod
    def is_displayed(player):
        return (
            TREATMENTS[player.participant.treatment].resource_allocation
            and player.id_in_group == C.OFFICER_ID
        )

    @staticmethod
    def js_vars(player):
        return {'total_allocation': player.group.total_allocation}

    @staticmethod
    def vars_for_template(player):
        history = get_cached_history(player)

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

        # Contribution of each citizen this round, shown above their allocation field
        contributions = {
            f'contribution{p.id_in_group}': p.field_maybe_none('contribution_points') or 0
            for p in player.group.get_players() if p.id_in_group != C.OFFICER_ID
        }

        return {
            'history': history,
            **contributions,
            'private_interaction': TREATMENTS[player.participant.treatment].private_interaction,
            'num_treatments': num_treatments,
            'num_rounds': num_rounds,
            'tot_num_rounds': tot_num_rounds,
            'tot_session_time': tot_session_time,
            'time_unit': time_unit,
            **instructions_vars(player),
        }
    
    @staticmethod
    def live_method(player, data):
        # Logs each calculation the officer makes. insert_row() reports its own
        # database errors, so a failed log never interrupts the page.
        if not isinstance(data, dict) or 'value' not in data:
            print(f"Calculator: ignoring message without 'value': {data}")
            return

        insert_row(data={
            **round_keys(player),
            'participant_code': player.participant.code,
            'id_in_group': player.id_in_group,
            'operation': data['value'],
        }, table='calculator_history')
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.timeout_penalty = timeout_happened
    

class ThirdWaitPage(WaitPage):
    template_name = 'public_goods/MyWaitPage.html'
    body_text = 'Esperando a que los demás participantes tomen sus decisiones...'

    @staticmethod
    def vars_for_template(player):
        history = get_cached_history(player)

        return {
            'segment': player.participant.segment,
            'history': history,
            'private_interaction': TREATMENTS[player.participant.treatment].private_interaction,
            'random_audits': TREATMENTS[player.participant.treatment].random_audits,
        }
    
    @staticmethod
    def after_all_players_arrive(group):
        store_actual_allocation(group)
        # Audits must be resolved before insert_history(), which computes payoffs
        # via set_payoffs() and so needs corruption_punishment already set.
        player = group.get_players()[0]
        if TREATMENTS[player.participant.treatment].random_audits:
            apply_corruption_penalty(group)
        insert_history(group)


class Results(Page):
    timeout_seconds = 20
    timer_text = 'Tiempo restante:'

    @staticmethod
    def vars_for_template(player):
        history = get_cached_history(player)

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
        # Last round of the session: there is no next round to set up.
        if player.round_number == C.NUM_ROUNDS:
            return

        # End of a treatment block: move on to the next treatment.
        if player.participant.treatment_round == player.session.config['num_rounds']:
            player.participant.segment += 1
            player.participant.treatment_round = 1
            player.participant.treatment = player.session.config['treatment_order'][player.participant.segment - 1]
        else:
            player.participant.treatment_round += 1


page_sequence = [
    Instructions,           # General instructions and comprehension check
    FirstWaitPage,          # Wait for all to finish instructions
    Interaction,            # Public contribution and private interaction
    SecondWaitPage,         # Wait before allocation
    ResourceAllocation,     # Officer allocates (if treatment)
    ThirdWaitPage,          # Apply audits (if treatment) or penalties
    Results                 # Display outcomes
]