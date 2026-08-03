"""Diarizacao via pyannote.audio, com degradacao explicita.

A diarizacao exige aceitar os termos de TRES modelos no Hugging Face (nao
dois — o terceiro so' aparece na hora de rodar, como dependencia
transitiva) e um token de acesso:
  - pyannote/speaker-diarization-3.1
  - pyannote/segmentation-3.0
  - pyannote/speaker-diarization-community-1 (usado por baixo dos panos
    pelo componente PLDA; nao esta' documentado como pre-requisito em
    lugar nenhum, so' aparece no erro se faltar)

Se o token nao estiver disponivel ou faltar aceitar algum dos tres, NAO
assumimos silenciosamente um unico falante: a transcricao volta marcada
como `diarizacao_disponivel=False`, o que forca revisao humana no
pipeline. Falhar silenciosamente aqui e' o pior bug possivel neste
projeto.

Testado ao vivo em 2026-08-03 com pyannote.audio 4.0.7. Duas mudancas de
API que quebravam com essa versao, ja' corrigidas:
  - `Pipeline.from_pretrained(..., use_auth_token=)` virou `token=`.
  - o retorno de `pipeline(audio)` deixou de ser um `Annotation` direto
    (com `.itertracks()`) e virou um `DiarizeOutput` com dois campos:
    `speaker_diarization` (com sobreposicao) e
    `exclusive_speaker_diarization` (sem sobreposicao). Usamos o
    exclusivo de proposito: fala simultanea de dois falantes e' o caso
    ambiguo que a regra 5 deste projeto proibe resolver sozinho.

Observado no mesmo teste: em audio curto (~19s, um so' locutor real), o
modelo super-segmentou e devolveu 3 rotulos de falante diferentes para a
mesma pessoa. Isso nao e' bug do codigo — e' limitacao conhecida do
modelo em trechos curtos — mas na pratica gera `multi_falante=True` com
mais frequencia do que o numero real de pessoas falando. O efeito colateral
e' seguro (forca revisao humana a mais, nunca a menos), so' nao e' preciso.
"""

from __future__ import annotations

import os
from pathlib import Path

from .modelos import Turno


class DiarizacaoIndisponivel(RuntimeError):
    pass


def token_hf() -> str | None:
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")


def carregar_pipeline(modelo: str = "pyannote/speaker-diarization-3.1"):
    token = token_hf()
    if not token:
        raise DiarizacaoIndisponivel(
            "HF_TOKEN ausente. Sem diarizacao, todo conteudo com possivel "
            "multiplo falante vai para revisao humana obrigatoria."
        )
    try:
        from pyannote.audio import Pipeline
    except ImportError as e:
        raise DiarizacaoIndisponivel(
            "pyannote.audio nao instalado (pip install pyannote.audio)"
        ) from e

    pipeline = Pipeline.from_pretrained(modelo, token=token)
    if pipeline is None:
        raise DiarizacaoIndisponivel(
            f"nao foi possivel carregar {modelo}. Aceite os termos do modelo "
            "no Hugging Face com a conta do token."
        )
    return pipeline


def diarizar(
    caminho_audio: Path,
    pipeline=None,
    min_falantes: int | None = None,
    max_falantes: int | None = None,
) -> list[Turno]:
    """Retorna os turnos de fala ordenados por inicio.

    Levanta DiarizacaoIndisponivel se nao houver como rodar. O chamador DEVE
    tratar essa excecao marcando o item para revisao — nunca ignorando.
    """
    pipeline = pipeline or carregar_pipeline()

    kwargs = {}
    if min_falantes is not None:
        kwargs["min_speakers"] = min_falantes
    if max_falantes is not None:
        kwargs["max_speakers"] = max_falantes

    saida = pipeline(str(caminho_audio), **kwargs)

    # `exclusive_speaker_diarization`: versao sem sobreposicao. Fala
    # simultanea de dois falantes e' exatamente o caso ambiguo que a regra
    # 5 do projeto proibe resolver por conta propria (atribuir a um dos
    # dois seria o erro que destroi o projeto) — usar a versao exclusiva
    # evita criar essa ambiguidade em vez de decidir por baixo dos panos.
    anotacao = saida.exclusive_speaker_diarization

    turnos = [
        Turno(inicio=float(seg.start), fim=float(seg.end), falante=str(rotulo))
        for seg, _, rotulo in anotacao.itertracks(yield_label=True)
    ]
    return sorted(turnos, key=lambda t: (t.inicio, t.fim))


def fundir_turnos_adjacentes(
    turnos: list[Turno], gap_maximo: float = 0.4
) -> list[Turno]:
    """Junta turnos consecutivos do mesmo falante separados por gap minimo.

    A diarizacao costuma fragmentar a fala continua em dezenas de turnos; isso
    faria o reagrupamento quebrar frases no meio sem necessidade.
    """
    if not turnos:
        return []
    saida = [Turno(turnos[0].inicio, turnos[0].fim, turnos[0].falante)]
    for t in turnos[1:]:
        ultimo = saida[-1]
        if t.falante == ultimo.falante and t.inicio - ultimo.fim <= gap_maximo:
            ultimo.fim = max(ultimo.fim, t.fim)
        else:
            saida.append(Turno(t.inicio, t.fim, t.falante))
    return saida
