"""
Bots for the public_goods app. Run the whole experiment with:

    otree test public_goods_demo

`public_goods_demo` plays every treatment except T6/T7, so it covers both
rounds with and without private interaction and officer allocation.

DATABASE_URL must point to a disposable PostgreSQL database: the game writes
to the `game_data` schema, and these bots add test rows to it.
"""

import sys

from otree.api import Bot, Submission

from . import C, TREATMENTS, Instructions, Interaction, ResourceAllocation, Results


class PlayerBot(Bot):
    def play_round(self):
        if Instructions.is_displayed(self.player):
            fields = Instructions.get_form_fields(self.player)
            yield Instructions, {field: C.COMPREHENSION_ANSWERS[field] for field in fields}

        # The page has no submit button: it moves on when its timer runs out.
        yield Submission(Interaction, check_html=False)

        if ResourceAllocation.is_displayed(self.player):
            share = self.group.total_allocation / 3
            # "Siguiente" submits from JavaScript, after checking the allocation adds up.
            yield Submission(
                ResourceAllocation,
                dict(allocation1=share, allocation2=share, allocation3=share),
                check_html=False,
            )

        yield Results


def call_live_method(method, page_class, group, **kwargs):
    """
    oTree runs this once per group and round when the bots reach a page with a
    live_method. `method(id_in_group, data)` acts as that player's liveSend()
    and returns the server's responses, keyed by recipient id_in_group.
    """

    if page_class == ResourceAllocation:
        expect(method(C.OFFICER_ID, {'type': 'calcOperation', 'value': '30 / 3 = 10'}), None)
        return

    treatment = group.get_player_by_id(1).participant.treatment
    if page_class == Interaction and TREATMENTS[treatment].private_interaction:
        play_private_interaction(method, group)


def offer(initiator_id, receiver_id, value):
    return _initiate('Ofrece', initiator_id, receiver_id, value)


def request(initiator_id, receiver_id, value):
    return _initiate('Solicita', initiator_id, receiver_id, value)


def _initiate(action, initiator_id, receiver_id, value):
    return {
        'type': 'initiatingTransaction',
        'action': action,
        'value': value,
        'initiatorId': initiator_id,
        'receiverId': receiver_id,
    }


def close(status, initiator_id, receiver_id, transaction_id):
    return {
        'type': 'closingTransaction',
        'status': status,
        'initiatorId': initiator_id,
        'receiverId': receiver_id,
        'transactionId': transaction_id,
    }


def expect(actual, expected, what=''):
    assert actual == expected, f'{what}: expected {expected!r}, got {actual!r}'


