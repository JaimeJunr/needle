"""Espelho pt-BR do environment productivity.

Tradução fiel, não adaptação: cada query pt diz exatamente o que a query en
dizia, para que o delta de acerto seja atribuível ao idioma e a mais nada.
Casos idiomáticos de português vivem em `stress.py`, fora deste score.

Texto livre (mensagem, título, nota, frase de data/hora) vai em FREE_TEXT:
a query e o gabarito traduzem juntos, porque o Needle copia verbatim.
Prioridade é enum: a query usa 'alta'/'baixa', e o mapeamento para
`high`/`low` é parte do que o braço pt/en mede. Locais com nome próprio
(Riverside Library, Cafe Roma) ficam no original.
"""

from typing import Annotated, Literal, Optional

import needle
from needle.environments import productivity as EN

from ._mirror import build_cases

Phrase = Annotated[str, needle.Field(min_length=1, max_length=60)]


FREE_TEXT = {
    "25 minutes": "25 minutos",
    "90 seconds": "90 segundos",
    "9:15pm": "21:15",
    "10 minutes": "10 minutos",
    "water the plants": "regar as plantas",
    "6pm": "18h",
    "call Grandma": "ligar pra vovó",
    "Sunday morning": "domingo de manhã",
    "renew the car insurance": "renovar o seguro do carro",
    "tomorrow at noon": "amanhã ao meio-dia",
    "take my vitamins": "tomar minhas vitaminas",
    "8:15am": "8h15",
    "dentist appointment": "consulta no dentista",
    "tomorrow at 3pm": "amanhã às 15h",
    "team standup": "reunião diária do time",
    "Monday at 9am": "segunda às 9h",
    "book club": "clube do livro",
    "Wednesday at 7pm": "quarta às 19h",
    "lunch with Sam": "almoço com o Sam",
    "Friday at 1pm": "sexta às 13h",
    "renew my passport": "renovar meu passaporte",
    "descale the kettle": "descalcificar a chaleira",
    "file the insurance claim": "dar entrada no sinistro",
    "organize the garage": "organizar a garagem",
    "sunflower42 is the wifi password": "sunflower42 é a senha do wifi",
    "bring the hiking boots": "levar as botas de trilha",
    "Packing List": "Lista de Bagagem",
    "plant the tulip bulbs in October": "plantar os bulbos de tulipa em outubro",
    "Garden": "Jardim",
    "hydrate": "hidratar",
    "5pm": "17h",
    "buy candles": "comprar velas",
    "rent is due Friday": "o aluguel vence sexta",
}


QUERIES = {
    # positive
    "start a timer for 25 minutes": "liga um timer de 25 minutos",
    "run a timer for 90 seconds": "roda um timer de 90 segundos",
    "set a timer that goes off at 9:15pm": "programa um timer que dispara às 21:15",
    "remind me at 6pm to water the plants": "me lembra às 18h de regar as plantas",
    "set a reminder for Sunday morning to call Grandma":
        "cria um lembrete para domingo de manhã de ligar pra vovó",
    "remind me tomorrow at noon to renew the car insurance":
        "me lembra amanhã ao meio-dia de renovar o seguro do carro",
    "could you remind me at 8:15am to take my vitamins":
        "pode me lembrar às 8h15 de tomar minhas vitaminas",
    "add dentist appointment to my calendar tomorrow at 3pm":
        "adiciona consulta no dentista no meu calendário amanhã às 15h",
    "schedule team standup for Monday at 9am":
        "agenda reunião diária do time para segunda às 9h",
    "put book club on my calendar Wednesday at 7pm at Riverside Library":
        "coloca clube do livro no meu calendário quarta às 19h no Riverside Library",
    "schedule lunch with Sam for Friday at 1pm at Cafe Roma":
        "agenda almoço com o Sam para sexta às 13h no Cafe Roma",
    "add renew my passport to my to-do list":
        "adiciona renovar meu passaporte na minha lista de tarefas",
    "add descale the kettle to my tasks":
        "adiciona descalcificar a chaleira nas minhas tarefas",
    "add file the insurance claim as a high priority task":
        "adiciona dar entrada no sinistro como uma tarefa de prioridade alta",
    "add a low priority task to organize the garage":
        "adiciona uma tarefa de prioridade baixa de organizar a garagem",
    "make a note that sunflower42 is the wifi password":
        "faz uma nota de que sunflower42 é a senha do wifi",
    "save a note titled Packing List saying bring the hiking boots":
        "salva uma nota com o título Lista de Bagagem dizendo levar as botas de trilha",
    "write a note titled Garden that says plant the tulip bulbs in October":
        "escreve uma nota com o título Jardim que diz plantar os bulbos de tulipa em outubro",
    # missing
    "remind me to take out the recycling": "me lembra de tirar a reciclagem",
    "set a timer for the pasta": "programa um timer para o macarrão",
    "put dinner with Alex on my calendar": "coloca jantar com o Alex no meu calendário",
    "set a reminder about picking up the dry cleaning":
        "cria um lembrete sobre buscar a lavanderia",
    # irrelevant
    "email the shopping list to my roommate":
        "manda a lista de compras por e-mail pro meu colega de quarto",
    "check my calendar for this weekend": "confere meu calendário desse fim de semana",
    "delete the reminder about the oil change": "apaga o lembrete da troca de óleo",
    # negation
    "don't set a timer for 20 minutes": "não programa um timer de 20 minutos",
    "do not put yoga class on my calendar for Saturday at 8am":
        "não coloca aula de yoga no meu calendário sábado às 8h",
    "never remind me about the water bill again": "nunca mais me lembra da conta de água",
    # invalid
    "set a timer for negative 5 minutes": "programa um timer de 5 minutos negativos",
    "remind me yesterday at 4pm to submit the timesheet":
        "me lembra ontem às 16h de entregar a folha de ponto",
    # parallel
    "set a timer for 10 minutes and remind me at 5pm to hydrate":
        "liga um timer de 10 minutos e me lembra às 17h de hidratar",
    "add buy candles to my task list and note that rent is due Friday":
        "adiciona comprar velas na minha lista de tarefas e anota que o aluguel vence sexta",
}


