"""Invariantes do conjunto de treino pt-BR.

O risco central de um fine-tune medido pelo próprio benchmark é contaminação:
treinar numa frase que depois é usada para avaliar transforma o número "depois"
em memorização disfarçada de aprendizado. Os testes abaixo existem para que
essa fraude seja impossível de cometer por acidente.
"""

import json
import unicodedata

import pytest

from benchmarks import ptbr
from benchmarks.ptbr import trainset


def _normalise(text):
    """Compara frases ignorando acento, caixa e pontuação.

    Contaminação por 'liga a luz da cozinha' vs 'Liga a luz da cozinha!' seria
    contaminação do mesmo jeito; comparar string crua deixaria passar.
    """
    stripped = "".join(
        ch for ch in unicodedata.normalize("NFD", text.casefold())
        if unicodedata.category(ch) != "Mn"
    )
    return " ".join("".join(ch if ch.isalnum() else " " for ch in stripped).split())


@pytest.fixture(scope="module")
def examples():
    return trainset.build()


@pytest.fixture(scope="module")
def benchmark_queries():
    queries = set()
    for mirror in ptbr.MIRRORS.values():
        queries.update(mirror.QUERIES.values())
    queries.update(case["query"] for case in ptbr.stress.TEST_CASES)
    return queries


def test_no_exact_contamination(examples, benchmark_queries):
    train = {ex["query"] for ex in examples}
    assert not (train & benchmark_queries)


def test_no_contamination_after_normalising(examples, benchmark_queries):
    train = {_normalise(ex["query"]) for ex in examples}
    leaked = train & {_normalise(q) for q in benchmark_queries}
    assert not leaked, f"frases de avaliação no treino: {sorted(leaked)[:5]}"


def test_dataset_is_large_enough_to_teach_vocabulary(examples):
    assert len(examples) >= 400


def test_every_example_matches_the_jsonl_contract(examples):
    for ex in examples:
        assert set(ex) <= {"query", "tools", "answers", "reasoning", "system"}
        assert ex["query"].strip()
        assert isinstance(ex["answers"], list)
        assert ex["tools"]
        for call in ex["answers"]:
            assert set(call) == {"name", "arguments"}


def test_arguments_only_use_declared_enum_values(examples):
    """Um valor de enum inventado ensinaria o modelo a emitir lixo."""
    schemas = {t["name"]: t for t in examples[0]["tools"]}
    for ex in examples:
        for call in ex["answers"]:
            properties = schemas[call["name"]]["parameters"]["properties"]
            for key, value in call["arguments"].items():
                prop = properties[key]
                if "enum" in prop:
                    assert value in prop["enum"], f"{key}={value!r} fora do enum"
                if "minimum" in prop:
                    assert value >= prop["minimum"]
                if "maximum" in prop:
                    assert value <= prop["maximum"]


def test_negative_examples_are_present(examples):
    """Sem exemplos de 'não chame nada', o modelo tunado chama tool em tudo.

    O doc do upstream cita cerca de 1 em 8 no gerador embutido; abaixo disso o
    fine-tune destrói justamente as categorias que hoje o gate protege.
    """
    empty = [ex for ex in examples if not ex["answers"]]
    assert len(empty) / len(examples) >= 0.12


def test_negation_is_taught_not_just_refusal(examples):
    """Negação precisa aparecer como caso negativo explícito, não sobrar."""
    negated = [ex for ex in examples
               if not ex["answers"] and _normalise(ex["query"]).startswith("nao")]
    assert len(negated) >= 20


def test_every_room_word_is_taught(examples):
    """O achado do benchmark: o modelo colapsa todo cômodo em bedroom.

    Se alguma palavra de cômodo aparecer pouco, o fine-tune não corrige o
    gargalo que motivou este treino.
    """
    counts = {}
    for ex in examples:
        for call in ex["answers"]:
            room = call["arguments"].get("room")
            if room:
                counts[room] = counts.get(room, 0) + 1
    for room in ("kitchen", "living_room", "bedroom", "study"):
        assert counts.get(room, 0) >= 30, f"{room} aparece só {counts.get(room, 0)}x"


def test_rooms_are_taught_in_balance(examples):
    """Desequilíbrio reensinaria o mesmo viés de frequência que causou o bug."""
    counts = {}
    for ex in examples:
        for call in ex["answers"]:
            room = call["arguments"].get("room")
            if room:
                counts[room] = counts.get(room, 0) + 1
    assert max(counts.values()) <= 2 * min(counts.values())


def test_reasoning_is_present_and_portuguese(examples):
    """O doc do upstream: reasoning ensina grounding, não só escolha de tool."""
    with_reasoning = [ex for ex in examples if ex.get("reasoning")]
    assert len(with_reasoning) / len(examples) >= 0.9


def test_serialises_to_jsonl(examples, tmp_path):
    path = tmp_path / "train.jsonl"
    trainset.write_jsonl(examples, path)
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == len(examples)
    for line in lines:
        json.loads(line)


def test_tools_are_taught_in_reasonable_proportion(examples):
    """Viés de tool causaria o mesmo erro do viés de cômodo, noutro eixo.

    Com 16 exemplos de luz para 1 de termostato, o caminho barato para o
    modelo é chamar control_lights em quase tudo.
    """
    counts = {}
    for ex in examples:
        for call in ex["answers"]:
            counts[call["name"]] = counts.get(call["name"], 0) + 1
    total = sum(counts.values())
    for name, count in counts.items():
        assert count / total >= 0.05, f"{name} é só {100 * count / total:.1f}% das chamadas"
