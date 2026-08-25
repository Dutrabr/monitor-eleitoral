import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.auto_aprovacao import (
    gerar_decisoes_automaticas,
    segmento_elegivel,
    video_e_falante_unico,
    video_menciona_o_proprio_candidato,
)


def _seg(**kw):
    base = {
        "texto": "algum texto",
        "status": "ok",
        "falante": "SPEAKER_00",
        "no_speech_prob": 0.05,
        "avg_logprob": -0.1,
        "compression_ratio": 1.3,
        "pureza_falante": 1.0,
    }
    base.update(kw)
    return base


# --- segmento_elegivel -------------------------------------------------

def test_segmento_elegivel_com_sinais_bons():
    assert segmento_elegivel(_seg()) is True


def test_segmento_nao_elegivel_no_speech_alto():
    assert segmento_elegivel(_seg(no_speech_prob=0.16)) is False


def test_segmento_nao_elegivel_logprob_baixo():
    assert segmento_elegivel(_seg(avg_logprob=-0.31)) is False


def test_segmento_nao_elegivel_compressao_alta():
    assert segmento_elegivel(_seg(compression_ratio=2.1)) is False


def test_segmento_nao_elegivel_pureza_menor_que_um():
    assert segmento_elegivel(_seg(pureza_falante=0.8)) is False


def test_segmento_nao_elegivel_descartado():
    assert segmento_elegivel(_seg(status="descartado")) is False


def test_segmento_nao_elegivel_sem_metrica_whisper():
    """Transcricao vinda de legenda nao tem essas metricas — nunca auto-aprova."""
    assert segmento_elegivel(_seg(no_speech_prob=None)) is False


# --- video_e_falante_unico ----------------------------------------------

def test_video_falante_unico_true():
    segs = [_seg(falante="SPEAKER_00"), _seg(falante="SPEAKER_00")]
    assert video_e_falante_unico(segs) is True


def test_video_dois_falantes_false():
    segs = [_seg(falante="SPEAKER_00"), _seg(falante="SPEAKER_01")]
    assert video_e_falante_unico(segs) is False


def test_video_sem_falante_nenhum_false():
    segs = [_seg(falante=None), _seg(falante=None)]
    assert video_e_falante_unico(segs) is False


def test_video_ignora_descartados_na_contagem():
    segs = [_seg(falante="SPEAKER_00"), _seg(falante="SPEAKER_01", status="descartado")]
    assert video_e_falante_unico(segs) is True


# --- gerar_decisoes_automaticas ------------------------------------------

def test_gera_confirmado_para_elegiveis_em_video_falante_unico():
    segs = [_seg(), _seg()]
    decisoes = gerar_decisoes_automaticas(segs, "candidato_fulano", {}, revisado_em="2026-08-19T00:00:00+00:00")
    assert decisoes["0"]["decisao"] == "confirmado"
    assert decisoes["0"]["falante_confirmado"] == "candidato_fulano"
    assert decisoes["1"]["decisao"] == "confirmado"


def test_nao_gera_decisao_para_segmento_nao_elegivel():
    segs = [_seg(), _seg(no_speech_prob=0.5)]
    decisoes = gerar_decisoes_automaticas(segs, "candidato_fulano", {}, revisado_em="2026-08-19T00:00:00+00:00")
    assert "0" in decisoes
    assert "1" not in decisoes


def test_video_multi_falante_nao_gera_nenhuma_decisao():
    segs = [_seg(falante="SPEAKER_00"), _seg(falante="SPEAKER_01")]
    decisoes = gerar_decisoes_automaticas(segs, "candidato_fulano", {}, revisado_em="2026-08-19T00:00:00+00:00")
    assert decisoes == {}


def test_nao_sobrescreve_decisao_ja_existente():
    segs = [_seg()]
    existentes = {"0": {"decisao": "rejeitado"}}
    decisoes = gerar_decisoes_automaticas(segs, "candidato_fulano", existentes, revisado_em="2026-08-19T00:00:00+00:00")
    assert decisoes["0"]["decisao"] == "rejeitado"


def test_marca_revisado_por_auto_aprovacao():
    segs = [_seg()]
    decisoes = gerar_decisoes_automaticas(segs, "candidato_fulano", {}, revisado_em="2026-08-19T00:00:00+00:00")
    assert decisoes["0"]["revisado_por"] == "auto_aprovacao_confianca"


def test_nao_muta_decisoes_original():
    segs = [_seg()]
    original = {}
    gerar_decisoes_automaticas(segs, "candidato_fulano", original, revisado_em="2026-08-19T00:00:00+00:00")
    assert original == {}


def _seg_texto(texto, **kw):
    base = {
        "texto": texto,
        "falante": "SPEAKER_00",
        "status": "ok",
        "no_speech_prob": 0.01,
        "avg_logprob": -0.1,
        "compression_ratio": 1.2,
        "pureza_falante": 1.0,
    }
    base.update(kw)
    return base


def test_barra_auto_aprovacao_quando_locutor_cita_o_nome_do_candidato():
    """Erro real de producao (2026-08-24): peca narrada em terceira pessoa,
    uma voz so', foi auto-aprovada como fala do proprio candidato."""
    segmentos = [_seg_texto("Orleans casou, se tornou pai e voltou pra cidade")]
    assert video_menciona_o_proprio_candidato(segmentos, "candidato_orleans_brandao")
    decisoes = gerar_decisoes_automaticas(
        segmentos, "candidato_orleans_brandao", {}, revisado_em="2026-08-25T00:00:00Z"
    )
    assert decisoes == {}


def test_fala_sem_o_proprio_nome_continua_auto_aprovando():
    segmentos = [_seg_texto("Nos vamos investir em saude e educacao para todos")]
    assert not video_menciona_o_proprio_candidato(segmentos, "candidato_acm_neto")
    decisoes = gerar_decisoes_automaticas(
        segmentos, "candidato_acm_neto", {}, revisado_em="2026-08-25T00:00:00Z"
    )
    assert decisoes["0"]["decisao"] == "confirmado"


def test_cargo_e_sobrenome_comum_no_falante_id_nao_barram_sozinhos():
    """Sem isso, 'professor'/'santos' casariam em quase toda fala e a
    auto-aprovacao morreria na pratica."""
    segmentos = [_seg_texto("O professor da escola publica precisa de valorizacao")]
    assert not video_menciona_o_proprio_candidato(
        segmentos, "candidato_professor_tulio_lopes"
    )
    assert not video_menciona_o_proprio_candidato(
        [_seg_texto("Vamos cuidar dos nossos santos e da nossa fe")],
        "candidato_renan_santos",
    )


def test_auto_apresentacao_legitima_tambem_barra_de_proposito():
    """'Eu sou Douglas Ruas' e' fala legitima dele, mas cai na revisao
    humana mesmo assim — trocar uma revisao a mais por nao publicar fala
    de terceiro e' o lado certo pra errar."""
    segmentos = [_seg_texto("Eu sou Douglas Ruas e conto com o seu voto")]
    assert video_menciona_o_proprio_candidato(segmentos, "candidato_douglas_ruas")
