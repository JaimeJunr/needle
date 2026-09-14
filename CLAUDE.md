# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is the Python package `cactus-needle` (`pip install cactus-needle`): inference, LoRA fine-tuning, and export for Needle 2, a 45M-parameter on-device tool-calling model. The model architecture itself (a "Simple Attention Network": Hadamard MLP, GQA attention, engram KV memory, multi-lane hyper-connections) lives in `needle/model/`; the compiled inference engine (the 14MB C++ binary) is a separate artifact fetched from Hugging Face at runtime, not built from this repo.

**`llms.txt` at the repo root is the authoritative, dense API reference** (install, `Needle`/`tool`/`extract`, tool schema rules, confidence gating, tool retrieval, environments, weights/`.cact` semantics, CLI). Read it before writing any code against the public API — it documents the exact contract and explicitly warns against inventing API not listed there.

## Commands

Setup (creates `.venv`, installs `-e .[train]`, adds `[gpu]` if an NVIDIA GPU is detected):
```sh
./setup          # or setup.bat on Windows
```

Run tests (mirrors CI in `.github/workflows/release.yaml`):
```sh
pytest -q -m "not slow"      # fast suite — what CI runs before every release
pytest -q                    # includes slow tests (JAX build/finetune, inits a tiny model)
pytest tests/test_tools.py::test_name -q   # single test
```
Tests requiring the native engine binary are skipped automatically via the `requires_engine` marker in `tests/conftest.py` when the engine hasn't been fetched yet (first real `Needle(...)` use downloads it from Hugging Face). `tiny_checkpoint` (also in `conftest.py`) builds a minimal 2-layer checkpoint for architecture/build/finetune tests without downloading anything.

The `train` extra (JAX/flax/optax/sentencepiece) is required for anything touching `needle/model/` beyond `run.py`; a runtime-only install cannot run `finetune`/`build`/`generate-data`.

CLI (installed as `needle`, entry point `needle.cli:main`):
```sh
needle run ...                # inference, needle/model/run.py
needle finetune data.jsonl ...   # LoRA finetune, needle/model/finetune.py
needle generate-data ...         # synthesize training data (needs OPENROUTER_API_KEY)
needle build ckpt.pkl --lora ... --out my.cact   # merge + quantize -> .cact export
needle download <org>/<repo> | <platform>        # pull a published .cact or engine runner
needle playground                                # local HTTP UI, needle/playground/server.py
```

## Architecture

