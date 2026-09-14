![Needle](assets/banner.png)

# Needle 2

*[Read this in English](README.md)*

Needle 2 é um modelo aberto de 45M de parâmetros para tool calling, uso de dispositivos e extração estruturada. O modelo inteiro é um único binário de 14MB que roda uma sessão completa em cerca de 28MB de RAM. É construído sobre os achados da nossa Simple Attention Network, comprimido para CQ2-bit com Cactus Quants, e embutido em sua própria engine. Nos benchmarks abaixo, o Needle 2 troca vitórias com outros modelos pequenos como FunctionGemma 270M, LFM2.5 230M e Apple FM, sendo de 5x a 70x menor, e com 2 bits contra o f16 deles.

Este repositório é o pacote Python: inferência, fine-tuning com LoRA e exportação. `pip install cactus-needle`, descreva suas ferramentas, e chame-as a partir do Python. A engine de inferência é buscada uma vez do Hugging Face e mantida em cache; não há nada mais para compilar, e a configuração offline para dispositivos air gapped está coberta em [doc/apis.md](doc/apis.md).

- **Autocontido**: pesos embutidos numa única engine de 14MB; sem arquivos de modelo separados para gerenciar, e a inferência não faz rede.
- **Contrato simples**: chamadas de ferramenta voltam como dados estruturados, texto entra, JSON sai; uma gramática em nível de byte compilada a partir dos seus schemas restringe cada token.
- **Com gate de confiança**: cada resposta carrega um score de confiança calibrado de uma cabeça aprendida; defina um limiar, aja acima dele, escale abaixo dele.
- **Recuperação de ferramentas**: declare um catálogo grande e uma cabeça de recuperação embutida renderiza apenas as cinco melhores ferramentas por turno, com a gramática restrita a esse subconjunto.
- **Memória limitada**: uma janela deslizante de 256 tokens com as ferramentas fixadas como KV sinks, então a memória total permanece perto de 28MB não importa quanto tempo a conversa dure.