TEST_CASES = build_cases(EN, QUERIES, free_text=FREE_TEXT)


# --- braço pt/pt: mesma superfície, descrições em português ----------------

@needle.tool
def set_timer(time_human: Phrase):
    """Programa um timer para a duração ou o horário de término dito.

    Args:
        time_human: A duração ou o horário alvo em formato legível, p.ex. '45 minutes', 'at 13:30'.
    """
    return {"ok": True, "time_human": time_human}


@needle.tool
def create_reminder(message: Annotated[str, needle.Field(min_length=1, max_length=120)], date_time_human: Phrase):
    """Cria um lembrete que dispara num horário dito. Um lembrete precisa de mensagem e de uma frase de hora; use add_task para afazeres sem data.

    Args:
        message: Do que ser lembrado, copiado palavra por palavra.
        date_time_human: A frase de data ou hora do usuário, copiada palavra por palavra.
    """
    return {"ok": True, "message": message, "date_time_human": date_time_human}


@needle.tool
def create_calendar_event(
    title: Annotated[str, needle.Field(min_length=1, max_length=120)],
    start_time_human: Phrase,
    location: Optional[Annotated[str, needle.Field(min_length=1, max_length=80)]] = None,
):
    """Cria um evento de calendário com título e horário de início. Copie os dois palavra por palavra; nunca reescreva nem resolva.

    Args:
        title: O título do evento copiado palavra por palavra.
        start_time_human: A frase de data ou hora de início copiada palavra por palavra.
        location: O local do evento; inclua apenas quando dito.
    """
    return {"ok": True, "title": title, "start_time_human": start_time_human, "location": location}


@needle.tool
def add_task(
    title: Annotated[str, needle.Field(min_length=1, max_length=120)],
    priority: Optional[Literal["low", "medium", "high"]] = None,
):
    """Adiciona uma tarefa no gerenciador. Tarefas não têm data; pedidos com data ou hora pertencem a create_reminder ou create_calendar_event.

    Args:
        title: A tarefa copiada palavra por palavra.
        priority: low, medium ou high; inclua apenas quando o usuário disser uma palavra de prioridade. low=baixa, medium=média, high=alta.
    """
    return {"ok": True, "title": title, "priority": priority}


@needle.tool
def create_note(
    text: Annotated[str, needle.Field(min_length=1, max_length=200)],
    title: Optional[Phrase] = None,
):
    """Salva uma nota livre. Notas guardam informação; nunca disparam alerta.

    Args:
        text: O conteúdo da nota copiado palavra por palavra.
        title: Um título curto; inclua apenas quando o usuário nomear um.
    """
    return {"ok": True, "text": text, "title": title}


TOOLS_PT = [set_timer, create_reminder, create_calendar_event, add_task, create_note]

SYSTEM_PT = (
    "Copie títulos, mensagens e frases de data ou hora ao pé da letra do usuário; "
    "nunca reescreva nem resolva elas. Mapeie cada pedido explicitamente suportado "
    "para exatamente uma chamada declarada. Não adivinhe valores que faltam. Pedidos "
    "não suportados, inválidos, ambíguos ou negados não retornam chamada nenhuma."
)
