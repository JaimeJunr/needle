"""Construção dos casos espelhados.

Um espelho declara apenas o mapa query_en -> query_pt. Gabarito, categoria e
criticidade são COPIADOS do módulo original — nunca redigitados. É o que torna
divergência de gabarito impossível por construção, em vez de só improvável.

A exceção é o texto livre, e ela existe por uma razão de contrato: o Needle
copia texto livre verbatim da frase para o argumento. Se a query em português
diz "regar as plantas", a resposta certa carrega "regar as plantas" — manter o
gabarito em inglês produziria a frase híbrida "me lembra às 6pm de water the
plants", que não é português e mediria outra coisa (se o modelo copia inglês de
dentro de uma frase portuguesa). Por isso `free_text` traduz os dois lados
juntos, e só nos valores declarados nominalmente.
"""

import copy


def _translate_arguments(arguments, free_text):
    return {
        key: free_text.get(value, value) if isinstance(value, str) else value
        for key, value in arguments.items()
    }


def build_cases(en_module, queries, free_text=None):
    missing = [c["query"] for c in en_module.TEST_CASES if c["query"] not in queries]
    if missing:
        raise ValueError(
            f"sem tradução para {len(missing)} caso(s) de {en_module.__name__}: {missing!r}"
        )

    free_text = free_text or {}
    used = set()
    cases = []
    for case in en_module.TEST_CASES:
        mirrored = dict(case)
        mirrored["query"] = queries[case["query"]]
        mirrored["query_en"] = case["query"]
        if free_text:
            # copy.deepcopy: substituir in-place corromperia TEST_CASES do
            # environment inglês para todo o processo, e o braço en/en passaria
            # a rodar contra um gabarito em português sem ninguém notar.
            calls = copy.deepcopy(case["calls"])
            for call in calls:
                arguments = call.get("arguments", {})
                used.update(v for v in arguments.values()
                            if isinstance(v, str) and v in free_text)
                call["arguments"] = _translate_arguments(arguments, free_text)
            mirrored["calls"] = calls
        cases.append(mirrored)

    orphans = sorted(set(free_text) - used)
    if orphans:
        raise ValueError(
            f"tradução de texto livre não usada em {en_module.__name__} "
            f"(provável typo, o valor não casa com nenhum argumento): {orphans!r}"
        )
    return cases
