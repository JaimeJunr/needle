# Needle in Brazilian Portuguese

Needle 3 is safe in Portuguese and does not do the job: on the cases where it
should act, it acts on **2 out of 18**. It does not hallucinate — it declines.

This fork teaches it to act, and ships the benchmark that measures both ends.

```
                                pt/en accuracy   critical failures   acts (positive)
  Needle 3, as shipped               34.4%              1                 2/18
  + this fork's LoRA adapter         65.6%              4                13/18
  + this fork's grounding gate       71.9%              2                14/18
```

English is not collateral damage — it improves:

```
                                en/en accuracy   critical failures
  Needle 3, as shipped               78.1%              3
  this fork, everything on           87.5%              0
```

Measured on `needle 3.0.1`, smart_home environment, 32 mirrored cases plus 22
stress cases. Reproduce with the commands at the bottom.

## What the upstream did right

Needle 2 hallucinated in Portuguese: asked to turn on the kitchen light, it
emitted `room: bedroom` — the right tool, an invented argument, every
Portuguese room collapsing onto the most frequent English one. Five critical
failures on the mirror.

Needle 3 fixed that. Critical failures in Portuguese went from 5 to 1, `missing`
(where the user names no room) went from 1/4 to a perfect 4/4, and the
confidence head became usable: 0.79 average instead of 0.08.

It bought that safety by declining. `positive` — the cases where a call *is* the
right answer — fell to 2/18. For a language the model was not trained on, that
is the correct trade: refusing beats guessing. What is missing is the language.

## What this fork adds

**A LoRA adapter** (`benchmarks/ptbr/trainset.py` generates the data) that
teaches the Portuguese vocabulary the model never saw. The diagnosis came from
the benchmark: the base model picked the right tool and missed the argument,
which reads as absent vocabulary rather than broken grammar — and vocabulary is
what LoRA fixes cheaply. It moves `positive` from 2/18 to 13/18.

**A grounding gate** (`benchmarks/ptbr/grounding.py`) that refuses any call
whose argument the sentence does not support. Fine-tuning a new language
partially undoes the upstream's `missing` fix — our adapter takes it from 4/4
back to 2/4, because teaching the model to act also teaches it to guess. The
gate restores it to 4/4, halves critical failures, and raises accuracy at the
same time. It costs zero extra inference: it is text comparison.

**A three-arm benchmark** that isolates two different questions:

| arm | tools described in | user speaks | answers |
|---|---|---|---|
| `en/en` | English | English | upstream baseline, reproduced exactly |
| `pt/en` | English | Portuguese | the realistic case |
| `pt/pt` | Portuguese | Portuguese | is it worth translating tool descriptions? |

Answer to the third: **no**. `pt/pt` scores below `pt/en` consistently. Keep
your tools described in English and let users speak Portuguese.

## Two layers, deliberately not summable

**Mirror** — the upstream's own 32 cases, translated literally, with the gold
standard *copied* from the source module rather than retyped. Answers "how much
is lost by changing only the language of the sentence?"

**Stress** — 22 cases English cannot express: colloquial and double negation
(`não liga a luz não`, `deixa quieta`), Brazilian numeric formats (`1.500` is
fifteen hundred, `22,5` is twenty-two point five), imperative and register
variation (`liga` / `ligue` / `ligar` / `dá uma acendida`), missing accents from
phone keyboards. Answers "where does Portuguese break the model in ways English
never would?"

Adding the two scores would produce a number that means nothing, so the runner
keeps them apart and the tests enforce the split.

## Honest limits

- **The adapter was trained on the Needle 2 checkpoint** and runs on the Needle 3
  engine unchanged. Retraining on the new checkpoint is untested and might do
  better.
- **Tuned weights have no confidence gate.** Fine-tuning does not update the
  confidence head, so `confidence` comes back `None` and the runner declares the
  gate inapplicable rather than inventing a number. The grounding gate is the
  replacement, and it is not equivalent: two critical failures remain.
- **Train and eval share domain and templates.** A hold-out guarantees no
  evaluation phrase was trained on — asserted raw and accent-insensitive — but
  the numbers speak for *new phrases in the same domain*, which is the real use
  case, and do not prove generalisation to a new domain.
- **One environment.** Only `smart_home` is mirrored so far.

## Reproduce

```sh
pip install "cactus-needle[train]"

# baseline, no adapter
python -m benchmarks.ptbr.runner --stress

# with the adapter and the gate
python -m benchmarks.ptbr.runner --stress --grounding --weights tuned.cact

# rebuild the training data (deterministic, no API needed)
python -m benchmarks.ptbr.trainset train.jsonl
needle finetune train.jsonl --epochs 10 --batch-size 2 --max-len 832 --out a.pkl
needle build checkpoints/needle2.pkl --lora a.pkl --out tuned.cact
```

Training took ~21h on 2 vCPU. Cap the memory (`systemd-run --user --scope -p
MemoryMax=3G`): unbounded, JAX will thrash a small machine into a hard freeze,
and `needle finetune` has no intermediate checkpoint and no `--resume`, so a
crash costs the whole run.
