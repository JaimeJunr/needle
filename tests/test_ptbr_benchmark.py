"""Invariantes do benchmark pt-BR.

O valor do espelho está inteiramente na paridade: se um caso pt divergir do
seu original en em gabarito, categoria ou contagem, o delta medido deixa de
ser "efeito do idioma" e vira ruído de tradução. Estes testes guardam isso.
"""

import pytest

from benchmarks import ptbr
from needle import environments

CATEGORIES = {"positive", "missing", "irrelevant", "negation", "invalid", "parallel"}


@pytest.fixture(params=sorted(ptbr.MIRRORS))
def mirror(request):
    return ptbr.MIRRORS[request.param]


def test_mirror_targets_a_real_environment(mirror):
    assert mirror.EN.__name__ in {m.__name__ for m in environments.ENVIRONMENTS.values()}


def test_every_english_query_has_one_translation(mirror):
    """Sem sobra nem falta: tradução órfã denuncia query que mudou no upstream."""
    en_queries = [case["query"] for case in mirror.EN.TEST_CASES]
    assert set(mirror.QUERIES) == set(en_queries)
    assert len(mirror.QUERIES) == len(en_queries)


def test_translations_are_not_copies(mirror):
    """Um caso deixado em inglês passaria silenciosamente e inflaria o score pt."""
    for en_query, pt_query in mirror.QUERIES.items():
        assert pt_query.strip(), f"tradução vazia para {en_query!r}"
        assert pt_query.strip().lower() != en_query.strip().lower(), (
            f"caso não traduzido: {en_query!r}"
        )


def test_cases_preserve_gold_standard(mirror):
    """O gabarito pt é o gabarito en, salvo o texto livre declarado.

    Texto livre é a única diferença permitida, e só para os valores que o
    módulo declara em FREE_TEXT: o Needle copia texto livre verbatim da frase,
    então traduzir a query sem traduzir o valor esperado exigiria do modelo que
    copiasse inglês de dentro de uma frase portuguesa. Tudo o mais -- nome da
    tool, conjunto de argumentos, enum, número -- continua idêntico.
    """
    free_text = getattr(mirror, "FREE_TEXT", {})
    for pt_case, en_case in zip(mirror.TEST_CASES, mirror.EN.TEST_CASES):
        assert len(pt_case["calls"]) == len(en_case["calls"])
        for pt_call, en_call in zip(pt_case["calls"], en_case["calls"]):
            assert pt_call["name"] == en_call["name"]
            assert set(pt_call["arguments"]) == set(en_call["arguments"])
            for key, en_value in en_call["arguments"].items():
                pt_value = pt_call["arguments"][key]
                expected = free_text.get(en_value, en_value) if isinstance(en_value, str) else en_value
                assert pt_value == expected, (
                    f"{key}: {pt_value!r} != {expected!r} -- valor mudou sem estar em FREE_TEXT"
                )
        assert pt_case["category"] == en_case["category"]
        assert pt_case.get("critical", False) == en_case.get("critical", False)
        assert pt_case["query"] == mirror.QUERIES[en_case["query"]]


def test_case_count_matches(mirror):
    assert len(mirror.TEST_CASES) == len(mirror.EN.TEST_CASES)


def test_categories_survive_translation(mirror):
    assert {case["category"] for case in mirror.TEST_CASES} == CATEGORIES


def test_translated_tools_keep_the_machine_readable_surface(mirror):
    """Descrição traduz; nome, tipo e valor de enum NÃO.

    O gabarito carrega os valores de enum ('kitchen', 'dim'). Traduzir um
    deles invalidaria todos os casos daquele tool de uma vez.
    """
    en_schemas = {fn._needle_tool["name"]: fn._needle_tool for fn in mirror.EN.TOOLS}
    pt_schemas = {fn._needle_tool["name"]: fn._needle_tool for fn in mirror.TOOLS_PT}

    assert set(pt_schemas) == set(en_schemas)
    for name, pt_schema in pt_schemas.items():
        en_props = en_schemas[name]["parameters"]["properties"]
        pt_props = pt_schema["parameters"]["properties"]
        assert set(pt_props) == set(en_props), f"parâmetros divergem em {name}"
        for key, pt_prop in pt_props.items():
            assert pt_prop.get("type") == en_props[key].get("type")
            assert pt_prop.get("enum") == en_props[key].get("enum")
            assert pt_prop.get("minimum") == en_props[key].get("minimum")
            assert pt_prop.get("maximum") == en_props[key].get("maximum")
        assert en_schemas[name]["parameters"].get("required") == \
            pt_schema["parameters"].get("required")


