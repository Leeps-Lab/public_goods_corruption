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
        label='¿Cuál es tu edad?',
        min=18,
    )
    gender = models.StringField(
        label='¿Cuál es tu género?',
        choices=['Masculino', 'Femenino', 'Otro', 'Prefiero no contestar'],
    )
    degree = models.StringField(
        label='¿Cuál es tu carrera?',
        choices=['Administración', 'Contabilidad', 'Derecho', 'Economía', 'Finanzas', 'Humanidades Digitales', 'Ingeniería Empresarial', 'Ingeniería de la Información', 'Ingeniería en Innovación y Diseño', 'Marketing', 'Negocios Internacionales', 'Política, Filosofía y Economía'],
    )
    zone_residence = models.StringField(
        label='¿Cuál es tu zona de residencia?',
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
            'Otro'
        ],
    )

    # Final Questionnaire
    understanding = models.LongStringField(
        blank=True,
        label='¿Qué crees que no estuvo claro de las instrucciones?',
    )
    doubts = models.LongStringField(
        blank=True,
        label='¿Qué dudas tuviste durante la sesión?',
    )
    suggestions = models.LongStringField(
        blank=True,
        label='¿Qué sugerencias tienes para mejorar la claridad de las instrucciones o la experiencia del juego?',
    )


# PAGES
class Demographics(Page):
    form_model = 'player'
    form_fields = ['age', 'gender', 'degree', 'zone_residence']

class FinalQuestionnaire(Page):
    form_model = 'player'
    form_fields = ['understanding', 'doubts', 'suggestions']


page_sequence = [Demographics, FinalQuestionnaire]