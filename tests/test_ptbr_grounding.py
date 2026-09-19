"""Invariantes do gate de grounding.

O fine-tune não atualiza a cabeça de confiança, então pesos tunados perdem o
gate que convertia erro em recusa. Medido: a confiança do modelo BASE não
substitui essa rede (AUC 0.552 no espelho, contra 0.5 de uma moeda), e exigir
concordância base/tunado custa 19 pontos de acerto. O grounding lexical é o
único que melhora acerto E reduz falha crítica ao mesmo tempo, porque ataca o
erro diagnosticado no modelo base: emitir um cômodo que a frase não menciona.
"""

import pytest

from benchmarks.ptbr import grounding


ANCHORS = {"room": {"kitchen": ("cozinha", "copa"), "bedroom": ("quarto",)}}


def _call(**arguments):
    return {"name": "control_lights", "arguments": arguments}


def test_call_with_anchor_in_query_is_grounded():
    assert grounding.is_grounded("liga a luz da cozinha", [_call(room="kitchen")], ANCHORS)


def test_call_inventing_a_room_is_not_grounded():
    """O erro que motivou o gate: o modelo emite bedroom sem a frase dizer."""
    assert not grounding.is_grounded("liga a luz da cozinha", [_call(room="bedroom")], ANCHORS)


def test_anchor_matches_without_accents():
    """Entrada de teclado de celular perde acento; o gate não pode punir isso."""
    assert grounding.is_grounded("liga a luz do escritorio",
                                 [_call(room="study")],
                                 {"room": {"study": ("escritório",)}})


def test_anchor_matches_regardless_of_case_and_punctuation():
    assert grounding.is_grounded("Liga a luz da COZINHA!", [_call(room="kitchen")], ANCHORS)


def test_empty_call_list_is_grounded():
    """Recusar nunca é infundado."""
    assert grounding.is_grounded("qualquer coisa", [], ANCHORS)


def test_argument_without_declared_anchors_is_left_alone():
    """Sem âncora declarada para o campo, o gate não opina — não inventa recusa."""
    assert grounding.is_grounded("liga a luz", [_call(action="on")], ANCHORS)


def test_unknown_enum_value_is_left_alone():
    """Valor fora do mapa não é evidência de alucinação; só de mapa incompleto."""
    assert grounding.is_grounded("liga a luz do porão", [_call(room="basement")], ANCHORS)


def test_any_ungrounded_call_condemns_the_whole_turn():
    """Uma chamada inventada junto de uma boa ainda é uma ação errada."""
    calls = [_call(room="kitchen"), _call(room="bedroom")]
    assert not grounding.is_grounded("liga a luz da cozinha", calls, ANCHORS)


def test_substring_anchor_does_not_match_across_word_boundary():
    """'sala' não pode casar dentro de 'salada' — seria fabricar grounding."""
    assert not grounding.is_grounded("prepara uma salada",
                                     [_call(room="living_room")],
                                     {"room": {"living_room": ("sala",)}})


def test_anchors_must_cover_the_english_term_too():
    """O gate roda também no braço en/en, cuja query não tem palavra pt.

    Medido: com âncoras só em português, en/en caiu de 75,0% para 53,1% com
    13 recusas — o gate condenava toda chamada inglesa por não achar 'cozinha'
    em 'turn on the kitchen lights'. Âncora é sobre o referente, não sobre o
    idioma da frase.
    """
    from benchmarks.ptbr import smart_home
    for value, words in smart_home.ANCHORS["room"].items():
        assert any(w in value or value.split("_")[0] in w for w in words), (
            f"{value} não tem âncora que cubra a query em inglês: {words}"
        )
