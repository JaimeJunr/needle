"""Gerador do conjunto de treino pt-BR para o fine-tune LoRA.

Determinístico e sem API: o vocabulário sob teste é fechado (quatro cômodos,
cinco tools), então templates cobrem o espaço melhor do que amostragem de um
modelo grande, e o resultado é reproduzível bit a bit.

O que este treino ataca é o achado do benchmark: o modelo base escolhe a tool
certa e erra o argumento, colapsando todo cômodo português em `bedroom`. O
gargalo é vocabulário ausente, não gramática, e é isso que os exemplos ensinam.

Configuração espelhada do braço pt/en — tools e system em inglês, query em
português. É o caso realista (o dev descreve em inglês, o usuário fala
português) e o de melhor calibração de confiança no benchmark base.

LIMITE METODOLÓGICO, declarado de propósito: o hold-out abaixo garante que
nenhuma frase de avaliação seja treinada, mas treino e avaliação compartilham
domínio e templates. O número medido depois vale para "frases novas no mesmo
domínio" — que é o caso de uso real — e NÃO prova generalização para um
domínio novo. Ler o ganho como prova de generalização ampla seria exagero.
"""

import json
import unicodedata

from needle.environments import smart_home as EN

TOOLS = [fn._needle_tool for fn in EN.TOOLS]
SYSTEM = EN.SYSTEM

# Cada cômodo carrega seus sinônimos com a preposição correta ("da cozinha",
# "do quarto") e as variantes sem acento, que o benchmark mostrou serem o eixo
# mais quebrado de todos.
#
# A contagem por cômodo tem de ficar equilibrada: foi exatamente o viés de
# frequência que fez o modelo base colapsar todo cômodo em `bedroom`, e um
# conjunto desequilibrado reensinaria o mesmo erro. Por isso todos têm três
# variantes, contando a preposição alternativa ("na cozinha" além de "da
# cozinha"), que também é fraseado real.
ROOMS = {
    "kitchen": [("cozinha", "da"), ("cozinha", "na"), ("copa", "da")],
    "living_room": [("sala", "da"), ("sala de estar", "da"), ("sala", "na")],
    "bedroom": [("quarto", "do"), ("dormitório", "do"), ("quarto", "no")],
    "study": [("escritório", "do"), ("escritorio", "do"), ("escritório", "no")],
}

FAN_ROOMS = ("living_room", "bedroom", "study")
VACUUM_ROOMS = ("kitchen", "living_room", "bedroom")

LIGHT_ON = ("liga", "ligue", "ligar", "acende", "acenda", "acender",
            "deixa acesa", "pode ligar", "poe pra funcionar")
LIGHT_OFF = ("desliga", "desligue", "desligar", "apaga", "apague", "apagar",
             "deixa apagada", "pode desligar")
FAN_ON = ("liga", "ligue", "ligar", "aciona", "poe pra funcionar", "pode ligar")
FAN_OFF = ("desliga", "desligue", "desligar", "para", "pode desligar")
OPEN = ("abre", "abra", "abrir", "levanta", "pode abrir")
CLOSE = ("fecha", "feche", "fechar", "baixa", "pode fechar")

LIGHT_NOUN = ("a luz", "as luzes", "a lâmpada", "a luz", "as luz")
BLIND_NOUN = ("a persiana", "as persianas", "a cortina", "as persianas")
FAN_NOUN = ("o ventilador", "a ventoinha", "o ventilador")

COLORS = {"warm white": ("branco quente", "branca quente"),
          "cool white": ("branco frio", "branca fria"),
          "red": ("vermelho", "vermelha"),
          "green": ("verde", "verde"),
          "blue": ("azul", "azul")}

SPEEDS = {"low": ("baixa", "no mínimo", "fraquinho"),
          "medium": ("média", "no médio", "medio"),
          "high": ("alta", "no máximo", "no talo")}


def _normalise(text):
    stripped = "".join(
        ch for ch in unicodedata.normalize("NFD", text.casefold())
        if unicodedata.category(ch) != "Mn"
    )
    return " ".join("".join(ch if ch.isalnum() else " " for ch in stripped).split())


def _held_out():
    """Toda frase de avaliação, normalizada. Nada daqui pode entrar no treino."""
    from benchmarks import ptbr
    queries = set()
    for mirror in ptbr.MIRRORS.values():
        queries.update(mirror.QUERIES.values())
    queries.update(case["query"] for case in ptbr.stress.TEST_CASES)
    return {_normalise(q) for q in queries}


def _example(query, answers, reasoning):
    return {"query": query, "tools": TOOLS, "system": SYSTEM,
            "answers": answers, "reasoning": reasoning}


