"""Executor dos três braços do benchmark pt-BR.

    python -m benchmarks.ptbr.runner                    # espelho, 3 braços
    python -m benchmarks.ptbr.runner --stress           # espelho + estresse
    python -m benchmarks.ptbr.runner --min-confidence 0.4
    python -m benchmarks.ptbr.runner --json out.json

O critério de acerto é o mesmo do harness oficial (`needle.environments._harness`),
copiado de propósito e não importado: se o upstream afrouxar a comparação, o
benchmark não pode afrouxar junto sem que alguém perceba.
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict

import needle


def _calls_match(got, want):
    if got == want:
        return True
    return sorted(json.dumps(c, sort_keys=True) for c in got) == \
        sorted(json.dumps(c, sort_keys=True) for c in want)


def apply_gate(got, confidence, min_confidence):
    """Aplica o contrato de producao: abaixo do limiar, a chamada vira recusa.

    `confidence` None significa cabeca de confianca nao calibrada -- o caso de
    todo modelo tunado, porque o fine-tune nao a atualiza. Ai o gate e
    INAPLICAVEL: nao se gateia nada, e quem le o resultado precisa saber que
    aquele numero nao passou pela mesma rede de protecao dos demais.
    """
    if not got or not min_confidence or confidence is None:
        return got, False
    if confidence < min_confidence:
        return [], True
    return got, False


def _agent(tools, system, weights=None):
    os.environ.setdefault("NEEDLE_STRICT_VALIDATE", "1")
    if weights:
        return needle.Needle(tools=tools, system=system, weights=weights)
    return needle.Needle(tools=tools, system=system)


def run_arm(name, tools, system, cases, min_confidence=0.0, verbose=False, weights=None):
    """Roda um conjunto de casos contra uma configuração de tools e devolve o resultado bruto."""
    agent = _agent(tools, system, weights)
    records = []
    started = time.time()
    for case in cases:
        agent.reset()
        response = agent.complete(case["query"])
        got = response.get("function_calls") or []
        confidence = response.get("confidence")
        got, gated = apply_gate(got, confidence, min_confidence)
        records.append({
            "query": case["query"],
            "query_en": case.get("query_en"),
            "category": case["category"],
            "phenomenon": case.get("phenomenon"),
            "critical": bool(case.get("critical")),
            "want": case["calls"],
            "got": got,
            "confidence": None if confidence is None else round(float(confidence), 4),
            "gated": gated,
            "ok": _calls_match(got, case["calls"]),
        })
        if verbose and not records[-1]["ok"]:
            print(f"  FAIL [{case['category']}] {case['query']}")
            print(f"    want {json.dumps(case['calls'], ensure_ascii=False)}")
            print(f"    got  {json.dumps(got, ensure_ascii=False)}")
    return {
        "arm": name,
        "seconds": round(time.time() - started, 1),
        "min_confidence": min_confidence,
        "records": records,
    }


def summarise(result):
    records = result["records"]
    passed = sum(r["ok"] for r in records)
    critical_failures = [r for r in records if r["critical"] and not r["ok"]]
    by_category = defaultdict(lambda: [0, 0])
    by_phenomenon = defaultdict(lambda: [0, 0])
    for r in records:
        by_category[r["category"]][1] += 1
        by_category[r["category"]][0] += r["ok"]
        if r["phenomenon"]:
            by_phenomenon[r["phenomenon"]][1] += 1
            by_phenomenon[r["phenomenon"]][0] += r["ok"]
    confidences = [r["confidence"] for r in records if r["confidence"] is not None]
    return {
        "arm": result["arm"],
        "passed": passed,
        "total": len(records),
        "pct": round(100.0 * passed / len(records), 1) if records else 0.0,
        "critical_failures": len(critical_failures),
        "mean_confidence": round(sum(confidences) / len(confidences), 4) if confidences else None,
        "gate_applicable": bool(confidences),
        "seconds": result["seconds"],
        "by_category": {k: v for k, v in sorted(by_category.items())},
        "by_phenomenon": {k: v for k, v in sorted(by_phenomenon.items())},
    }


def _print_summary(title, summaries):
    print(f"\n{title}")
    print(f"  {'braço':<8} {'acerto':>12} {'%':>7} {'críticos':>9} {'confiança':>10} {'tempo':>7}")
    for s in summaries:
        confidence = "n/d" if s["mean_confidence"] is None else f"{s['mean_confidence']:.4f}"
        print(f"  {s['arm']:<8} {s['passed']:>5}/{s['total']:<6} {s['pct']:>6.1f}% "
              f"{s['critical_failures']:>9} {confidence:>10} {s['seconds']:>6.1f}s")
    if any(not s["gate_applicable"] for s in summaries):
        print("  ! confianca n/d: o fine-tune nao atualiza a cabeca de confianca, "
              "entao o gate NAO se aplica a pesos tunados")

    categories = sorted({c for s in summaries for c in s["by_category"]})
    if categories:
        print(f"\n  por categoria")
        header = "  " + f"{'categoria':<12}" + "".join(f"{s['arm']:>10}" for s in summaries)
        print(header)
        for cat in categories:
            row = f"  {cat:<12}"
            for s in summaries:
                ok, total = s["by_category"].get(cat, (0, 0))
                row += f"{f'{ok}/{total}':>10}"
            print(row)

    phenomena = sorted({p for s in summaries for p in s["by_phenomenon"]})
    if phenomena:
        print(f"\n  por fenômeno")
        print("  " + f"{'fenômeno':<20}" + "".join(f"{s['arm']:>10}" for s in summaries))
        for ph in phenomena:
            row = f"  {ph:<20}"
            for s in summaries:
                ok, total = s["by_phenomenon"].get(ph, (0, 0))
                row += f"{f'{ok}/{total}':>10}"
            print(row)


def _deltas(summaries):
    by_arm = {s["arm"]: s for s in summaries}
    print("\n  leitura")
    if "en/en" in by_arm and "pt/en" in by_arm:
        d = by_arm["pt/en"]["pct"] - by_arm["en/en"]["pct"]
        print(f"    custo do idioma (en/en -> pt/en): {d:+.1f} pontos")
    if "pt/en" in by_arm and "pt/pt" in by_arm:
        d = by_arm["pt/pt"]["pct"] - by_arm["pt/en"]["pct"]
        print(f"    ganho de traduzir as descrições (pt/en -> pt/pt): {d:+.1f} pontos")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Benchmark pt-BR do Needle")
    parser.add_argument("--min-confidence", type=float, default=0.0,
                        help="Aplica o contrato de produção: abaixo do limiar, trata como recusa.")
    parser.add_argument("--stress", action="store_true",
                        help="Roda também a camada de estresse (pontuada separadamente).")
    parser.add_argument("--json", type=str, default=None, help="Salva o resultado bruto.")
    parser.add_argument("--verbose", action="store_true", help="Imprime cada falha.")
    parser.add_argument("--weights", type=str, default=None,
                        help="Um .cact tunado a avaliar no lugar do modelo base.")
    args = parser.parse_args(argv)

    from benchmarks import ptbr

    payload = {"mirror": [], "stress": []}
    for env_name, mirror in sorted(ptbr.MIRRORS.items()):
        EN = mirror.EN
        arms = [
            ("en/en", EN.TOOLS, EN.SYSTEM, EN.TEST_CASES),
            ("pt/en", EN.TOOLS, EN.SYSTEM, mirror.TEST_CASES),
            ("pt/pt", mirror.TOOLS_PT, mirror.SYSTEM_PT, mirror.TEST_CASES),
        ]
        results = []
        for arm_name, tools, system, cases in arms:
            if args.verbose:
                print(f"\n[{env_name}] braço {arm_name}")
            results.append(run_arm(arm_name, tools, system, cases,
                                   args.min_confidence, args.verbose, args.weights))
        summaries = [summarise(r) for r in results]
        payload["mirror"].append({"environment": env_name, "results": results})
        _print_summary(f"espelho · {env_name} (gate de confiança {args.min_confidence})", summaries)
        _deltas(summaries)

    if args.stress:
        smart_home = ptbr.MIRRORS["smart_home"]
        EN = smart_home.EN
        stress_arms = [
            ("pt/en", EN.TOOLS, EN.SYSTEM),
            ("pt/pt", smart_home.TOOLS_PT, smart_home.SYSTEM_PT),
        ]
        results = [run_arm(n, t, s, ptbr.stress.TEST_CASES, args.min_confidence,
                           args.verbose, args.weights)
                   for n, t, s in stress_arms]
        payload["stress"] = results
        _print_summary(f"estresse pt-BR (gate de confiança {args.min_confidence})",
                       [summarise(r) for r in results])
        print("\n  (o score de estresse NÃO é comparável ao do espelho: casos diferentes)")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"\nresultado bruto em {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