def play_private_interaction(method, group):
    """
    One round of private interaction, covering every outcome a transaction can
    have, as the page's JavaScript would send it. Citizens 1-3, officer 4.
    """

    players = {p.id_in_group: p for p in group.get_players()}
    c1, c2 = players[1], players[2]

    def balances():
        return {i: (p.current_points, p.reserved_points) for i, p in players.items()}

    # Page load with nothing going on: only the available points come back.
    expect(method(2, {'type': 'reloadPage'}), {2: {'reservedPoints': c2.reserved_points}}, 'empty reload')

    # Contribution.
    response = method(2, {'type': 'contributionPoints', 'value': 5})
    expect(response[2]['contributionPointsValid'], True, 'contribution')
    expect(c2.contribution_points, 5, 'contribution stored')

    # The same contribution sent twice is only charged once.
    before = balances()
    response = method(2, {'type': 'contributionPoints', 'value': 7})
    expect(response[2]['contributionPoints'], 5, 'second contribution answers with the first')
    expect((c2.contribution_points, balances()), (5, before), 'second contribution charges nothing')

    # A contribution of 0 is restored on reload too.
    method(3, {'type': 'contributionPoints', 'value': 0})
    expect(method(3, {'type': 'reloadPage'})[3].get('contributionPointsReload'), True, 'reload: 0 contribution kept')

    # Chat goes to sender and recipient.
    response = method(1, {'text': 'hola', 'recipient': C.OFFICER_ID})
    expect(set(response), {1, C.OFFICER_ID}, 'chat recipients')
    expect(response[1][0]['text'], 'hola', 'chat text')

    # Offer, accepted. The receiver reloads while it's pending and must see
    # both the offer and their earlier contribution.
    response = method(1, offer(1, 2, 10))
    transaction_id = response[1]['transactionId']
    expect(response[2]['offerPoints'] and response[2]['receiver'], True, 'offer reaches receiver')
    expect(c1.reserved_points, c1.current_points - 10, 'offer reserves points')

    reload = method(2, {'type': 'reloadPage'})[2]
    expect(reload.get('offerPoints'), True, 'reload: pending offer')
    expect(reload.get('contributionPointsReload'), True, 'reload: contribution kept')

    c1_before, c2_before = c1.current_points, c2.current_points
    response = method(2, close('Aceptado', 1, 2, transaction_id))
    expect((c1.current_points, c2.current_points), (c1_before - 10, c2_before + 10), 'accept moves points')
    expect(response[1]['transactions'][-1]['¿Se aceptó?'], 'Aceptado', 'accepted shows in table')
    expect(c1.round_transfers_given, 10, 'transfer given')
    expect(c2.round_transfers_received, 10, 'transfer received')

    # A second click on "Aceptar" for the same transaction changes nothing.
    before = balances()
    expect(method(2, close('Aceptado', 1, 2, transaction_id)), None, 'double accept')
    expect(balances(), before, 'double accept leaves balances')

    # Offer above available points: refused, and leaves no chat message behind.
    too_much = c1.reserved_points + 1
    response = method(1, offer(1, C.OFFICER_ID, too_much))
    expect(response[1]['offerPoints'], False, 'offer too large')
    expect(set(response), {1}, 'offer too large only answers the initiator')
    chat = method(1, {})[1]
    expect([m for m in chat if f'ofreció {too_much}' in m['text']], [], 'no message for refused offer')

    # The database fails to record an offer: refused, nothing reserved.
    before = balances()
    game = sys.modules[Interaction.__module__]
    original = game.open_transaction
    game.open_transaction = lambda data: None
    try:
        response = method(1, offer(1, C.OFFICER_ID, 5))
    finally:
        game.open_transaction = original
    expect(response, {1: {'offerPoints': False, 'otherId': C.OFFICER_ID, 'error': 'No se pudo enviar. Inténtalo de nuevo.'}}, 'unrecorded offer')
    expect(balances(), before, 'unrecorded offer reserves nothing')

    # Messages the page never sends are ignored or refused: acting for another
    # player, an offer to oneself, an amount that isn't a positive whole number,
    # or answering a transaction one isn't the receiver of.
    expect(method(2, offer(1, 3, 5)), None, 'offer on behalf of someone else')
    expect(method(1, offer(1, 1, 5)), None, 'offer to oneself')
    for bad_value in (0, -5, 2.5):
        expect(method(1, offer(1, 2, bad_value))[1]['offerPoints'], False, f'offer of {bad_value}')
    expect(method(1, request(1, 2, 0))[1]['requestPoints'], False, 'request of 0')
    transaction_id = method(1, offer(1, C.OFFICER_ID, 5))[1]['transactionId']
    expect(method(1, close('Aceptado', 1, C.OFFICER_ID, transaction_id)), None, 'initiator accepting own offer')
    expect(method(3, close('Rechazado', 1, C.OFFICER_ID, transaction_id)), None, 'outsider rejecting')
    expect(method(C.OFFICER_ID, close('Cancelado', 1, C.OFFICER_ID, transaction_id)), None, 'receiver cancelling')
    method(1, close('Cancelado', 1, C.OFFICER_ID, transaction_id))
    expect(balances(), before, 'ignored messages leave balances')

    # Request, rejected.
    before = balances()
    response = method(C.OFFICER_ID, request(C.OFFICER_ID, 3, 20))
    transaction_id = response[C.OFFICER_ID]['transactionId']
    expect(response[3]['requestPoints'] and response[3]['receiver'], True, 'request reaches receiver')
    response = method(3, close('Rechazado', C.OFFICER_ID, 3, transaction_id))
    expect(response[3]['transactions'][-1]['¿Se aceptó?'], 'Rechazado', 'rejected shows in table')
    expect(balances(), before, 'rejection leaves balances')

    # Request above the group's total points: refused.
    response = method(C.OFFICER_ID, request(C.OFFICER_ID, 3, group.total_initial_points + 1))
    expect(response[C.OFFICER_ID]['requestPoints'], False, 'request too large')

    # Request the receiver can't cover: accepted, but fails.
    response = method(C.OFFICER_ID, request(C.OFFICER_ID, 1, c1.reserved_points + 1))
    transaction_id = response[C.OFFICER_ID]['transactionId']
    response = method(1, close('Aceptado', C.OFFICER_ID, 1, transaction_id))
    expect(response[1]['error'], 'No tienes suficientes puntos disponibles.', 'unaffordable request')
    expect(balances(), before, 'failed request leaves balances')

    # The initiator reloads while their offer is pending: the receiver gets
    # their buttons back, with their own transactions table, not the initiator's.
    response = method(1, offer(1, C.OFFICER_ID, 5))
    transaction_id = response[1]['transactionId']
    response = method(1, {'type': 'reloadPage'})
    expect(response[1]['offerPoints'] and response[1]['initiator'], True, 'initiator reload: pending offer')
    officer_table = method(C.OFFICER_ID, {'type': 'reloadPage'})[C.OFFICER_ID]['transactions']
    expect(response[C.OFFICER_ID]['transactions'], officer_table, "initiator reload: receiver's own table")

    # Offer cancelled; the receiver's "Aceptar" arriving afterwards is ignored.
    response = method(1, close('Cancelado', 1, C.OFFICER_ID, transaction_id))
    expect(response[C.OFFICER_ID]['cancelAction'], True, 'cancel reaches receiver')
    expect(balances(), before, 'cancel releases reserved points')
    expect(method(C.OFFICER_ID, close('Aceptado', 1, C.OFFICER_ID, transaction_id)), None, 'accept after cancel')
    expect(balances(), before, 'accept after cancel leaves balances')

    # Nothing left pending, so a reload restores no offer.
    expect('offerPoints' in method(1, {'type': 'reloadPage'})[1], False, 'reload after cancel')

    # The officer clicks "Siguiente" with an offer to them and a request of
    # theirs both pending: both expire, the offered points are released, and
    # every citizen is told the officer left.
    before = balances()
    offer_id = method(1, offer(1, C.OFFICER_ID, 5))[1]['transactionId']
    request_id = method(C.OFFICER_ID, request(C.OFFICER_ID, 2, 3))[C.OFFICER_ID]['transactionId']
    response = method(C.OFFICER_ID, {'type': 'leavingInteraction'})
    expect(response[C.OFFICER_ID], {'leftConfirmed': True}, 'leaver moves on')
    expect(set(response), {1, 2, 3, C.OFFICER_ID}, 'every citizen is told')
    expect(response[1]['partnerLeft'], C.OFFICER_ID, 'citizen grays out the officer')
    expect(response[1]['chat'][0]['name'], 'SystemInfo', 'left notice in chat')
    expect(balances(), before, 'expired offer releases reserved points')
    for transaction_id in (offer_id, request_id):
        expect(game.get_transaction(transaction_id)['status'], 'Expirado', 'pending transaction expires')

    # Nothing more reaches the officer, and nothing is recorded.
    response = method(1, offer(1, C.OFFICER_ID, 5))
    expect((response[1]['offerPoints'], response[1]['partnerLeft']), (False, C.OFFICER_ID), 'offer to a player who left')
    expect(balances(), before, 'refused offer reserves nothing')
    expect(method(1, {'text': 'hola?', 'recipient': C.OFFICER_ID})[1]['partnerLeft'], C.OFFICER_ID, 'chat to a player who left')
    response = method(2, close('Aceptado', C.OFFICER_ID, 2, request_id))
    expect(response[2]['partnerLeft'], C.OFFICER_ID, 'answering an expired request')
    expect(balances(), before, 'answering an expired request moves nothing')

    # A citizen reloading still sees the officer grayed out; the officer
    # reloading (or clicking again) just moves on.
    expect(method(1, {'type': 'reloadPage'})[1]['partnersLeft'][0]['partnerLeft'], C.OFFICER_ID, 'reload keeps the officer grayed out')
    expect(method(C.OFFICER_ID, {'type': 'reloadPage'}), {C.OFFICER_ID: {'leftConfirmed': True}}, 'leaver reloading')
    expect(method(C.OFFICER_ID, {'type': 'leavingInteraction'}), {C.OFFICER_ID: {'leftConfirmed': True}}, 'second click')

    # Contribution times: citizens 2 and 3 contributed above, the officer never does.
    game_sql = sys.modules[game.record_contribution_time.__module__]
    with game_sql._cursor() as cur:
        cur.execute("""
            SELECT id_in_group, contributed_at IS NOT NULL AS contributed
            FROM game_data.interaction_times
            WHERE session_code = %s AND round_number = %s AND group_id = %s
        """, (group.session.code, group.round_number, group.id))
        contributed = {row['id_in_group']: row['contributed'] for row in cur.fetchall()}
    expect((contributed.get(2), contributed.get(3), contributed.get(C.OFFICER_ID)), (True, True, False), 'contribution times')