def _call(name, **arguments):
    return {"name": name, "arguments": arguments}


def _light_cases():
    out = []
    for room, names in ROOMS.items():
        for word, prep in names:
            for index, verb in enumerate(LIGHT_ON):
                noun = LIGHT_NOUN[index % 2]
                out.append(_example(
                    f"{verb} {noun} {prep} {word}",
                    [_call("control_lights", room=room, action="on")],
                    f"'{word}' identifica o cômodo {room}; '{verb}' pede acender, logo action=on"))
            for verb in LIGHT_OFF:
                out.append(_example(
                    f"{verb} {LIGHT_NOUN[0]} {prep} {word}",
                    [_call("control_lights", room=room, action="off")],
                    f"'{word}' identifica o cômodo {room}; '{verb}' pede apagar, logo action=off"))
            for percent in (10, 25, 40, 60, 75, 90):
                out.append(_example(
                    f"diminui {LIGHT_NOUN[0]} {prep} {word} para {percent} por cento",
                    [_call("control_lights", room=room, action="dim",
                           brightness_percent=percent)],
                    f"'{word}' é {room}; 'diminui' pede dim e {percent} vira brightness_percent"))
            for enum, words in COLORS.items():
                out.append(_example(
                    f"acende {LIGHT_NOUN[0]} {prep} {word} em {words[0]}",
                    [_call("control_lights", room=room, action="on", color=enum)],
                    f"'{word}' é {room}; '{words[0]}' é a cor {enum}; pedido de cor implica action=on"))
    return out


def _fan_cases():
    out = []
    for room in FAN_ROOMS:
        for word, prep in ROOMS[room]:
            for verb in FAN_ON:
                out.append(_example(
                    f"{verb} {FAN_NOUN[0]} {prep} {word}",
                    [_call("control_fan", room=room, action="on")],
                    f"'{word}' é {room}; '{verb}' pede ligar, logo action=on"))
            for verb in FAN_OFF:
                out.append(_example(
                    f"{verb} {FAN_NOUN[0]} {prep} {word}",
                    [_call("control_fan", room=room, action="off")],
                    f"'{word}' é {room}; '{verb}' pede desligar, logo action=off"))
            for enum, words in SPEEDS.items():
                out.append(_example(
                    f"liga {FAN_NOUN[0]} {prep} {word} na velocidade {words[0]}",
                    [_call("control_fan", room=room, action="on", speed=enum)],
                    f"'{word}' é {room}; '{words[0]}' é a velocidade {enum}"))
    return out


def _blind_cases():
    out = []
    for room, names in ROOMS.items():
        for word, prep in names:
            for verb in OPEN:
                out.append(_example(
                    f"{verb} {BLIND_NOUN[0]} {prep} {word}",
                    [_call("control_blinds", room=room, action="open")],
                    f"'{word}' é {room}; '{verb}' pede abrir"))
            for verb in CLOSE:
                out.append(_example(
                    f"{verb} {BLIND_NOUN[1]} {prep} {word}",
                    [_call("control_blinds", room=room, action="close")],
                    f"'{word}' é {room}; '{verb}' pede fechar"))
    return out


def _thermostat_cases():
    templates = ("coloca o termostato em {t} graus", "põe o termostato em {t} graus",
                 "poe o termostato a {t} graus", "ajusta o termostato para {t} graus",
                 "deixa a casa em {t} graus", "quero {t} graus em casa",
                 "ajusta a temperatura para {t} graus", "deixa a temperatura em {t} graus")
    out = []
    for index, temp in enumerate(range(10, 31)):
        for template in templates[index % 2::2]:
            out.append(_example(
                template.format(t=temp),
                [_call("set_thermostat", temperature=temp)],
                f"{temp} está entre 10 e 30, logo é temperature válido"))
    for phrase, temp in (("aquece a casa para 25 graus", 25),
                         ("esfria a casa para 18 graus", 18),
                         ("esquenta aqui pra 24 graus", 24),
                         ("resfria a casa toda para 20 graus", 20)):
        out.append(_example(phrase, [_call("set_thermostat", temperature=temp)],
                            f"{temp} é o alvo dito e está dentro dos limites"))
    return out


