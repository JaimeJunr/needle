"""Espelho pt-BR do environment kitchen_appliance.

Tradução fiel, não adaptação: cada query pt diz exatamente o que a query en
dizia, para que o delta de acerto seja atribuível ao idioma e a mais nada.
Casos idiomáticos de português vivem em `stress.py`, fora deste score.

Rótulos de timer (texto livre) vão em FREE_TEXT: a query e o gabarito
traduzem juntos, porque o Needle copia verbatim. Ciclos, ações da
cafeteira e nomes de aparelho são enum: a query usa 'econômico', 'forno',
e o mapeamento para `eco`/`oven` é parte do que o braço pt/en mede.
"""

from typing import Annotated, Literal, Optional

import needle
from needle.environments import kitchen_appliance as EN

from ._mirror import build_cases


FREE_TEXT = {
    "pasta": "macarrão",
    "brisket": "peito bovino",
    "eggs": "ovos",
    "cookies": "biscoitos",
}


QUERIES = {
    # positive
    "preheat the oven to 180 degrees": "preaquece o forno a 180 graus",
    "set the oven to 220 degrees": "coloca o forno em 220 graus",
    "bake at 200 degrees": "assa a 200 graus",
    "bring the oven up to 160 degrees": "sobe o forno pra 160 graus",
    "brew a fresh pot of coffee": "passa uma jarra de café fresco",
    "start brewing another batch of coffee": "começa a passar outro lote de café",
    "stop the coffee maker": "para a cafeteira",
    "keep my coffee warm": "mantém meu café quente",
    "run the dishwasher on the eco cycle": "liga a lava-louças no ciclo econômico",
    "start a heavy dishwasher cycle": "inicia um ciclo pesado da lava-louças",
    "run a quick cycle on the dishwasher": "roda um ciclo rápido na lava-louças",
    "set a pasta timer for 10 minutes": "coloca um timer de macarrão de 10 minutos",
    "start a 90 minute timer for the brisket": "inicia um timer de 90 minutos para o peito bovino",
    "give me a 5 minute timer for the eggs": "me dá um timer de 5 minutos para os ovos",
    "the cookies need a 12 minute timer": "os biscoitos precisam de um timer de 12 minutos",
    "check the oven": "verifica o forno",
    "check on the dishwasher": "dá uma olhada na lava-louças",
    "check the coffee maker for me": "verifica a cafeteira pra mim",
    # missing
    "heat up the oven for the garlic bread": "aquece o forno pro pão de alho",
    "set a cooking timer for the rice": "coloca um timer de cozinha para o arroz",
    "start a timer for 25 minutes": "inicia um timer de 25 minutos",
    "change the coffee maker setting": "muda a configuração da cafeteira",
    # irrelevant
    "defrost some chicken in the microwave": "descongela um frango no micro-ondas",
    "boil the kettle for tea": "ferve a chaleira pro chá",
    "turn the fridge down to 3 degrees": "abaixa a geladeira pra 3 graus",
    # negation
    "don't preheat the oven to 220 degrees tonight":
        "não preaquece o forno a 220 graus hoje à noite",
    "do not run the dishwasher on heavy today":
        "não liga a lava-louças no pesado hoje",
    "never brew coffee this late at night": "nunca passa café tão tarde da noite",
    # invalid
    "get the oven up to 300 degrees": "sobe o forno pra 300 graus",
    "set a stew timer for 500 minutes": "coloca um timer de ensopado de 500 minutos",
    # parallel
    "set the oven to 180 degrees and start a pizza timer for 15 minutes":
        "coloca o forno em 180 graus e inicia um timer de pizza de 15 minutos",
    "brew coffee and run the dishwasher on quick":
        "passa café e liga a lava-louças no rápido",
}


TEST_CASES = build_cases(EN, QUERIES, free_text=FREE_TEXT)


# --- braço pt/pt: mesma superfície, descrições em português ----------------

@needle.tool
def set_oven(temperature: Annotated[int, needle.Field(ge=50, le=250)]):
    """Preaquece ou ajusta o forno para uma temperatura em graus Celsius. Use get_appliance_status para conferir.

    Args:
        temperature: Temperatura alvo em graus Celsius.
    """
    return {"ok": True, "temperature": temperature}


@needle.tool
def control_coffee_maker(action: Literal["brew", "stop", "warm"]):
    """Controla a cafeteira. Nunca use para o forno ou para a lava-louças.

    Args:
        action: brew, stop ou warm. brew=passar, stop=parar, warm=manter quente.
    """
    return {"ok": True, "action": action}


@needle.tool
def start_dishwasher(cycle: Optional[Literal["eco", "heavy", "quick"]] = None):
    """Liga a lava-louças, opcionalmente num ciclo de lavagem dito.

    Args:
        cycle: O ciclo de lavagem; inclua apenas quando dito. eco=econômico, heavy=pesado, quick=rápido.
    """
    return {"ok": True, "cycle": cycle}


@needle.tool
def set_cooking_timer(
    label: Annotated[str, needle.Field(min_length=1, max_length=40)],
    minutes: Annotated[int, needle.Field(ge=1, le=360)],
):
    """Programa um timer de cozinha com nome.

    Args:
        label: Rótulo do timer, copiado do usuário.
        minutes: Duração do timer em minutos.
    """
    return {"ok": True, "label": label, "minutes": minutes}


@needle.tool
def get_appliance_status(appliance: Literal["oven", "coffee_maker", "dishwasher"]):
    """Lê o estado atual de um aparelho. Isso não muda nada; qualquer pedido de mudar configuração usa as outras tools.

    Args:
        appliance: Qual aparelho conferir. oven=forno, coffee_maker=cafeteira, dishwasher=lava-louças.
    """
    return {"ok": True, "appliance": appliance, "status": "idle"}


TOOLS_PT = [set_oven, control_coffee_maker, start_dishwasher, set_cooking_timer, get_appliance_status]

SYSTEM_PT = (
    "Mapeie cada ação de aparelho explicitamente pedida e suportada para exatamente uma chamada "
    "declarada; nunca duplique uma ação. Não adivinhe valores que faltam. Pedidos não "
    "suportados, inválidos, ambíguos ou negados não retornam chamada nenhuma."
)
