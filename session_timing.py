"""
Estimated session length shown in the general instructions. Shared by the
introduction and public_goods apps, so every page shows the same estimate.
"""

ROUND_MINUTES = 4   # Average length of one round
EXTRA_MINUTES = 10  # Reading the instructions and answering the final questionnaire


def session_timing(config):
    """
    Number of blocks and rounds in the session, and its estimated length as
    Spanish text (e.g. '58 minutos', '1 hora y 10 minutos').

    Args:
        config (dict): The session config ('treatment_order', 'num_rounds').
    """

    num_treatments = len(config['treatment_order'])
    num_rounds = config['num_rounds']
    tot_num_rounds = num_treatments * num_rounds

    minutes = tot_num_rounds * ROUND_MINUTES + EXTRA_MINUTES
    if minutes < 60:
        duration = f'{minutes} minutos'
    else:
        hours, rest = divmod(minutes, 60)
        duration = f'{hours} hora' if hours == 1 else f'{hours} horas'
        if rest:
            duration += f' y {rest} minutos'

    return {
        'num_treatments': num_treatments,
        'num_rounds': num_rounds,
        'tot_num_rounds': tot_num_rounds,
        'session_duration': duration,
    }
