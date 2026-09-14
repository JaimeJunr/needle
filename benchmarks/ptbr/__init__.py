"""Benchmark pt-BR do Needle.

Duas camadas, deliberadamente não somáveis:

  espelho  — os mesmos casos do conjunto inglês, traduzidos ao pé da letra e
             com gabarito copiado da origem. Responde: quanto se perde só por
             trocar o idioma da frase?
  estresse — casos que o inglês não consegue expressar (negação coloquial,
             vírgula decimal, imperativo variável, falta de acento).
             Responde: onde o português quebra de um jeito próprio?

Três braços de execução, definidos em `runner.py`:

  en/en  descrições em inglês, queries em inglês   (linha de base do upstream)
  pt/en  descrições em inglês, queries em português (o caso realista)
  pt/pt  descrições em português, queries em português

O delta en/en -> pt/en é o custo do idioma. O delta pt/en -> pt/pt diz se
vale a pena traduzir as descrições das tools.
"""

import importlib

_MIRROR_NAMES = ("smart_home",)

__all__ = ["MIRRORS", "stress", "trainset", *_MIRROR_NAMES]


def _load(name):
    return importlib.import_module(f"benchmarks.ptbr.{name}")


def __getattr__(name):
    if name in _MIRROR_NAMES or name in ("stress", "trainset"):
        return _load(name)
    if name == "MIRRORS":
        return {n: _load(n) for n in _MIRROR_NAMES}
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted([*globals(), "MIRRORS", "stress", "trainset", *_MIRROR_NAMES])