def _vacuum_cases():
    out = []
    for room in VACUUM_ROOMS:
        for word, prep in ROOMS[room]:
            out.append(_example(
                f"aspira {prep.replace('da', 'a').replace('do', 'o')} {word}",
                [_call("start_robot_vacuum", action="start", room=room)],
                f"'{word}' é {room}; pedido de aspirar num cômodo dito"))
            out.append(_example(
                f"manda o aspirador limpar {prep} {word}",
                [_call("start_robot_vacuum", action="start", room=room)],
                f"'{word}' é {room}; 'limpar' inicia uma limpeza"))
    for phrase, action in (("liga o aspirador", "start"), ("começa a aspirar", "start"),
                           ("liga o robô", "start"), ("manda o aspirador trabalhar", "start"),
                           ("aciona o aspirador", "start"), ("põe o aspirador pra rodar", "start"),
                           ("para o aspirador", "stop"), ("pausa o aspirador", "stop"),
                           ("desliga o robô aspirador", "stop"),
                           ("interrompe a limpeza", "stop"), ("para de aspirar", "stop"),
                           ("desliga o robô", "stop"),
                           ("manda o aspirador carregar", "dock"),
                           ("devolve o aspirador para a base", "dock"),
                           ("manda o robô voltar pra base", "dock"),
                           ("recolhe o aspirador", "dock"),
                           ("põe o aspirador pra carregar", "dock")):
        out.append(_example(phrase, [_call("start_robot_vacuum", action=action)],
                            f"ação {action} sem cômodo dito, logo room é omitido"))
    return out


def _negative_cases():
    """Negação, alvo ausente, valor inválido e fora de escopo.

    Sem estes o fine-tune destrói justamente as categorias que o gate de
    confiança hoje protege — e negação errada é o erro mais caro do conjunto.
    """
    out = []
    for room, names in ROOMS.items():
        for word, prep in names:
            # Metade abre com não/nao; a outra metade nega sem partícula
            # inicial, que é como o pt-BR nega de verdade e era a lacuna que
            # derrubou `negation` para 0/3 no experimento de uma epoch.
            for template in (f"não acende {LIGHT_NOUN[0]} {prep} {word}",
                             f"nao liga {LIGHT_NOUN[0]} {prep} {word}",
                             f"não liga {LIGHT_NOUN[0]} {prep} {word} não",
                             f"nao desliga {FAN_NOUN[0]} {prep} {word}",
                             f"não fecha {BLIND_NOUN[0]} {prep} {word}",
                             f"não abre {BLIND_NOUN[0]} {prep} {word} não",
                             f"nao mexe {prep} {word}",
                             f"não precisa acender {LIGHT_NOUN[0]} {prep} {word}",
                             f"deixa {LIGHT_NOUN[0]} {prep} {word} quieta",
                             f"deixa quieto {FAN_NOUN[0]} {prep} {word}",
                             f"nem vem abrir {BLIND_NOUN[0]} {prep} {word}",
                             f"nem pensa em ligar {FAN_NOUN[0]} {prep} {word}",
                             f"esquece {BLIND_NOUN[0]} {prep} {word}",
                             f"esquece {LIGHT_NOUN[0]} {prep} {word} por hoje",
                             f"melhor nao mexer {prep} {word}",
                             f"de jeito nenhum acende {LIGHT_NOUN[0]} {prep} {word}",
                             f"pode deixar {LIGHT_NOUN[0]} {prep} {word} como está",
                             f"tira a mão {prep} {word}"):
                out.append(_example(template, [],
                                    "pedido negado: nenhuma chamada deve ser emitida"))
    for phrase in ("liga a luz", "acende as luzes", "desliga o ventilador",
                   "abre a persiana", "fecha as cortinas", "liga o ventilador",
                   "diminui a luz", "apaga a luz"):
        out.append(_example(phrase, [],
                            "o cômodo não foi dito; adivinhar o alvo é proibido"))
    for phrase in ("coloca o termostato numa temperatura boa",
                   "deixa a casa mais confortável", "abaixa um pouco a luz da sala",
                   "deixa o quarto mais claro"):
        out.append(_example(phrase, [], "valor vago, sem número: não há argumento a preencher"))
    for phrase in ("coloca o termostato em 45 graus", "coloca o termostato em 5 graus",
                   "diminui a luz da sala para 200 por cento",
                   "diminui a luz do quarto para 1.500 por cento",
                   "coloca o termostato em 38 graus"):
        out.append(_example(phrase, [], "valor fora dos limites declarados: nenhuma chamada"))
    for phrase in ("tranca a porta da frente", "toca uma música na sala",
                   "qual a temperatura lá fora", "o aspirador está carregando?",
                   "manda mensagem pro João", "liga a televisão da sala",
                   "faz um café", "abre o portão da garagem",
                   "que horas são", "acende a luz do banheiro",
                   "liga o chuveiro", "abre a janela do quarto",
                   "qual a previsão do tempo", "coloca um alarme pras 7",
                   "liga o ar condicionado do quarto", "desliga a geladeira",
                   "a luz da sala está acesa?", "quanto gastei de energia",
                   "liga o som da sala", "aspira o teto",
                   "fecha a porta da cozinha", "liga a luz do corredor"):
        out.append(_example(phrase, [], "nenhuma tool declarada cobre esse pedido"))
    for phrase in ("deixa a luz mais ou menos", "põe o ventilador numa boa velocidade",
                   "ajusta a persiana um pouco", "deixa a casa agradável",
                   "coloca o termostato no normal", "deixa a luz do jeito que eu gosto",
                   "aspira quando der", "deixa mais escuro ali",
                   "deixa a temperatura boa pra dormir", "clareia um pouco aqui",
                   "deixa o ventilador numa velocidade gostosa",
                   "ajusta tudo pro modo noite", "deixa a luz fraquinha",
                   "coloca uma temperatura de inverno",
                   "deixa a persiana meio aberta", "põe a luz num tom agradável"):
        out.append(_example(phrase, [], "pedido vago: nenhum valor concreto a preencher"))
    for phrase in ("coloca o termostato em 100 graus", "coloca o termostato em 0 graus",
                   "diminui a luz da cozinha para 300 por cento",
                   "coloca o termostato em 9 graus", "coloca o termostato em 31 graus",
                   "diminui a luz do escritório para -10 por cento"):
        out.append(_example(phrase, [], "valor fora dos limites declarados: nenhuma chamada"))
    return out


