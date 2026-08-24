"""
ATENCAO — limite conhecido desta funcao (achado em 2026-08-24):
`video_e_falante_unico` responde "ha' UMA voz nesse video?", nao "essa
voz e' a do candidato?". Um video narrado por locutor profissional tem
uma voz so' e passa por aqui — foi assim que 5 pecas de campanha
narradas em terceira pessoa ("Orleans casou, se tornou pai") foram
publicadas como palavra do proprio candidato.

Quem chama com `--falante-confirmado` esta' AFIRMANDO que a voz do video
e' a do candidato. Antes de usar a flag, confira que o video e' o
candidato falando, nao locutor/jingle/depoimento. Material desse tipo
existe e e' legitimo publicar — mas como `tipo_material:
"material_de_campanha"` (ver `revisao.montar_publicacao`), em secao
separada, nunca como fala dele.
Auto-aprovacao de segmentos de alta confianca — excecao PARCIAL a regra 2.

Regra 2 do projeto (CLAUDE.md) e' que nenhuma citacao vai ao ar sem um
humano ter ouvido o trecho. Esta excecao foi decisao explicita do dono do
projeto (2026-08-19): ele nao tem tempo pra revisar tudo e topou uma taxa
de erro estimada de ate' ~5% ("1 em 20") pras citacoes que passarem por
aqui, em troca de nao depender do tempo dele pra toda revisao.

Calibrado contra amostra real de 141 segmentos ja revisados a mao
(ver scripts/analisar_confianca_threshold.py). Com os 4 criterios abaixo,
87 dos 141 (62%) teriam sido auto-aprovados, com ZERO erros de texto
observados nesse grupo. Pela regra de tres (limite superior pra zero
eventos observados em n tentativas e' ~3/n), a taxa real de erro nesse
grupo fica em ate' ~3,4% com 95% de confianca — dentro do 5% aceito.

A amostra e' PEQUENA (so' 2 episodios de erro no total, nenhum caso de
video multi-falante testado ainda). Isso nao e' garantia, e' o melhor
corte possivel com o dado que existe agora — revisitar quando o volume
de revisao real crescer (ver Proximo no CLAUDE.md).

Restricoes que NUNCA relaxam, custe o que custar:
  - So' se aplica a video de UM UNICO falante do inicio ao fim. Video com
    mais de uma pessoa continua 100% na revisao humana normal, sem
    excecao — e' exatamente o cenario que a amostra nao testou ainda.
  - So' se aplica a segmento com as 4 metricas de confianca do Whisper
    presentes. Transcricao vinda de legenda do YouTube (sem essas
    metricas) nunca se qualifica.
  - `falante_id` de quem confirma a identidade continua sendo decidido
    fora daqui (mesma convencao de sempre: canal oficial do candidato,
    verificado no momento da coleta) — este modulo nunca adivinha quem
    fala, so' decide se o TEXTO transcrito e' confiavel o suficiente pra
    dispensar audicao humana.
"""

from __future__ import annotations

from typing import Any

from .revisao import Decisao, registrar_decisao

NO_SPEECH_MAX = 0.15
LOGPROB_MIN = -0.30
COMPRESSION_MAX = 2.0

REVISADO_POR_AUTO = "auto_aprovacao_confianca"


def segmento_elegivel(segmento: dict[str, Any]) -> bool:
    """Segmento individual bate os 4 sinais de confianca calibrados.

    Qualquer metrica ausente (None) reprova — e' o caso de transcricao
    vinda de legenda, que nunca tem avg_logprob/no_speech_prob/
    compression_ratio/pureza_falante do Whisper.
    """
    if segmento.get("status") == "descartado":
        return False
    no_speech = segmento.get("no_speech_prob")
    logprob = segmento.get("avg_logprob")
    compressao = segmento.get("compression_ratio")
    pureza = segmento.get("pureza_falante")
    if None in (no_speech, logprob, compressao, pureza):
        return False
    return (
        no_speech < NO_SPEECH_MAX
        and logprob > LOGPROB_MIN
        and compressao < COMPRESSION_MAX
        and pureza == 1.0
    )


def video_e_falante_unico(segmentos: list[dict[str, Any]]) -> bool:
    """Video inteiro tem um so' falante do inicio ao fim (nunca troca).

    Usa o `falante` bruto da diarizacao (SPEAKER_00 etc.), nao o
    `falante_confirmado` — esse campo so' existe apos revisao humana, que
    e' exatamente o que este modulo tenta dispensar quando seguro.
    """
    falantes = {s.get("falante") for s in segmentos if s.get("status") != "descartado"}
    falantes.discard(None)
    return len(falantes) == 1


def gerar_decisoes_automaticas(
    segmentos: list[dict[str, Any]],
    falante_id: str,
    decisoes: dict[str, Any],
    *,
    revisado_em: str,
) -> dict[str, Any]:
    """Gera CONFIRMADO automatico pros segmentos elegiveis de um video de
    falante unico. Devolve nova copia de `decisoes` (mesmo contrato de
    `registrar_decisao` — nunca muta o dict recebido).

    Se o video tiver mais de um falante, devolve `decisoes` inalterado:
    todo segmento continua exigindo revisao humana normal, sem excecao.
    """
    if not video_e_falante_unico(segmentos):
        return decisoes

    for i, seg in enumerate(segmentos):
        if str(i) in decisoes:
            continue  # ja tem decisao (humana ou auto anterior) — nao sobrescreve
        if segmento_elegivel(seg):
            decisoes = registrar_decisao(
                decisoes,
                i,
                Decisao.CONFIRMADO,
                texto_final=None,
                temas=None,
                falante=falante_id,
                revisado_por=REVISADO_POR_AUTO,
                revisado_em=revisado_em,
            )
    return decisoes
