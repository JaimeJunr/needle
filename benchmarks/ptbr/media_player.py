"""Espelho pt-BR do environment media_player.

Tradução fiel, não adaptação: cada query pt diz exatamente o que a query en
dizia, para que o delta de acerto seja atribuível ao idioma e a mais nada.
Casos idiomáticos de português vivem em `stress.py`, fora deste score.

Títulos de música, artista e gênero são nomes próprios / nomes de gênero:
ficam no original e não entram em FREE_TEXT. O modelo copia o trecho
('Purple Rain by Prince', 'smooth jazz'), não reescreve.
"""

from typing import Annotated

import needle
from needle.environments import media_player as EN

from ._mirror import build_cases


FREE_TEXT = {}


QUERIES = {
    # positive
    "play Purple Rain by Prince": "toca Purple Rain by Prince",
    "put on some smooth jazz": "coloca um smooth jazz",
    "queue up Blinding Lights by The Weeknd": "coloca na fila Blinding Lights by The Weeknd",
    "play some lofi beats": "toca um lofi beats",
    "put on Hotel California by the Eagles": "coloca Hotel California by the Eagles",
    "play Bohemian Rhapsody by Queen": "toca Bohemian Rhapsody by Queen",
    "set the volume to 40": "coloca o volume em 40",
    "turn the volume up to 85": "sobe o volume pra 85",
    "lower the volume to 15": "abaixa o volume pra 15",
    "set the speaker volume to 60": "coloca o volume da caixa em 60",
    "crank the volume up to 95": "joga o volume pra 95",
    "pause the music": "pausa a música",
    "hit pause on the song": "aperta o pause na música",
    "pause playback while I take this call": "pausa a reprodução enquanto eu atendo essa ligação",
    "resume the music": "retoma a música",
    "resume playback where it left off": "retoma a reprodução de onde parou",
    "skip this song": "pula essa música",
    "skip to the next track": "pula pra próxima faixa",
    # missing
    "turn up the volume a little": "sobe um pouco o volume",
    "play something for me": "toca alguma coisa pra mim",
    "turn the music down a bit": "abaixa um pouco a música",
    "play whatever you think I'd like": "toca o que você achar que eu gostaria",
    # irrelevant
    "put on the podcast Hard Fork": "coloca o podcast Hard Fork",
    "tune into the radio station Jazz FM": "sintoniza a rádio Jazz FM",
    "add this song to my favorites playlist": "adiciona essa música na playlist de favoritos",
    # negation
    "don't pause the song, I love this part": "não pausa a música, eu amo essa parte",
    "do not turn the volume up to 90": "não sobe o volume pra 90",
    "never play Baby Shark on this speaker again": "nunca toca Baby Shark nessa caixa de novo",
    # invalid
    "set the volume to 140": "coloca o volume em 140",
    "turn the volume up to 500": "sobe o volume pra 500",
    # parallel
    "set the volume to 55 and play Clair de Lune by Debussy":
        "coloca o volume em 55 e toca Clair de Lune by Debussy",
    "pause the music and turn the volume down to 20":
        "pausa a música e abaixa o volume pra 20",
}


TEST_CASES = build_cases(EN, QUERIES, free_text=FREE_TEXT)


# --- braço pt/pt: mesma superfície, descrições em português ----------------

@needle.tool
def play_music(query: Annotated[str, needle.Field(min_length=1, max_length=80)]):
    """Toca música por nome de música, artista, álbum ou gênero. Copie o pedido palavra por palavra. Use as tools de reprodução para pausar, retomar ou pular.

    Args:
        query: A música, o artista, o álbum ou o gênero, copiado palavra por palavra.
    """
    return {"ok": True, "query": query}


@needle.tool
def pause_media():
    """Pausa a mídia que está tocando. Não recebe argumentos."""
    return {"ok": True, "state": "paused"}


@needle.tool
def resume_media():
    """Retoma a reprodução pausada. Começar algo novo é play_music. Não recebe argumentos."""
    return {"ok": True, "state": "playing"}


@needle.tool
def skip_track():
    """Pula para a próxima faixa. Não recebe argumentos."""
    return {"ok": True, "state": "skipped"}


@needle.tool
def set_volume(level: Annotated[int, needle.Field(ge=0, le=100)]):
    """Ajusta o volume da caixa. Isso nunca pausa nem pula nada.

    Args:
        level: Nível de volume de 0 a 100.
    """
    return {"ok": True, "level": level}


TOOLS_PT = [play_music, pause_media, resume_media, skip_track, set_volume]

SYSTEM_PT = (
    "Mapeie cada ação de mídia explicitamente pedida e suportada para exatamente uma chamada "
    "declarada; nunca duplique uma ação. Não adivinhe valores que faltam. Pedidos não "
    "suportados, inválidos, ambíguos ou negados não retornam chamada nenhuma."
)
