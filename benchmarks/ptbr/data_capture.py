"""Espelho pt-BR do environment data_capture.

Tradução fiel, não adaptação: cada query pt diz exatamente o que a query en
dizia, para que o delta de acerto seja atribuível ao idioma e a mais nada.
Casos idiomáticos de português vivem em `stress.py`, fora deste score.

Descrições de refeição (texto livre) vão em FREE_TEXT: a query e o gabarito
traduzem juntos, porque o Needle copia verbatim. Nomes, telefones, e-mails
e estabelecimentos são identificadores e ficam no original. Categoria e
tipo de refeição são enum: a query usa 'transporte', 'almoço', e o
mapeamento para `transport`/`lunch` é parte do que o braço pt/en mede.
"""

from typing import Annotated, Literal, Optional

import needle
from needle.environments import data_capture as EN

from ._mirror import build_cases


FREE_TEXT = {
    "grilled salmon with rice": "salmão grelhado com arroz",
    "leftover pad thai": "sobra de pad thai",
    "oatmeal with berries": "aveia com frutas vermelhas",
    "rice cakes with peanut butter": "biscoitos de arroz com pasta de amendoim",
    "turkey sandwich on rye": "sanduíche de peru no pão de centeio",
}


QUERIES = {
    # positive
    "add Maya Chen to my contacts": "adiciona Maya Chen nos meus contatos",
    "save Leo Park to contacts, phone 555-0134":
        "salva Leo Park nos contatos, telefone 555-0134",
    "create a contact for Nadia Osei, number 917-555-0188, email nadia@osei.dev":
        "cria um contato pra Nadia Osei, número 917-555-0188, e-mail nadia@osei.dev",
    "put Tomás Rivera in my contacts": "coloca Tomás Rivera nos meus contatos",
    "log an expense of 23 for transport": "registra uma despesa de 23 de transporte",
    "record an 85.99 groceries expense from FreshMart":
        "anota uma despesa de 85.99 de mercado do FreshMart",
    "track 142.75 spent on utilities": "registra 142.75 gastos em contas",
    "capture 260 in shopping spend from Uniqlo":
        "captura 260 de gasto em compras na Uniqlo",
    "log 18.75 for entertainment": "registra 18.75 de entretenimento",
    "log a meal, grilled salmon with rice":
        "registra uma refeição, salmão grelhado com arroz",
    "log lunch, leftover pad thai": "registra o almoço, sobra de pad thai",
    "record oatmeal with berries for breakfast":
        "anota aveia com frutas vermelhas no café da manhã",
    "jot down what i ate, rice cakes with peanut butter":
        "anota o que eu comi, biscoitos de arroz com pasta de amendoim",
    "log 750 ml of water": "registra 750 ml de água",
    "record 500 ml of water intake": "anota 500 ml de ingestão de água",
    "i drank 1200 ml of water, log it": "eu bebi 1200 ml de água, registra",
    "log my weight at 82.5 kg": "registra meu peso em 82.5 kg",
    "record a weight of 74 kg": "anota um peso de 74 kg",
    # missing
    "log an expense of 45 from this afternoon":
        "registra uma despesa de 45 dessa tarde",
    "record my transport spending from today as an expense":
        "anota meu gasto de transporte de hoje como despesa",
    "log my water intake from this morning":
        "registra minha ingestão de água dessa manhã",
    "log my current weight for me": "registra meu peso atual pra mim",
    # irrelevant
    "text Marcus to ask about his new number":
        "manda mensagem pro Marcus perguntando o número novo dele",
    "how much have i spent on groceries this month":
        "quanto eu gastei de mercado esse mês",
    "delete yesterday's lunch entry from the log":
        "apaga o registro do almoço de ontem",
    # negation
    "don't log the 15.40 i spent on transport":
        "não registra os 15.40 que eu gastei de transporte",
    "do not add Ravi Kumar at 415-555-0162 to my contacts":
        "não adiciona Ravi Kumar no 415-555-0162 nos meus contatos",
    "never log 79.4 kg as my weight": "nunca registra 79.4 kg como meu peso",
    # invalid
    "log my weight as 500 kg": "registra meu peso como 500 kg",
    "log 9000 ml of water for today": "registra 9000 ml de água de hoje",
    # parallel
    "log lunch, turkey sandwich on rye, and 600 ml of water":
        "registra o almoço, sanduíche de peru no pão de centeio, e 600 ml de água",
    "log my weight of 78.4 kg and 350 ml of water":
        "registra meu peso de 78.4 kg e 350 ml de água",
}


