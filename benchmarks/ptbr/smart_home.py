"""Espelho pt-BR do environment smart_home.

Tradução fiel, não adaptação: cada query pt diz exatamente o que a query en
dizia, para que o delta de acerto seja atribuível ao idioma e a mais nada.
Casos idiomáticos de português vivem em `stress.py`, fora deste score.

Os valores de enum seguem em inglês de propósito. O gabarito os carrega
('study', 'dim'), então traduzi-los invalidaria os casos; e o mapeamento
"escritório" -> `study` é justamente parte do que o braço pt/en mede.
"""

from typing import Annotated, Literal, Optional

import needle
from needle.environments import smart_home as EN

from ._mirror import build_cases

Room = Literal["kitchen", "living_room", "bedroom", "study"]


QUERIES = {
    # positive
    "turn on the kitchen lights": "liga a luz da cozinha",
    "switch off the lights in the bedroom": "desliga as luzes do quarto",
    "dim the living room lights to 35 percent": "diminui a luz da sala para 35 por cento",
    "turn on the study lights in warm white": "acende a luz do escritório em branco quente",
    "put the bedroom lights on in blue": "acende a luz do quarto em azul",
    "set the thermostat to 22 degrees": "coloca o termostato em 22 graus",
    "warm the house to 24 degrees": "aquece a casa para 24 graus",
    "cool the whole home down to 19 degrees": "resfria a casa toda para 19 graus",
    "turn on the bedroom fan": "liga o ventilador do quarto",
    "switch the study fan off": "desliga o ventilador do escritório",
    "turn on the living room fan at high speed": "liga o ventilador da sala na velocidade alta",
    "run the study fan on low": "liga o ventilador do escritório na velocidade baixa",
    "open the kitchen blinds": "abre a persiana da cozinha",
    "close the blinds in the living room": "fecha as persianas da sala",
    "open up the bedroom blinds": "abre as persianas do quarto",
    "start the robot vacuum": "liga o robô aspirador",
    "start vacuuming the bedroom": "começa a aspirar o quarto",
    "stop the robot vacuum": "para o robô aspirador",
    # missing
    "turn on the lights": "liga as luzes",
    "set the thermostat to something comfortable": "coloca o termostato numa temperatura agradável",
    "open the blinds": "abre as persianas",
    "turn the fan on": "liga o ventilador",
    # irrelevant
    "lock the back door": "tranca a porta dos fundos",
    "check whether the robot vacuum is charging": "verifica se o robô aspirador está carregando",
    "play some jazz in the living room": "toca um jazz na sala",
    # negation
    "don't turn on the study lights": "não acende a luz do escritório",
    "do not close the living room blinds": "não fecha as persianas da sala",
    "never run the vacuum while I am on a call": "nunca liga o aspirador enquanto eu estiver em ligação",
    # invalid
    "dim the bedroom lights to 150 percent": "diminui a luz do quarto para 150 por cento",
    "set the thermostat to 40 degrees": "coloca o termostato em 40 graus",
    # parallel
    "turn off the bedroom lights and set the thermostat to 18 degrees":
        "desliga a luz do quarto e coloca o termostato em 18 graus",
    "start the vacuum in the kitchen and open the living room blinds":
        "liga o aspirador na cozinha e abre as persianas da sala",
}


TEST_CASES = build_cases(EN, QUERIES)


# --- braço pt/pt: mesma superfície, descrições em português ----------------

@needle.tool
def control_lights(
    room: Room,
    action: Literal["on", "off", "dim"],
    brightness_percent: Annotated[Optional[int], needle.Field(ge=0, le=100)] = None,
    color: Optional[Literal["warm white", "cool white", "red", "green", "blue"]] = None,
):
    """Acende ou apaga a luz de um cômodo, diminui o brilho para uma porcentagem, ou define a cor. Pedido de cor implica acender. Nunca use para persianas, ventilador ou qualquer outro aparelho.

    Args:
        room: O cômodo a controlar. kitchen=cozinha, living_room=sala, bedroom=quarto, study=escritório.
        action: on para acender, off para apagar, dim para diminuir o brilho.
        brightness_percent: Brilho de 0 a 100. Pedido de diminuir com número tem de levar esse número nesta mesma chamada.
        color: A cor da luz; inclua apenas quando o usuário disser uma.
    """
    return {"ok": True, "room": room, "action": action,
            "brightness_percent": brightness_percent, "color": color}


