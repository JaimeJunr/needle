"""Construção dos casos espelhados.

Um espelho declara apenas o mapa query_en -> query_pt. Gabarito, categoria e
criticidade são COPIADOS do módulo original — nunca redigitados. É o que torna
divergência de gabarito impossível por construção, em vez de só improvável.
"""


def build_cases(en_module, queries):
    missing = [c["query"] for c in en_module.TEST_CASES if c["query"] not in queries]
    if missing:
        raise ValueError(
            f"sem tradução para {len(missing)} caso(s) de {en_module.__name__}: {missing!r}"
        )
    cases = []
    for case in en_module.TEST_CASES:
        mirrored = dict(case)
        mirrored["query"] = queries[case["query"]]
        mirrored["query_en"] = case["query"]
        cases.append(mirrored)
    return cases