def test_translated_tools_actually_describe_in_portuguese(mirror):
    for fn in mirror.TOOLS_PT:
        assert fn._needle_tool["description"].strip()
        assert fn._needle_tool["description"] != \
            {f._needle_tool["name"]: f._needle_tool["description"]
             for f in mirror.EN.TOOLS}[fn._needle_tool["name"]]


def test_system_prompt_is_translated(mirror):
    assert mirror.SYSTEM_PT.strip()
    assert mirror.SYSTEM_PT != mirror.EN.SYSTEM


# --- camada de estresse: casos pt-BR que não existem no espelho -------------

PHENOMENA = {"negacao_coloquial", "formato_numerico", "registro", "sem_acento"}


def test_stress_cases_are_tagged_by_phenomenon():
    for case in ptbr.stress.TEST_CASES:
        assert case["phenomenon"] in PHENOMENA, case
        assert case["category"] in CATEGORIES, case


def test_every_phenomenon_is_exercised():
    assert {case["phenomenon"] for case in ptbr.stress.TEST_CASES} == PHENOMENA


def test_stress_cases_never_leak_into_the_mirror_score():
    """As duas camadas medem coisas diferentes e não podem ser somadas."""
    mirror_queries = {q for m in ptbr.MIRRORS.values() for q in m.QUERIES.values()}
    for case in ptbr.stress.TEST_CASES:
        assert case["query"] not in mirror_queries


def test_stress_cases_match_declared_tools():
    schemas = {fn._needle_tool["name"]: fn._needle_tool
               for m in ptbr.MIRRORS.values() for fn in m.EN.TOOLS}
    for case in ptbr.stress.TEST_CASES:
        for call in case["calls"]:
            parameters = schemas[call["name"]]["parameters"]
            assert set(call["arguments"]) <= set(parameters["properties"])
            for key, value in call["arguments"].items():
                prop = parameters["properties"][key]
                if "enum" in prop:
                    assert value in prop["enum"]
                if "minimum" in prop:
                    assert value >= prop["minimum"]
                if "maximum" in prop:
                    assert value <= prop["maximum"]


# --- texto livre: traduzir query e gabarito juntos --------------------------

def test_free_text_translation_travels_with_the_query():
    """Campo de texto livre tem de ser traduzido na query E no gabarito.

    O contrato do Needle é copiar texto livre verbatim: se a frase diz
    'regar as plantas', a resposta certa carrega 'regar as plantas'. Manter o
    gabarito em inglês produziria a frase híbrida 'me lembra às 6pm de water
    the plants', que não é português e não mede custo de idioma -- mediria se
    o modelo copia inglês de dentro de uma frase portuguesa.
    """
    from benchmarks.ptbr import _mirror

    class FakeEnvironment:
        __name__ = "fake"
        TEST_CASES = [{
            "query": "remind me at 6pm to water the plants",
            "calls": [{"name": "set_reminder",
                       "arguments": {"message": "water the plants", "when": "6pm"}}],
            "category": "positive",
        }]

    cases = _mirror.build_cases(
        FakeEnvironment,
        {"remind me at 6pm to water the plants": "me lembra às 6pm de regar as plantas"},
        free_text={"water the plants": "regar as plantas"},
    )
    assert cases[0]["calls"][0]["arguments"]["message"] == "regar as plantas"
    assert cases[0]["calls"][0]["arguments"]["when"] == "6pm", "campo fora do mapa não muda"


def test_free_text_never_touches_the_source_module():
    """Substituir in-place corromperia o environment inglês para todo o processo."""
    from benchmarks.ptbr import _mirror

    class FakeEnvironment:
        __name__ = "fake"
        TEST_CASES = [{
            "query": "log grilled salmon",
            "calls": [{"name": "log_meal", "arguments": {"food": "grilled salmon"}}],
            "category": "positive",
        }]

    _mirror.build_cases(FakeEnvironment, {"log grilled salmon": "registra salmão grelhado"},
                        free_text={"grilled salmon": "salmão grelhado"})
    assert FakeEnvironment.TEST_CASES[0]["calls"][0]["arguments"]["food"] == "grilled salmon"


def test_free_text_map_must_not_carry_unused_entries():
    """Entrada órfã indica tradução que não casou -- provável typo silencioso."""
    from benchmarks.ptbr import _mirror

    class FakeEnvironment:
        __name__ = "fake"
        TEST_CASES = [{"query": "hello", "calls": [], "category": "irrelevant"}]

    with pytest.raises(ValueError, match="não usada"):
        _mirror.build_cases(FakeEnvironment, {"hello": "olá"},
                            free_text={"nunca aparece": "jamais"})
