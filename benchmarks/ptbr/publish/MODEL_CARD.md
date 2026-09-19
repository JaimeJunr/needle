---
library_name: cactus-needle
pipeline_tag: text-generation
license: apache-2.0
base_model: Cactus-Compute/needle2
language:
  - pt
  - en
tags:
  - tool-calling
  - function-calling
  - on-device
  - edge
  - quantization
  - portuguese
  - brazilian-portuguese
---

# Needle pt-BR

Needle in Brazilian Portuguese. A LoRA fine-tune of
[Cactus-Compute/needle](https://huggingface.co/Cactus-Compute/needle3) that
teaches the model the Portuguese vocabulary it was never trained on.

**The problem.** Needle 3 is safe in Portuguese and does not do the job. On the
cases where a tool call is the right answer, it acts on **2 out of 18**. It does
not hallucinate — it declines, which is the correct trade for a language the
model was not trained on. What is missing is the language.

**What this does.**

```
pt/en (tools described in English, user speaks Portuguese)

                                accuracy   critical failures   acts
  Needle 3, as shipped            34.4%            1           2/18
  + this adapter                  65.6%            4          13/18
  + adapter and grounding gate    71.9%            2          14/18
```

English does not regress — it improves:

```
en/en                           accuracy   critical failures
  Needle 3, as shipped            78.1%            3
  + adapter and gate              87.5%            0
```

Measured on `needle 3.0.1`, `smart_home` environment, 32 mirrored cases plus 22
Portuguese-specific stress cases. The benchmark, the training data generator and
the gate are all open:
[github.com/JaimeJunr/needle](https://github.com/JaimeJunr/needle/tree/main/benchmarks/ptbr).

## Use

```sh
pip install cactus-needle
needle download JaimeJunr/needle-ptbr
```

```python
import needle

@needle.tool
def control_lights(room: str, action: str):
    "Turn lights on or off in a room."
    return {"ok": True, "room": room, "action": action}

agent = needle.Needle(tools=[control_lights], weights="needle-ptbr.cact")
agent.complete("liga a luz da cozinha")
```

**Describe your tools in English.** Translating tool descriptions to Portuguese
scores consistently *worse* (`pt/pt` 68.8% against `pt/en` 71.9%). Let the user
speak Portuguese and keep the schema in English.

## The grounding gate is not optional

Fine-tuning a new language costs something the upstream had already fixed: the
model stops inventing rooms (`missing` 4/4) until you teach it to act, and then
it starts guessing again (`missing` 2/4). The gate restores 4/4, halves critical
failures and raises accuracy at the same time, at zero extra inference — it is
text comparison.

It ships in the repository, not in these weights:
[`benchmarks/ptbr/grounding.py`](https://github.com/JaimeJunr/needle/blob/main/benchmarks/ptbr/grounding.py).
Without it, expect the 65.6% / 4-critical row.

## Limits, stated plainly

- **Trained on the Needle 2 checkpoint**, runs on the Needle 3 engine. It works,
  but the quantisation scheme changed between them (`CQ mixed` 2-bit to `CQ W4`),
  so this adapter was built for a target the current engine no longer uses.
  Retraining on the Needle 3 checkpoint was attempted and **did not work** --
  see below.
- **Slow on CPU with the Needle 3 engine**: 36-57 seconds per call on a 4-thread
  laptop, against roughly half a second on the Needle 2 engine. The adapter is
  not the cause -- the base model is equally slow -- but plan evaluation runs
  accordingly.
- **No confidence gate.** Fine-tuning does not update the confidence head, so
  tuned weights report `confidence` as `None`. The base model's calibrated
  confidence (0.79 average in Portuguese on Needle 3) is lost. The grounding gate
  is a replacement, not an equivalent: two critical failures remain.
- **One domain.** Trained and measured on smart-home tool surfaces. The numbers
  speak for new phrases in that domain — a hold-out guarantees no evaluation
  phrase was trained on — and do not prove generalisation to a new domain.
- **Brazilian Portuguese**, not European. The stress cases target pt-BR
  colloquial negation, numeric format and register.

## The Needle 3 retrain did not work

Worth stating so nobody repeats it. A LoRA was trained on the Needle 3
checkpoint itself -- 10/10 epochs, validation loss 0.0390, `needle build`
reporting `merged 5 weight groups` and writing a 63.47 MB `.cact`. Every signal
said success.

The resulting model behaves **identically to the untuned base**: it answers
English correctly and returns an empty call list for Portuguese, exactly like
the stock model. The adapter had no effect.

The size is the clue: the engine's own base is 35.34 MB and the merged artifact
came out at 63.47 MB. A working merge should land near the base. The likely
cause is that rank-16 LoRA over "5 weight groups" does not map onto the Needle 3
architecture the way it did on Needle 2, so the trained weights are not where
the engine reads them.

Unresolved. The adapter published here is the Needle 2 one, which is measured
and works.

## How it was built

Deterministic generator, no API: the vocabulary is closed (four rooms, five
tools), so templates cover the space better than sampling a large model, and the
dataset is reproducible bit for bit.

902 examples, **28.2% negatives**. That proportion was measured, not guessed: at
15.6% a single epoch drove `negation` from 1/3 to 0/3 and raised critical
failures from 5 to 7 — the model learned to act and unlearned restraint. Half
the negation templates carry no leading particle (`deixa quieta`, `nem pensa`,
`melhor nao mexer`), because that is how Portuguese actually negates.

LoRA rank 16, 10 epochs, batch 2. ~21h on 2 vCPU.

## Attribution

Derivative of [Cactus-Compute/needle](https://huggingface.co/Cactus-Compute/needle3),
Apache 2.0. The base model, the engine and the Simple Attention Network
architecture are their work ([arXiv:2607.18363](https://arxiv.org/abs/2607.18363)).
This repository adds a Portuguese LoRA adapter and nothing else; the upstream
made the safety trade that this builds on.

Licensed under Apache 2.0.