Pesos: [huggingface.co/Cactus-Compute/needle2](https://huggingface.co/Cactus-Compute/needle2) &middot; código-fonte: [github.com/cactus-compute/needle](https://github.com/cactus-compute/needle).

![Size-quality frontier: mobile-class and below](assets/frontier.png)

## Simple Attention Network

Needle 2 é uma Simple Attention Network, nossa receita densa para modelos pequenos: um Hadamard MLP no lugar do FFN, atenção GQA, memória de chave-valor engram, e hyper-connections multi-lane. Veja o paper para o design e as ablações: [arXiv:2607.18363](https://arxiv.org/abs/2607.18363).

![Simple Attention Network architecture](assets/architecture.png)

Cada bloco carrega sua regra de atualização. Aqui x̂ é o achatamento normalizado por RMS dos quatro fluxos residuais, H a transformada de Walsh-Hadamard ortonormal (uma matriz fixa, aplicada em tempo n log n sem pesos para ler), (kₜ, vₜ) linhas coletadas de tabelas de n-gramas com hash, e P a normalização duplamente estocástica dos logits de roteamento A, computada por iteração de Sinkhorn; a, b, g e todos os σ-gates são aprendidos e dependentes da entrada. Tanto os resíduos de atenção quanto os de MLP são sandwich-normed e gated, os sites engram disparam em duas camadas, e a decodificação é restrita por uma gramática em nível de byte compilada a partir dos schemas declarados.

## Início rápido

```sh
pip install cactus-needle
```

O pacote de runtime não instala a stack de treinamento. Adicione o extra `train`
ao usar fine-tuning ou exportação de checkpoint:

```sh
pip install "cactus-needle[train]"
```

O Needle lê as descrições das suas ferramentas para decidir o que chamar e como preencher os argumentos, então descrevê-las bem é o jogo inteiro.

**Simples**: decore uma função. A assinatura dá os tipos de argumento, o docstring é a descrição da ferramenta, e `run()` completa o loop: o modelo escolhe a chamada, o Needle executa sua função, alimenta o resultado de volta, e retorna a resposta final com os resultados das ferramentas executadas anexados como `results`.

```python
import needle

@needle.tool
def get_weather(city: str):
    "Get the current weather for a city."
    return {"city": city, "temp_c": 27, "sky": "clear"}

agent = needle.Needle(tools=[get_weather])
print(agent.run("what's it like in Lagos right now?")["results"])
# [{'city': 'Lagos', 'temp_c': 27, 'sky': 'clear'}]
```

**Extração**: para extrair dados estruturados de um texto, declare o formato e chame `extract()`. Passe um modelo Pydantic e você recebe de volta um objeto tipado.

```python
from pydantic import BaseModel

class Invoice(BaseModel):
    vendor: str
    total: float
    due_date: str

invoice = needle.extract("Invoice from Acme Corp, $1,200.00, due 2026-09-01", Invoice)
print(invoice.vendor, invoice.total)   # -> Acme Corp 1200.0
```

Descrições e opções por argumento, restrições de valor compiladas na gramática de decodificação, schemas JSON brutos, como conduzir o loop com `complete()`, o contrato de resposta, fatos de sistema, recuperação de ferramentas e gate de confiança estão todos cobertos em [doc/apis.md](doc/apis.md).

## Playground

Experimente qualquer modelo no navegador: escolha um preset, edite as ferramentas ou o prompt, e clique em Run. Consultas de acompanhamento continuam a mesma conversa.

```sh
needle playground                      # base model, http://127.0.0.1:7860
needle playground --weights my.cact    # a tuned model
```

O servidor baixa e inicializa o modelo antes de servir, então a primeira consulta é instantânea. O botão **Finetune on these tools** roda o pipeline de fine-tuning abaixo a partir da UI e devolve um `.cact` para download.

## Environments

Superfícies de ferramentas prontas em `needle.environments`: `smart_home`, `media_player`, `productivity`, `wearable`, `kitchen_appliance` e `data_capture`. Cada uma é um conjunto de ferramentas curado à mão cujos enums, limites e descrições mapeiam de forma limpa para a decodificação restrita do Needle, com um agente pronto e uma suíte de aceitação congelada.

```python
from needle.environments import smart_home

smart_home.agent.complete("dim the study lights to 30 percent")
smart_home.run_tests()
```

`python -m needle.environments.smart_home` roda uma suíte a partir do shell. Para adaptar um environment ao seu produto, troque os valores `Literal` (cômodos, contatos, categorias) pelos seus próprios e mantenha os formatos: conjuntos fechados como enums, números limitados, cópia literal para texto livre, cinco ferramentas ou menos. As superfícies de ferramentas completas e o contrato da suíte estão em [doc/environments.md](doc/environments.md).

## Fine-tuning

O Needle faz fine-tuning com LoRA sobre a base congelada e mescla o adaptador na exportação, então uma execução é barata e o modelo ajustado continua sendo um único `.cact` que roda na mesma engine. O fluxo é: (opcionalmente) sintetizar dados, fazer fine-tuning com LoRA, depois construir um `.cact` ajustado. Veja [doc/finetuning.md](doc/finetuning.md) para dimensionamento de dataset, leitura da curva de loss e troubleshooting.

**Formato de dados.** Um arquivo JSONL, um exemplo por linha. `reasoning` é opcional; um exemplo fora do tópico tem `answers: []`.

```json
{"query": "dim the kitchen to 10", "tools": [{"name": "set_lights", "parameters": {"type": "object", "properties": {"room": {"type": "string"}, "brightness": {"type": "integer"}}, "required": ["room"]}}], "answers": [{"name": "set_lights", "arguments": {"room": "kitchen", "brightness": 10}}], "reasoning": "'kitchen' -> room; 'dim to 10' -> brightness 10"}
```

**1. Sintetizar dados (opcional).** Precisa de `OPENROUTER_API_KEY`. Comece a partir de um arquivo de schema de ferramenta, ou expanda um conjunto existente:

```sh
export OPENROUTER_API_KEY=sk-or-...
needle generate-data --tools my_tools.json --num-samples 500 --output data.jsonl
needle generate-data --augment data.jsonl --num-samples 500      # expand an existing JSONL
```

Defina `OPENROUTER_URL` para usar um gateway compatível com OpenAI no lugar do endpoint padrão do OpenRouter.

**2. Fine-tuning com LoRA.** O checkpoint base baixa automaticamente do Hugging Face se você não passar `--checkpoint`. `--generate N` primeiro sintetiza mais N exemplos a partir das ferramentas nos seus dados (também precisa de `OPENROUTER_API_KEY`).

```sh
needle finetune data.jsonl --epochs 10
needle finetune data.jsonl --epochs 10 --generate 300 --lora-rank 16 --lora-alpha 32
```

Opções principais: `--epochs` (padrão 3), `--lora-rank` (16), `--lora-alpha` (32), `--lr` (1e-4), `--batch-size` (16), `--max-len` (1024), `--val-split` (0.1), `--checkpoint <base.pkl>`, `--checkpoint-dir <dir>` (padrão `checkpoints`), `--out <adapter.pkl>`, `--generate <n>`, `--model <id>` (padrão `deepseek/deepseek-v4-flash`), e `--workers <n>` (padrão 8). `--generate` usa o endpoint configurado do OpenRouter para sintetizar exemplos extras antes do treinamento. O adaptador é escrito em `checkpoints/needle_lora.pkl` por padrão. Uma loss de validação é impressa a cada época a partir do split reservado.

O treinamento é JAX puro e roda em qualquer acelerador suportado pelo jax. Numa máquina NVIDIA, instale o build CUDA e o mesmo comando treina na GPU:

```sh
pip install "cactus-needle[train,gpu]"
```

No Apple Silicon o extra `metal` treina na GPU:

```sh
pip install "cactus-needle[train,metal]"
```

**3. Construir um `.cact` ajustado.** Mescla o adaptador na base e quantiza. A base baixa automaticamente se estiver ausente.

```sh
needle build checkpoints/needle2.pkl --lora checkpoints/needle_lora.pkl --out my_needle.cact
```

Adicione `--bits 2` para um modelo menor (por padrão a exportação segue o mapa de bits por camada declarado no checkpoint, caindo para 4 quando o checkpoint não declara nenhum), ou defina `NEEDLE_HF_REPO=<you>/<model>` e passe `--upload` para publicar o `.cact`. O comando correspondente `needle download <you>/<model>/my_needle.cact` baixa um arquivo publicado em qualquer máquina, e `needle download <platform>` (ex.: `macos-arm64`) busca o executor de engine daquela plataforma.

**4. Execute.** A engine é agnóstica a pesos, então um `.cact` ajustado roda nela diretamente - sem recompilação:

```python
import needle
agent = needle.Needle(weights="my_needle.cact", tools=[...])
agent.run("...")
```

## Telemetria

A Cactus Compute coleta telemetria de uso estritamente anônima (nome da função, versão do pacote, sistema operacional — nunca seus prompts, saídas ou dados); desative com `NEEDLE_TELEMETRY=0` ou `DO_NOT_TRACK=1`.

## Citação

Needle 2 é construído pelo time da Cactus Compute. Se você o usar em seu trabalho, por favor cite:

```bibtex
@misc{needle2_2026,
  title        = {Needle 2: A 45M-Parameter Foundation Tool-Calling Model for Tiny Devices},
  author       = {Ndubuaku, Henry and Mosoyan, Karen and Mroz, Jakub and Cylich, Noah and
                  Kumar, Satyajit and Sandhu, Parkirat and Shemet, Roman and Lee, Justin H.},
  year         = {2026},
  organization = {Cactus Compute, Inc.},
  howpublished = {\url{https://github.com/cactus-compute/needle}}
}
```

Entre em contato pelo founders@cactuscompute.com para parcerias, colaborações, sinergias e para implantar o Needle2 no seu produto.