@needle.tool
def set_thermostat(temperature: Annotated[int, needle.Field(ge=10, le=30)]):
    """Ajusta o termostato da casa para uma temperatura alvo em graus Celsius. Nunca controla ventilador, luz ou qualquer outro aparelho.

    Args:
        temperature: Temperatura alvo em graus Celsius.
    """
    return {"ok": True, "temperature": temperature}


@needle.tool
def control_fan(
    room: Literal["living_room", "bedroom", "study"],
    action: Literal["on", "off"],
    speed: Optional[Literal["low", "medium", "high"]] = None,
):
    """Liga ou desliga o ventilador de um cômodo, opcionalmente numa velocidade dita. Nunca mexe no termostato.

    Args:
        room: O cômodo cujo ventilador controlar. living_room=sala, bedroom=quarto, study=escritório.
        action: on para ligar, off para desligar.
        speed: Velocidade do ventilador; inclua apenas quando dita. low=baixa, medium=média, high=alta.
    """
    return {"ok": True, "room": room, "action": action, "speed": speed}


@needle.tool
def control_blinds(room: Room, action: Literal["open", "close"]):
    """Abre ou fecha a persiana de um único cômodo dito. Nunca escolha o cômodo por conta própria. Nunca use para luzes ou para o aspirador.

    Args:
        room: O cômodo cuja persiana mover. kitchen=cozinha, living_room=sala, bedroom=quarto, study=escritório.
        action: open para abrir, close para fechar.
    """
    return {"ok": True, "room": room, "action": action}


@needle.tool
def start_robot_vacuum(
    action: Literal["start", "stop", "dock"],
    room: Optional[Literal["kitchen", "living_room", "bedroom"]] = None,
):
    """Liga ou para o robô aspirador, ou manda ele voltar para a base para carregar.

    Args:
        action: start para ligar, stop para parar, dock para voltar à base.
        room: O cômodo a aspirar; inclua apenas ao iniciar uma limpeza num cômodo dito.
    """
    return {"ok": True, "action": action, "room": room}


TOOLS_PT = [control_lights, set_thermostat, control_fan, control_blinds, start_robot_vacuum]

SYSTEM_PT = (
    "Mapeie cada ação da casa explicitamente pedida e suportada para exatamente uma chamada "
    "declarada; nunca duplique uma ação. Não adivinhe alvos ou valores que faltam. Pedidos não "
    "suportados, inválidos, ambíguos ou negados não retornam chamada nenhuma."
)


# --- âncoras para o gate de grounding --------------------------------------
#
# Palavras pt-BR que sustentam cada valor de enum. Usadas por `--grounding`
# para recusar chamada cujo cômodo a frase não menciona -- o erro exato que o
# modelo base cometia, colapsando todo cômodo em `bedroom`.
#
# Só `room` está mapeado: é onde o erro se concentra, e âncora para verbo de
# ação (`on`/`off`) daria falso negativo em perífrase ("dá uma acendida"), que
# o modelo acerta e o gate não deve punir.
# O termo em inglês entra junto porque o gate roda nos TRÊS braços, inclusive
# `en/en`. Medido com âncoras só em português: en/en caiu de 75,0% para 53,1%
# com 13 recusas -- o gate condenava toda chamada inglesa por não achar
# "cozinha" em "turn on the kitchen lights". A âncora é sobre o referente, não
# sobre o idioma em que a frase foi escrita.
ANCHORS = {
    "room": {
        "kitchen": ("cozinha", "copa", "kitchen"),
        "living_room": ("sala", "living", "estar", "lounge"),
        "bedroom": ("quarto", "dormitorio", "dormitório", "suite", "suíte", "bedroom"),
        "study": ("escritorio", "escritório", "estudo", "estudos", "study"),
    },
}