- **`needle/__init__.py`** — the public API surface: `Needle` (agent class: `complete`, `run`, `embed`, `reset`), `extract`, `tool`, `Field`. `Needle` loads the native engine via `ctypes`, resolves declared tools/Pydantic models/raw schemas into JSON schema, and compiles the grammar that constrains decoding. `extract()` builds a one-shot `Needle` internally and, with `strict=True`, validates temporal grounding, fabricated values, and negation against the source text.
- **`needle/agent/`** — `tools.py` converts functions/Pydantic models into tool JSON schemas (attached to the function as `_needle_tool`); `fetch.py` resolves platform/generation/version and downloads the engine wheel from the configured Hugging Face repo, extracting `libneedle.*` into the cache.
- **`needle/model/`** — the JAX/Flax side, only needed for training/export, not for inference:
  - `architecture.py` — `TransformerConfig` and the Flax `SimpleAttentionNetwork` (the actual model definition).
  - `run.py` — loads a `.pkl` checkpoint, builds the model, runs generation (backs `needle run`).
  - `finetune.py` — LoRA fine-tuning loop, dataset generation via OpenRouter, and the `build` command that merges a LoRA adapter into the base and hands off to `export.py`.
  - `export.py` — writes the final `.cact` export.
  - `quantize.py` — fake quantization / QAT during training and the deployment-time quantization used at export (default CQ2-bit per the checkpoint's per-layer bit map, `--bits 2/4` overrides).
  - `decode.py` — KV-cached and batched decoding.
  - `tokenizer.py` — SentencePiece wrapper, fetches the tokenizer from Hugging Face if absent.
  - **Weights lifecycle**: training produces `.pkl` checkpoints; `needle build` merges LoRA + quantizes into a single `.cact`, which is what `Needle(weights=...)` and the engine actually load. The engine cannot unload weights once a tuned `.cact` is bound — construct base-model agents before tuned ones, or use separate processes.
- **`needle/environments/`** — six ready-made tool surfaces (`smart_home`, `media_player`, `productivity`, `wearable`, `kitchen_appliance`, `data_capture`), each exposing `TOOLS`, `SYSTEM`, a lazily-constructed `agent`, `TEST_CASES`, and `run_tests()`. `_harness.py` is the shared plumbing: it memoizes the `Needle(tools=..., system=...)` agent per module, enables strict extraction validation, and diffs produced calls against the frozen `TEST_CASES` suite. When adapting an environment, keep the shape (closed sets as `Literal` enums, bounded numbers, verbatim copy for free text, five tools or fewer) — that shape is what the model's constrained decoding was trained against.
- **`needle/playground/`** — `server.py` is a `ThreadingHTTPServer` serving `index.html`/`app.js`/`style.css` and exposing `/complete`, `/reset`, `/load-model`, `/finetune`, `/finetune/status`, `/model`, `/download/...`; it keeps a single `Engine` that lazily constructs/reuses a `Needle` instance and runs the fine-tune pipeline from the "Finetune on these tools" button.
- **`benchmarks/ptbr/`** — a three-arm pt-BR evaluation layered on top of the `needle.environments` surfaces, independent of the training/inference code above:
  - `_mirror.py` translates an English environment's `TEST_CASES` into Portuguese queries while keeping the expected calls, category, and criticality identical (`build_cases`).
  - `smart_home.py` mirrors `needle.environments.smart_home`: `TEST_CASES` (translated queries, English tools/system) plus a `TOOLS_PT`/`SYSTEM_PT` variant (translated tool descriptions and system prompt, same machine-readable schema).
  - `stress.py` holds pt-BR-only cases (colloquial negation, Brazilian numeric formats, registers/imperatives, missing accents/typos) not mirrored from English, tagged with `phenomenon`/`rationale`.
  - `trainset.py` deterministically generates a LoRA fine-tune JSONL set (pt query / en tools+system arm), dedupes against itself and against every query reserved for evaluation (contamination guard), and writes it via `write_jsonl()`.
  - `runner.py` runs each mirror across three arms — `en/en`, `pt/en` (English tools/system, Portuguese query), `pt/pt` — applies confidence-based refusal gating (`apply_gate`), and summarises accuracy/critical-failure/confidence per category and phenomenon; `--stress` additionally runs `stress.TEST_CASES` on the `pt/en`/`pt/pt` arms, scored separately since those cases aren't mirror-equivalent.
  - The corresponding tests (`tests/test_ptbr_benchmark.py`, `test_ptbr_runner.py`, `test_ptbr_trainset.py`) assert the mirror/stress split stays clean, tool schemas stay in sync between English and Portuguese, and the generated trainset is contamination-free and well-formed — these are the tests to run/extend when touching anything under `benchmarks/ptbr/`.

## Release process

Releases are fully automated (`.github/workflows/release.yaml`): a daily cron job runs the fast test suite and, if `main` has moved since the last tag, bumps the patch version in `pyproject.toml` and `needle/__init__.py`, builds, publishes to PyPI, and pushes the tag itself. Do not hand-bump `version`/`__version__` or create release tags manually.

## Docs

`doc/apis.md`, `doc/environments.md`, and `doc/finetuning.md` expand on `llms.txt` with worked examples (system facts, tool retrieval, offline/air-gapped setup, adapting an environment, dataset sizing and loss-curve reading). README has both an English (`README.md`) and Portuguese (`README.pt-BR.md`) version, kept in sync.
