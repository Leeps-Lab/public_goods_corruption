from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'cuestionario_final'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    # Demographics
    age = models.IntegerField(
        label='*¿Cuál es tu edad?',
        min=18,
    )
    gender = models.StringField(
        label='*¿Cuál es tu género?',
        choices=['Masculino', 'Femenino', 'Otro', 'Prefiero no contestar'],
    )
    zone_residence = models.StringField(
        label='*¿Cuál es tu zona de residencia?',
        choices=[
            'Zona 1: Puente Piedra, Comas, Carabayllo',
            'Zona 2: Independencia, Los Olivos, San Martín de Porras',
            'Zona 3: San Juan de Lurigancho',
            'Zona 4: Cercado, Rimac, Breña, La Victoria',
            'Zona 5: Ate, Chaclacayo, Lurigancho, Santa Anita, San Luis, El Agustino',
            'Zona 6: Jesús María, Lince, Pueblo Libre, Magdalena, San Miguel',
            'Zona 7: Miraflores, San Isidro, San Borja, Surco, La Molina',
            'Zona 8: Surquillo, Barranco, Chorrillos, San Juan de Miraflores',
            'Zona 9: Villa El Salvador, Villa maría del Triunfo, Lurín, Pachacamac',
            'Zona 10: Callao, Bellavista, La Perla, La Punta, Carmen de la Legua, Ventanilla',
            'Fuera de Lima',
        ],
    )
    university = models.StringField(
        label='¿En qué universidad estudias?',
        choices=[
            'Universidad del Pacífico',
            'Pontificia Universidad Católica del Perú (PUCP)',
            'Universidad Nacional Mayor de San Marcos (UNMSM)',
            'Universidad de Lima',
            'Universidad San Ignacio de Loyola (USIL)',
            'Universidad Peruana de Ciencias Aplicadas (UPC)',
            'Universidad Nacional de Ingeniería (UNI)',
            'Universidad Nacional Agraria La Molina (UNALM)',
            'Universidad de Piura (UDEP)',
            'Universidad ESAN',
            'Otra',
        ],
    )
    degree = models.StringField(
        label='¿Cuál es tu carrera?',
        choices=[
            'Administración',
            'Contabilidad',
            'Economía',
            'Finanzas',
            'Negocios Internacionales',
            'Marketing',
            'Derecho',
            'Ciencias Políticas',
            'Relaciones Internacionales',
            'Sociología',
            'Psicología',
            'Comunicaciones',
            'Ingeniería Industrial',
            'Ingeniería de Sistemas',
            'Ingeniería Empresarial',
            'Ingeniería Civil',
            'Ingeniería Electrónica',
            'Ingeniería Mecánica',
            'Arquitectura',
            'Medicina',
            'Enfermería',
            'Educación',
            'Otra',
        ],
    )
    year_of_study = models.StringField(
        label='¿En qué año de estudios te encuentras?',
        choices=[
            'Primer año',
            'Segundo año',
            'Tercer año',
            'Cuarto año',
            'Quinto año',
            'Sexto año o más',
            'Egresado',
        ],
    )
    previous_experiments = models.IntegerField(
        label='*¿Has participado en experimentos económicos o de comportamiento anteriormente?',
        choices=[
            [0, 'No, esta es mi primera vez'],
            [1, 'Sí, ya he participado anteriormente'],
            [2, 'No recuerdo']
        ],
        widget=widgets.RadioSelect,
    )

    # Attitudes toward corruption and public officials
    trust_public_officials = models.IntegerField(
        choices=[
            [1, 'Nada'],
            [2, 'Poco'],
            [3, 'Moderadamente'],
            [4, 'Bastante'],
            [5, 'Mucho'],
        ],
        label='*¿Cuánto confías en los funcionarios públicos en general?',
        widget=widgets.RadioSelect,
    )
    trust_government = models.IntegerField(
        choices=[
            [1, 'Nada'],
            [2, 'Poco'],
            [3, 'Moderadamente'],
            [4, 'Bastante'],
            [5, 'Mucho'],
        ],
        label='*¿Cuánto confías en las instituciones públicas?',
        widget=widgets.RadioSelect,
    )
    fairness_importance = models.IntegerField(
        choices=[
            [1, 'Nada importante'],
            [2, 'Poco importante'],
            [3, 'Moderadamente importante'],
            [4, 'Muy importante'],
            [5, 'Extremadamente importante'],
        ],
        label='*¿Qué tan importante es para ti que los recursos públicos se distribuyan de manera justa?',
        widget=widgets.RadioSelect,
    )

    # Final Questionnaire
    instructions_clarity = models.IntegerField(
        choices=[
            [1, 'Muy poco claras'],
            [2, 'Poco claras'],
            [3, 'Moderadamente claras'],
            [4, 'Muy claras'],
            [5, 'Completamente claras'],
        ],
        label='*¿Qué tan claras fueron las instrucciones del experimento?',
        widget=widgets.RadioSelect,
    )
    feedback_issues = models.LongStringField(
        blank=True,
        label='¿Hubo algún momento durante el juego en el que no estabas seguro de qué hacer o cómo proceder? Por favor, describe la situación.',
    )
    feedback_suggestions = models.LongStringField(
        blank=True,
        label='¿Tienes alguna sugerencia para mejorar el experimento? (Por ejemplo: instrucciones, interfaz, duración, etc.)',
    )


# PAGES
class Demographics(Page):
    form_model = 'player'
    form_fields = [
        'age',
        'gender',
        'zone_residence',
        'university',
        'degree',
        'year_of_study',
        'previous_experiments',
        'trust_public_officials',
        'trust_government',
        'fairness_importance',
    ]

class FinalQuestionnaire(Page):
    form_model = 'player'
    form_fields = [
        'instructions_clarity',
        'feedback_issues',
        'feedback_suggestions',
    ]


page_sequence = [Demographics, FinalQuestionnaire]