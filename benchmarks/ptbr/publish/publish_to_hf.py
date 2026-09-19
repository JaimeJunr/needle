"""Publica o adapter pt-BR num repositório de modelo no Hugging Face.

Roda onde o `.cact` está e onde `huggingface_hub` já existe — no box ele vem
junto com `cactus-needle`, então não há nada a instalar.

    # autenticar uma vez (o token fica em ~/.cache/huggingface/token)
    python -c "from huggingface_hub import login; login()"

    # publicar
    python benchmarks/ptbr/publish/publish_to_hf.py \
        --repo <usuario>/needle-ptbr \
        --cact ~/needle-runs/ptbr_n3.cact

    # ver o que subiria, sem subir
    python benchmarks/ptbr/publish/publish_to_hf.py --repo ... --cact ... --dry-run

O token NUNCA é passado por argumento: viraria linha no histórico do shell e
na lista de processos. Use `login()` ou a variável `HF_TOKEN`.

A Apache 2.0 dos pesos originais exige três coisas, e o script recusa publicar
sem elas: a licença junto, atribuição ao upstream e a marcação de que isto é
obra derivada. Estão no MODEL_CARD.md e são conferidas antes do upload.
"""

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent.parent

# Sem isto o card sobe sem cumprir a Apache 2.0, e ninguém percebe até alguém
# reclamar. Barato conferir, caro descobrir depois.
REQUIRED_IN_CARD = {
    "license: apache-2.0": "campo de licença no frontmatter",
    "Cactus-Compute/needle": "atribuição ao modelo original",
    "Derivative of": "marcação explícita de obra derivada",
    "Limits": "seção de limites",
}


def _check_card(card_text):
    missing = [why for token, why in REQUIRED_IN_CARD.items() if token not in card_text]
    if missing:
        raise SystemExit(
            "MODEL_CARD.md incompleto, faltando:\n  - " + "\n  - ".join(missing)
        )


def _check_authenticated():
    from huggingface_hub import HfApi

    try:
        return HfApi().whoami()["name"]
    except Exception:
        raise SystemExit(
            "não autenticado no Hugging Face.\n"
            '  rode:  python -c "from huggingface_hub import login; login()"\n'
            "  ou:    export HF_TOKEN=<seu token de escrita>"
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo", required=True, help="destino, ex.: usuario/needle-ptbr")
    parser.add_argument("--cact", required=True, type=Path, help="o .cact a publicar")
    parser.add_argument("--private", action="store_true", help="cria o repo privado")
    parser.add_argument("--dry-run", action="store_true", help="lista e sai, sem subir")
    args = parser.parse_args(argv)

    card = HERE / "MODEL_CARD.md"
    licence = REPO_ROOT / "LICENSE"

    for path in (card, licence, args.cact):
        if not path.exists():
            raise SystemExit(f"não encontrado: {path}")

    _check_card(card.read_text(encoding="utf-8"))

    # O nome do arquivo publicado casa com o repo, porque é assim que
    # `needle download <org>/<repo>` resolve o artefato do outro lado.
    target_name = f"{args.repo.split('/')[-1]}.cact"
    uploads = [
        (card, "README.md"),
        (licence, "LICENSE"),
        (args.cact, target_name),
    ]

    size_mb = args.cact.stat().st_size / 1e6
    print(f"destino : {args.repo}{' (privado)' if args.private else ''}")
    print(f"pesos   : {args.cact} -> {target_name}  ({size_mb:.1f} MB)")
    for src, dest in uploads[:2]:
        print(f"anexo   : {src.name} -> {dest}")

    if args.dry_run:
        print("\n--dry-run: nada foi enviado.")
        return 0

    user = _check_authenticated()
    print(f"autenticado como: {user}")

    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(args.repo, repo_type="model", private=args.private, exist_ok=True)
    for src, dest in uploads:
        print(f"enviando {dest} ...", flush=True)
        api.upload_file(
            path_or_fileobj=str(src),
            path_in_repo=dest,
            repo_id=args.repo,
            repo_type="model",
        )

    print(f"\npublicado: https://huggingface.co/{args.repo}")
    print(f"testar:    needle download {args.repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