TEST_CASES = build_cases(EN, QUERIES, free_text=FREE_TEXT)


# --- braço pt/pt: mesma superfície, descrições em português ----------------

@needle.tool
def create_contact(
    name: Annotated[str, needle.Field(min_length=1, max_length=60)],
    phone: Optional[Annotated[str, needle.Field(pattern=r"^\+?[0-9][0-9 -]{5,17}$")]] = None,
    email: Optional[Annotated[str, needle.Field(format="email")]] = None,
):
    """Salva um contato novo. Copie o nome palavra por palavra e o número dígito por dígito; nunca invente nem complete.

    Args:
        name: Nome completo do contato, copiado palavra por palavra.
        phone: O número de telefone exatamente como dado; inclua apenas quando dito.
        email: O endereço de e-mail; inclua apenas quando dito.
    """
    return {"ok": True, "name": name, "phone": phone, "email": email}


@needle.tool
def log_expense(
    amount: Annotated[float, needle.Field(ge=0, le=100000)],
    category: Literal["food", "groceries", "transport", "entertainment", "utilities", "shopping"],
    merchant: Optional[Annotated[str, needle.Field(min_length=1, max_length=60)]] = None,
):
    """Registra dinheiro gasto. Anote só valores que o usuário disse; nunca estime.

    Args:
        amount: O valor como dito, só dígitos.
        category: A categoria de gasto que o usuário nomeou. food=comida, groceries=mercado, transport=transporte, entertainment=entretenimento, utilities=contas, shopping=compras.
        merchant: A loja ou o vendedor copiado palavra por palavra; inclua apenas quando nomeado.
    """
    return {"ok": True, "amount": amount, "category": category, "merchant": merchant}


@needle.tool
def log_meal(
    description: Annotated[str, needle.Field(min_length=1, max_length=120)],
    meal_type: Optional[Literal["breakfast", "lunch", "dinner", "snack"]] = None,
):
    """Registra uma refeição ou um alimento. Use log_expense para dinheiro gasto com comida.

    Args:
        description: O que foi comido, copiado palavra por palavra.
        meal_type: Qual refeição; inclua apenas quando dito. breakfast=café da manhã, lunch=almoço, dinner=jantar, snack=lanche.
    """
    return {"ok": True, "description": description, "meal_type": meal_type}


@needle.tool
def log_water_intake(amount_ml: Annotated[int, needle.Field(ge=1, le=5000)]):
    """Registra consumo de água no seu diário de água.

    Args:
        amount_ml: Quantidade de água em mililitros.
    """
    return {"ok": True, "amount_ml": amount_ml}


@needle.tool
def log_weight(weight_kg: Annotated[float, needle.Field(ge=20, le=300)]):
    """Registra uma medição de peso corporal em quilogramas.

    Args:
        weight_kg: O peso em quilogramas como dito.
    """
    return {"ok": True, "weight_kg": weight_kg}


TOOLS_PT = [create_contact, log_expense, log_meal, log_water_intake, log_weight]

SYSTEM_PT = (
    "Copie nomes, estabelecimentos e descrições ao pé da letra do usuário. Registre só "
    "valores que o usuário disse; nunca estime. Mapeie cada registro explicitamente "
    "suportado para exatamente uma chamada declarada. Pedidos não suportados, incompletos, "
    "ambíguos ou negados não retornam chamada nenhuma."
)
