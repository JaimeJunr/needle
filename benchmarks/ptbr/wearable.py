"""Espelho pt-BR do environment wearable.

Tradução fiel, não adaptação: cada query pt diz exatamente o que a query en
dizia, para que o delta de acerto seja atribuível ao idioma e a mais nada.
Casos idiomáticos de português vivem em `stress.py`, fora deste score.

Texto livre da resposta vai em FREE_TEXT: a query e o gabarito traduzem
juntos, porque o Needle copia verbatim. Remetentes são enum (Maya, Leo,
Dr. Patel, Cactus Team) e ficam no original. Tipos de treino são enum: a
query usa 'corrida', 'natação', e o mapeamento para `running`/`swimming`
é parte do que o braço pt/en mede.
"""

from typing import Annotated, Literal

import needle
from needle.environments import wearable as EN

from ._mirror import build_cases

Sender = Literal["Maya", "Leo", "Dr. Patel", "Cactus Team"]


FREE_TEXT = {
    "be there in 10 minutes": "chego em 10 minutos",
    "See you Thursday": "Até quinta-feira",
    "the build is green": "o build está verde",
    "lunch works for me": "almoço serve pra mim",
    "almost home": "quase em casa",
}


QUERIES = {
    # positive
    "reply to Maya saying be there in 10 minutes":
        "responde a Maya dizendo chego em 10 minutos",
    "reply to Dr. Patel with See you Thursday":
        "responde ao Dr. Patel com Até quinta-feira",
    "answer the Cactus Team message saying the build is green":
        "responde a mensagem da Cactus Team dizendo o build está verde",
    "send Leo a reply that says lunch works for me":
        "manda pro Leo uma resposta que diz almoço serve pra mim",
    "dismiss the notification from Leo": "dispensa a notificação do Leo",
    "swipe away the alert from Maya": "arrasta o alerta da Maya",
    "clear the Dr. Patel notification": "limpa a notificação do Dr. Patel",
    "get rid of the Cactus Team notification": "tira a notificação da Cactus Team",
    "start a running workout": "inicia um treino de corrida",
    "begin a swimming session on my watch": "começa uma sessão de natação no meu relógio",
    "kick off some strength training": "começa um treino de força",
    "track a cycling workout": "registra um treino de ciclismo",
    "go ahead and start a walking workout": "pode iniciar um treino de caminhada",
    "end my workout": "encerra meu treino",
    "finish the current workout session": "termina a sessão de treino atual",
    "wrap up my workout now": "finaliza meu treino agora",
    "find my phone": "acha meu celular",
    "make my phone ring so I can locate it": "faz meu celular tocar pra eu achar ele",
    # missing
    "send a reply to Maya": "manda uma resposta pra Maya",
    "dismiss the latest notification": "dispensa a última notificação",
    "start a workout": "inicia um treino",
    "reply saying I am stuck in a meeting": "responde dizendo que estou preso numa reunião",
    # irrelevant
    "check my heart rate on the watch": "confere minha frequência cardíaca no relógio",
    "call Maya from my watch": "liga pra Maya pelo relógio",
    "show my step count for today": "mostra minha contagem de passos de hoje",
    # negation
    "don't reply to the message from Leo": "não responde a mensagem do Leo",
    "do not start a running workout yet": "não inicia um treino de corrida ainda",
    "never dismiss notifications from Dr. Patel":
        "nunca dispensa notificações do Dr. Patel",
    # invalid
    "reply to Priya saying happy birthday": "responde a Priya dizendo feliz aniversário",
    "start a pilates workout": "inicia um treino de pilates",
    # parallel
    "dismiss the notification from Leo and start a strength workout":
        "dispensa a notificação do Leo e inicia um treino de força",
    "find my phone and reply to Maya saying almost home":
        "acha meu celular e responde a Maya dizendo quase em casa",
}


TEST_CASES = build_cases(EN, QUERIES, free_text=FREE_TEXT)


# --- braço pt/pt: mesma superfície, descrições em português ----------------

@needle.tool
def reply_to_notification(notification_match: Sender, text: Annotated[str, needle.Field(min_length=1, max_length=240)]):
    """Responde a uma notificação de mensagem de um remetente conhecido. Copie o texto da resposta palavra por palavra, preservando a capitalização. Use dismiss_notification para limpar uma sem responder.

    Args:
        notification_match: De quem é a notificação.
        text: A mensagem de resposta copiada palavra por palavra.
    """
    return {"ok": True, "notification_match": notification_match, "text": text}


@needle.tool
def dismiss_notification(notification_match: Sender):
    """Dispensa a notificação de um remetente sem responder.

    Args:
        notification_match: De quem é a notificação a dispensar.
    """
    return {"ok": True, "notification_match": notification_match}


@needle.tool
def start_workout(workout_type: Literal["running", "walking", "cycling", "swimming", "strength", "yoga"]):
    """Começa a registrar um treino de um tipo explicitamente nomeado: running, walking, cycling, swimming, strength ou yoga. Use end_workout para encerrar um que já está rolando.

    Args:
        workout_type: O tipo de treino que o usuário nomeou. running=corrida, walking=caminhada, cycling=ciclismo, swimming=natação, strength=força, yoga=ioga.
    """
    return {"ok": True, "workout_type": workout_type}


@needle.tool
def end_workout():
    """Encerra a sessão de treino atual. Começar um novo é start_workout. Não recebe argumentos."""
    return {"ok": True, "state": "ended"}


@needle.tool
def find_my_phone():
    """Faz o celular tocar para você achá-lo. Não recebe argumentos."""
    return {"ok": True, "ringing": True}


TOOLS_PT = [reply_to_notification, dismiss_notification, start_workout, end_workout, find_my_phone]

SYSTEM_PT = (
    "Copie o texto da resposta ao pé da letra, preservando a capitalização. Mapeie cada "
    "ação do relógio explicitamente pedida e suportada para exatamente uma chamada "
    "declarada. Não adivinhe valores que faltam. Pedidos não suportados, inválidos, "
    "ambíguos ou negados não retornam chamada nenhuma."
)
