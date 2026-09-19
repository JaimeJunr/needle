#!/usr/bin/env bash
# Roda o par de controle do experimento pt-BR numa máquina só, em sequência.
#
# A pergunta: 28,2% de negativos foi melhor que os 15,6% originais? Os dois
# braços rodam AQUI, com batch, epochs, rank e seed idênticos, mudando apenas
# o dataset -- é o que torna o delta atribuível à proporção de negativos.
# Distribuir os braços entre máquinas diferentes acrescentaria o batch size
# como segunda variável (o box não aguenta batch 4), e o número não pertenceria
# a nenhuma das duas.
#
# Cada braço grava adapter, .cact e avaliação assim que termina, então uma
# queda na segunda corrida não custa a primeira -- o finetune não tem
# checkpoint intermediário nem --resume, e esta é a única proteção disponível.
#
# uso: run_pair.sh <dir-de-runs> <repo> [batch] [epochs] [memmax]
set -u

RUNS="${1:-$HOME/needle-runs}"
REPO="${2:-$HOME/projects/needle}"
BATCH="${3:-2}"
EPOCHS="${4:-10}"
MEMMAX="${5:-3G}"
PY="$REPO/.venv/bin"

cd "$REPO" || exit 1
export NEEDLE_TELEMETRY=0

run_arm() {
  local name="$1" jsonl="$2"
  local log="$RUNS/${name}.log"

  if [ -f "$RUNS/${name}.cact" ]; then
    echo "[$(date -Is)] $name: .cact já existe, pulando" | tee -a "$RUNS/pair.log"
    return 0
  fi

  echo "[$(date -Is)] $name: treino iniciado (batch $BATCH, $EPOCHS epochs)" | tee -a "$RUNS/pair.log"
  systemd-run --user --scope -p MemoryMax="$MEMMAX" \
    /usr/bin/time -v "$PY/needle" finetune "$jsonl" \
      --epochs "$EPOCHS" --batch-size "$BATCH" --max-len 832 \
      --out "$RUNS/${name}.pkl" > "$log" 2>&1
  local rc=$?
  if [ $rc -ne 0 ] || [ ! -f "$RUNS/${name}.pkl" ]; then
    echo "[$(date -Is)] $name: TREINO FALHOU (rc=$rc) -- ver $log" | tee -a "$RUNS/pair.log"
    return 1
  fi

  echo "[$(date -Is)] $name: build do .cact" | tee -a "$RUNS/pair.log"
  systemd-run --user --scope -p MemoryMax="$MEMMAX" \
    "$PY/needle" build checkpoints/needle2.pkl \
      --lora "$RUNS/${name}.pkl" --out "$RUNS/${name}.cact" >> "$log" 2>&1 || {
    echo "[$(date -Is)] $name: BUILD FALHOU -- ver $log" | tee -a "$RUNS/pair.log"
    return 1
  }

  echo "[$(date -Is)] $name: avaliando" | tee -a "$RUNS/pair.log"
  "$PY/python" -m benchmarks.ptbr.runner --stress \
    --weights "$RUNS/${name}.cact" --json "$RUNS/${name}-eval.json" \
    > "$RUNS/${name}-eval.txt" 2>&1 || {
    echo "[$(date -Is)] $name: AVALIACAO FALHOU" | tee -a "$RUNS/pair.log"
    return 1
  }

  echo "[$(date -Is)] $name: CONCLUIDO" | tee -a "$RUNS/pair.log"
}

echo "[$(date -Is)] par iniciado em $(hostname)" | tee -a "$RUNS/pair.log"
run_arm "v1_neg156" "$RUNS/v1_neg156.jsonl"
run_arm "v2_neg282" "$RUNS/v2_neg282.jsonl"
echo "[$(date -Is)] PAR FINALIZADO" | tee -a "$RUNS/pair.log"
