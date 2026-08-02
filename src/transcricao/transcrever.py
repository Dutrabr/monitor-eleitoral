"""Wrapper do faster-whisper, configurado contra alucinacao.

Os parametros abaixo nao sao os defaults. Os defaults do Whisper favorecem
fluencia — ele preenche silencio com texto plausivel. Para uso jornalistico
queremos o oposto: preferir lacuna a invencao.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .modelos import Palavra, Segmento

# Modelos disponiveis: tiny, base, small, medium, large-v3, large-v3-turbo.
# Para pt-BR com nomes proprios e jargao politico, nao use abaixo de "medium".
MODELO_PADRAO = "large-v3"


def carregar_modelo(
    nome: str = MODELO_PADRAO,
    device: str = "auto",
    compute_type: str = "default",
):
    """Carrega o modelo. Import local para nao exigir a lib em quem so testa."""
    from faster_whisper import WhisperModel

    return WhisperModel(nome, device=device, compute_type=compute_type)


def _opcoes_conservadoras() -> dict[str, Any]:
    return {
        "language": "pt",
        "task": "transcribe",
        # timestamp por palavra: e' o que permite citar o segundo exato
        "word_timestamps": True,
        # VAD corta silencio antes de chegar ao modelo. Principal defesa
        # contra alucinacao em trilha sonora e pausa longa.
        "vad_filter": True,
        "vad_parameters": {
            "threshold": 0.5,
            "min_speech_duration_ms": 250,
            "min_silence_duration_ms": 700,
            "speech_pad_ms": 200,
        },
        # corta o loop de repeticao quando o modelo entra em ciclo
        "hallucination_silence_threshold": 2.0,
        "repetition_penalty": 1.1,
        "no_repeat_ngram_size": 3,
        # sem condicionar no texto anterior: reduz propagacao de erro, ao
        # custo de um pouco de coesao. Para citacao, vale a troca.
        "condition_on_previous_text": False,
        # limiares de descarte do proprio decoder
        "log_prob_threshold": -1.0,
        "no_speech_threshold": 0.6,
        "compression_ratio_threshold": 2.4,
        "beam_size": 5,
    }


def _converter_segmento(s: Any) -> Segmento:
    palavras: list[Palavra] = []
    for w in (s.words or []):
        palavras.append(
            Palavra(
                inicio=float(w.start),
                fim=float(w.end),
                texto=w.word,
                probabilidade=float(w.probability),
            )
        )
    return Segmento(
        inicio=float(s.start),
        fim=float(s.end),
        texto=s.text.strip(),
        avg_logprob=float(s.avg_logprob),
        no_speech_prob=float(s.no_speech_prob),
        compression_ratio=float(s.compression_ratio),
        palavras=palavras,
    )


def transcrever(
    caminho_audio: Path,
    modelo=None,
    nome_modelo: str = MODELO_PADRAO,
    **sobrescritas: Any,
) -> tuple[list[Segmento], dict[str, Any]]:
    """Transcreve e devolve (segmentos, info).

    `info` entra no manifesto: registra idioma detectado, duracao e os
    parametros usados, para que a transcricao seja reproduzivel.
    """
    modelo = modelo or carregar_modelo(nome_modelo)
    opcoes = {**_opcoes_conservadoras(), **sobrescritas}

    segmentos_iter, info = modelo.transcribe(str(caminho_audio), **opcoes)
    segmentos = [_converter_segmento(s) for s in segmentos_iter]

    meta = {
        "modelo": nome_modelo,
        "idioma_detectado": info.language,
        "probabilidade_idioma": round(float(info.language_probability), 4),
        "duracao_s": round(float(info.duration), 2),
        "duracao_apos_vad_s": round(float(info.duration_after_vad), 2),
        "opcoes": {
            k: v for k, v in opcoes.items() if k != "vad_parameters"
        },
        "vad_parameters": opcoes.get("vad_parameters"),
    }
    return segmentos, meta


def texto_corrido(segmentos: Iterable[Segmento]) -> str:
    return " ".join(s.texto for s in segmentos if s.texto).strip()
