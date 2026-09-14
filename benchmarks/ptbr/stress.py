"""Camada de estresse: fenômenos do pt-BR sem equivalente no conjunto inglês.

Estes casos NÃO entram no score do espelho. O espelho responde "quanto se
perde ao trocar o idioma da mesma frase"; esta camada responde "onde o
português quebra o modelo de um jeito que o inglês nunca testaria". Somar os
dois produziria um número que não significa nada.

Todos usam a superfície de tools do smart_home, para que o eixo sob teste
seja a língua e não o domínio.
"""

# Cada caso carrega, além do contrato normal de TEST_CASES:
#   phenomenon: o fenômeno linguístico sob teste
#   rationale:  por que este caso é capaz de quebrar, em uma linha

TEST_CASES = [

    # --- negação coloquial e dupla ----------------------------------------
    # A negação em pt-BR raramente é o "don't" inicial do inglês. Ela vem no
    # fim da frase, duplicada, ou embutida num verbo que não parece negativo.
    # Errar aqui é o erro mais caro do conjunto: aciona o que se pediu para
    # NÃO fazer. Por isso todos são críticos, como no espelho.
    {"query": "não liga a luz da cozinha não", "calls": [], "category": "negation",
     "critical": True, "phenomenon": "negacao_coloquial",
     "rationale": "dupla negação com 'não' final, construção sem paralelo em inglês"},
    {"query": "deixa a luz do quarto quieta", "calls": [], "category": "negation",
     "critical": True, "phenomenon": "negacao_coloquial",
     "rationale": "negação sem partícula negativa: 'deixar quieto' = não mexer"},
    {"query": "nem vem acender a luz da sala", "calls": [], "category": "negation",
     "critical": True, "phenomenon": "negacao_coloquial",
     "rationale": "'nem vem' nega um imperativo que aparece na forma afirmativa"},
    {"query": "tira a mão do termostato", "calls": [], "category": "negation",
     "critical": True, "phenomenon": "negacao_coloquial",
     "rationale": "proibição idiomática; a frase contém o alvo mas pede inação"},
    {"query": "esquece o aspirador por hoje", "calls": [], "category": "negation",
     "critical": True, "phenomenon": "negacao_coloquial",
     "rationale": "negação por descarte, verbo afirmativo e alvo nomeado"},

    # --- formato numérico brasileiro --------------------------------------
    # Vírgula decimal e ponto de milhar são invertidos em relação ao inglês.
    # O upstream corrigiu recentemente o tratamento de separador de milhar
    # (fix(grounding) em #123), então este é o eixo com risco conhecido.
    {"query": "diminui a luz da sala para 35,0 por cento",
     "calls": [{"name": "control_lights",
                "arguments": {"room": "living_room", "action": "dim", "brightness_percent": 35}}],
     "category": "positive", "phenomenon": "formato_numerico",
     "rationale": "vírgula decimal onde o inglês usaria ponto"},
    {"query": "coloca o termostato em 22,5 graus",
     "calls": [{"name": "set_thermostat", "arguments": {"temperature": 22}}],
     "category": "positive", "phenomenon": "formato_numerico",
     "rationale": "decimal com vírgula num campo inteiro: exige truncar, não rejeitar"},
    {"query": "põe o termostato a vinte e dois graus",
     "calls": [{"name": "set_thermostat", "arguments": {"temperature": 22}}],
     "category": "positive", "phenomenon": "formato_numerico",
     "rationale": "número por extenso composto; em pt-BR leva 'e', diferente do inglês"},
    {"query": "deixa a luz do quarto em cinquenta por cento",
     "calls": [{"name": "control_lights",
                "arguments": {"room": "bedroom", "action": "dim", "brightness_percent": 50}}],
     "category": "positive", "phenomenon": "formato_numerico",
     "rationale": "porcentagem por extenso sem dígito nenhum na frase"},
    {"query": "diminui a luz da sala para 1.500 por cento", "calls": [], "category": "invalid",
     "critical": True, "phenomenon": "formato_numerico",
     "rationale": "ponto de milhar brasileiro: ler como 1.5 aceitaria um valor fora do bound"},

    # --- registro, imperativo e tratamento --------------------------------
    # O inglês tem uma forma imperativa. O português tem imperativo de tu, de
    # você, infinitivo usado como ordem, e perífrase com diminutivo.
    {"query": "ligue a luz da cozinha, por favor",
     "calls": [{"name": "control_lights", "arguments": {"room": "kitchen", "action": "on"}}],
     "category": "positive", "phenomenon": "registro",
     "rationale": "imperativo formal de 'você' + fórmula de cortesia"},
    {"query": "acender a luz do escritório",
     "calls": [{"name": "control_lights", "arguments": {"room": "study", "action": "on"}}],
     "category": "positive", "phenomenon": "registro",
     "rationale": "infinitivo como ordem, construção sem paralelo direto em inglês"},
    {"query": "dá uma acendida na luz do quarto",
     "calls": [{"name": "control_lights", "arguments": {"room": "bedroom", "action": "on"}}],
     "category": "positive", "phenomenon": "registro",
     "rationale": "perífrase 'dar uma -ida', altamente idiomática"},
    {"query": "abaixa um pouquinho a luz da sala", "calls": [], "category": "missing",
     "critical": True, "phenomenon": "registro",
     "rationale": "diminutivo como quantificador vago: não há número, então não há chamada"},
    {"query": "cê pode desligar o ventilador do quarto?",
     "calls": [{"name": "control_fan", "arguments": {"room": "bedroom", "action": "off"}}],
     "category": "positive", "phenomenon": "registro",
     "rationale": "'cê' reduzido e pedido em forma de pergunta"},
    {"query": "manda o aspirador pra base",
     "calls": [{"name": "start_robot_vacuum", "arguments": {"action": "dock"}}],
     "category": "positive", "phenomenon": "registro",
     "rationale": "'pra' contraído e verbo 'mandar' no lugar de 'enviar'"},

    # --- acento ausente e erro de digitação --------------------------------
    # Entrada real de teclado de celular. Como a decodificação é byte-level,
    # a ausência de acento muda os bytes de verdade, não só a aparência.
    {"query": "liga a luz da cozinha as 8",
     "calls": [], "category": "irrelevant", "phenomenon": "sem_acento",
     "rationale": "'as' sem crase introduz agendamento, que nenhuma tool suporta"},
    {"query": "nao acende a luz do escritorio", "calls": [], "category": "negation",
     "critical": True, "phenomenon": "sem_acento",
     "rationale": "negação sem acento: 'nao' precisa negar tão bem quanto 'não'"},
    {"query": "desliga o ventilador do quarto por favor",
     "calls": [{"name": "control_fan", "arguments": {"room": "bedroom", "action": "off"}}],
     "category": "positive", "phenomenon": "sem_acento",
     "rationale": "frase correta sem acento nenhum a perder: controle do eixo"},
    {"query": "abre a persiana da cozinah",
     "calls": [], "category": "missing", "critical": True, "phenomenon": "sem_acento",
     "rationale": "typo por transposição no alvo; inventar 'cozinha' seria adivinhar"},
    {"query": "poe o termostato em 21 graus",
     "calls": [{"name": "set_thermostat", "arguments": {"temperature": 21}}],
     "category": "positive", "phenomenon": "sem_acento",
     "rationale": "'poe' sem acento para 'põe', vogal nasal perdida"},

    # --- paralelo, que o espelho cobre pouco -------------------------------
    {"query": "apaga a luz da sala e fecha as persianas de la",
     "calls": [{"name": "control_lights", "arguments": {"room": "living_room", "action": "off"}},
               {"name": "control_blinds", "arguments": {"room": "living_room", "action": "close"}}],
     "category": "parallel", "phenomenon": "sem_acento",
     "rationale": "anáfora 'de lá' sem acento: o segundo cômodo só existe por referência"},
]
