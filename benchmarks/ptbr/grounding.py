"""Gate de grounding: recusa chamada cujo argumento a frase não sustenta.

Por que existe: o fine-tune não atualiza a cabeça de confiança, então pesos
tunados devolvem `confidence = None` e o gate de confiança — que no modelo base
convertia erro em recusa — deixa de existir. Sem rede, o modelo tunado acerta
mais e erra com convicção.

Três substitutos foram medidos contra o mesmo conjunto, cruzando a avaliação do
base com a do tunado v2 caso a caso:

    gate                      espelho            estresse
    (nenhum)                  65,6%  4 críticos  50,0%  4 críticos
    confiança do base         46,9%  0           45,5%  0
    concordância base/tunado  46,9%  1           50,0%  0
    grounding lexical         68,8%  3           59,1%  2

Os dois primeiros compram segurança pagando acerto. A confiança do base nem
sequer discrimina: AUC 0,552 no espelho (0,5 é uma moeda), porque em português
ela fica uniformemente perto de zero, inclusive nos casos que o tunado acerta.

O grounding é o único que melhora as duas colunas, e a razão é que ele ataca o
erro exato diagnosticado no início do trabalho: o modelo escolhe a tool certa e
inventa o argumento, colapsando todo cômodo português em `bedroom`. Uma chamada
cujo cômodo não aparece na frase vira recusa — que, nos casos `missing`, era
justamente a resposta certa.

Custo: zero inferência extra. É comparação de texto.
"""

import re
import unicodedata


def _normalise(text):
    """Minúsculas, sem acento, pontuação virando espaço.

    Sem isso o gate puniria 'escritorio' digitado sem acento, que é entrada
    normal de teclado de celular e o eixo mais frágil do modelo.
    """
    stripped = "".join(
        ch for ch in unicodedata.normalize("NFD", str(text).casefold())
        if unicodedata.category(ch) != "Mn"
    )
    return " ".join("".join(ch if ch.isalnum() else " " for ch in stripped).split())


def _mentions(haystack, anchor):
    """Casa a âncora como palavra inteira.

    Busca por substring casaria 'sala' dentro de 'salada' e fabricaria o
    grounding que este módulo existe para verificar.
    """
    return re.search(rf"(?<!\w){re.escape(anchor)}(?!\w)", haystack) is not None


def is_grounded(query, calls, anchors):
    """True se toda chamada tem âncora lexical na frase.

    `anchors` mapeia nome-de-argumento -> {valor: (palavras que o sustentam)}.
    Argumento sem âncoras declaradas, ou valor fora do mapa, passa sem opinião:
    mapa incompleto não é evidência de alucinação, e transformar silêncio em
    recusa inventaria uma segurança que não foi medida.
    """
    normalised = _normalise(query)
    for call in calls:
        for name, value in call.get("arguments", {}).items():
            candidates = anchors.get(name, {}).get(value)
            if not candidates:
                continue
            if not any(_mentions(normalised, _normalise(word)) for word in candidates):
                return False
    return True