def _parallel_cases():
    out = []
    pairs = (("kitchen", "living_room"), ("bedroom", "study"), ("living_room", "bedroom"))
    for first, second in pairs:
        w1, p1 = ROOMS[first][0]
        w2, p2 = ROOMS[second][0]
        out.append(_example(
            f"apaga a luz {p1} {w1} e abre a persiana {p2} {w2}",
            [_call("control_lights", room=first, action="off"),
             _call("control_blinds", room=second, action="open")],
            f"duas ações independentes: luz em {first} e persiana em {second}"))
        out.append(_example(
            f"acende a luz {p1} {w1} e fecha a persiana {p2} {w2}",
            [_call("control_lights", room=first, action="on"),
             _call("control_blinds", room=second, action="close")],
            f"duas ações independentes: luz em {first} e persiana em {second}"))
    return out


def _thin_negatives(examples, negative_ratio):
    """Subamostra negativos até a proporção pedida, preservando variedade.

    Existe para o braço de controle do experimento: comparar 28% contra 15,6%
    de negativos exige que TUDO o mais seja idêntico. Gerar a variante por um
    segundo arquivo mediria drift entre arquivos, não o efeito da proporção.

    A amostragem é por passo constante sobre a lista, não aleatória: além de
    determinística, ela varre os blocos na ordem em que foram gerados
    (negação, alvo ausente, valor vago, fora de escopo), então nenhum tipo de
    recusa some inteiro -- o que aconteceria ao cortar os N primeiros.
    """
    positives = [ex for ex in examples if ex["answers"]]
    negatives = [ex for ex in examples if not ex["answers"]]
    if not negatives or negative_ratio >= len(negatives) / len(examples):
        return examples
    target = round(negative_ratio * len(positives) / (1 - negative_ratio))
    target = max(1, min(target, len(negatives)))
    stride = len(negatives) / target
    keep = {id(negatives[min(int(i * stride), len(negatives) - 1)]) for i in range(target)}
    return [ex for ex in examples if ex["answers"] or id(ex) in keep]


def build(negative_ratio=None):
    """Monta o conjunto, removendo qualquer frase que colida com a avaliação.

    `negative_ratio` produz a variante de controle (ex.: 0.156 reproduz a
    proporção do primeiro experimento); None entrega o conjunto cheio.
    """
    raw = (_light_cases() + _fan_cases() + _blind_cases() + _thermostat_cases()
           + _vacuum_cases() + _negative_cases() + _parallel_cases())
    held_out = _held_out()
    seen = set()
    examples = []
    for ex in raw:
        key = _normalise(ex["query"])
        if key in held_out or key in seen:
            continue
        seen.add(key)
        examples.append(ex)
    if negative_ratio is not None:
        examples = _thin_negatives(examples, negative_ratio)
    return examples


def write_jsonl(examples, path):
    with open(path, "w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(json.dumps(ex, ensure_ascii=False) + "\n")
    return path


if __name__ == "__main__":
    import sys

    examples = build()
    out = sys.argv[1] if len(sys.argv) > 1 else "ptbr_train.jsonl"
    write_jsonl(examples, out)
    empty = sum(1 for e in examples if not e["answers"])
    print(f"{len(examples)} exemplos -> {out} ({empty} negativos, "
          f"{100.0 * empty / len(examples):.1f}%)")
