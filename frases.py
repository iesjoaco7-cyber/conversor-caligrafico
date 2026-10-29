"""frases.py — Banco de frases para practicar (refranes y frases de dominio público)."""
import random

FRASES = [
    "Más vale tarde que nunca.",
    "Poco a poco se va lejos.",
    "El que busca, encuentra.",
    "No hay mal que por bien no venga.",
    "A buen entendedor, pocas palabras bastan.",
    "Despacio que estoy apurado.",
    "Quien siembra vientos recoge tempestades.",
    "La práctica hace al maestro.",
    "Cada día es una página en blanco.",
    "Escribir a mano es pensar más despacio.",
    "Hoy el cielo de Córdoba amaneció celeste.",
    "Una carta escrita a mano vale por mil mensajes.",
    "La paciencia es amarga, pero su fruto es dulce.",
    "Más vale maña que fuerza.",
    "En boca cerrada no entran moscas.",
    "Al mal tiempo, buena cara.",
    "El saber no ocupa lugar.",
    "Querido diario: hoy aprendí algo nuevo.",
    "Gracias por todo, con cariño.",
    "Feliz cumpleaños, que se cumplan todos tus deseos.",
    "Ñandú, pingüino y cigüeña viajan juntos.",
    "¿Quién escribió esta carta tan bonita?",
    "¡Qué lindo día para tomar unos mates!",
    "El veloz murciélago hindú comía feliz cardillo y kiwi.",
]

# Pangrama: contiene todas las letras, ideal para ver el estilo completo.
PANGRAMA = "El veloz murciélago hindú comía feliz cardillo y kiwi."


def frase_aleatoria(excluir: str | None = None) -> str:
    """Devuelve una frase distinta a la anterior, para que el botón siempre cambie algo."""
    opciones = [f for f in FRASES if f != excluir]
    return random.choice(opciones)
