"""Teste de integracao da pipeline com modelo falso.

Nao baixa modelo de ML: substitui o transcritor por um duble que devolve
segmentos controlados. O objetivo e' verificar a fiacao — proveniencia,
atribuicao, qualidade, fila de revisao — nao a acuracia do Whisper.
"""

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao import diarizar as mod_diarizar
from transcricao import pipeline, proveniencia
from transcricao.modelos import Status, Turno

ffmpeg_ok = shutil.which("ffmpeg") is not None
requer_ffmpeg = pytest.mark.skipif(not ffmpeg_ok, reason="ffmpeg ausente")


# --- dubles -----------------------------------------------------------------

@dataclass
class _W:
    start: float
    end: float
    word: str
    probability: float


@dataclass
class _S:
    start: float
    end: float
    text: str
    avg_logprob: float
    no_speech_prob: float
    compression_ratio: float
    words: list


@dataclass
class _Info:
    language: str = "pt"
    language_probability: float = 0.99
    duration: float = 6.0
    duration_after_vad: float = 5.4


def _palavras(texto, ini, fim, prob=0.95):
    partes = texto.split()
    passo = (fim - ini) / max(len(partes), 1)
    return [
        _W(ini + i * passo, ini + (i + 1) * passo, " " + w, prob)
        for i, w in enumerate(partes)
    ]


class ModeloFalso:
    """Duas falas: 0-3s de um falante, 3-6s de outro."""

    def transcribe(self, caminho, **kwargs):
        segs = [
            _S(
                0.0, 3.0,
                "vamos ampliar a rede federal de ensino tecnico",
                -0.20, 0.02, 1.35,
                _palavras("vamos ampliar a rede federal de ensino tecnico", 0.0, 3.0),
            ),
            _S(
                3.0, 6.0,
                "e como o senhor pretende financiar essa proposta",
                -0.22, 0.03, 1.30,
                _palavras("e como o senhor pretende financiar essa proposta", 3.0, 6.0),
            ),
        ]
        return iter(segs), _Info()


class ModeloRuidoso(ModeloFalso):
    """Um segmento bom e um claramente alucinado em silencio."""

    def transcribe(self, caminho, **kwargs):
        segs = [
            _S(
                0.0, 3.0,
                "o investimento em saude basica sera prioridade absoluta",
                -0.18, 0.02, 1.30,
                _palavras(
                    "o investimento em saude basica sera prioridade absoluta", 0.0, 3.0
                ),
            ),
            _S(
                3.0, 6.0,
                "Legendas pela comunidade Amara.org",
                -1.80, 0.94, 2.90,
                _palavras("Legendas pela comunidade Amara.org", 3.0, 6.0, prob=0.2),
            ),
        ]
        return iter(segs), _Info()


@pytest.fixture
def midia(tmp_path):
    """Arquivo de midia real, gerado pelo ffmpeg."""
    destino = tmp_path / "video_original.wav"
    subprocess.run(
        [
            "ffmpeg", "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
            "-ac", "1", "-ar", "16000", "-y", str(destino), "-loglevel", "error",
        ],
        check=True,
    )
    return destino


# --- proveniencia -----------------------------------------------------------

@requer_ffmpeg
def test_hash_estavel_e_verificavel(midia):
    h1 = proveniencia.hash_arquivo(midia)
    h2 = proveniencia.hash_arquivo(midia)
    assert h1 == h2 and len(h1) == 64
    assert proveniencia.verificar_integridade(midia, h1)
    assert not proveniencia.verificar_integridade(midia, "0" * 64)


@requer_ffmpeg
def test_manifesto_tem_campos_de_custodia(midia):
    m = proveniencia.manifesto(
        midia,
        fonte="youtube",
        url="https://exemplo/watch?v=abc",
        perfil="@canal",
        coletado_em="2026-07-29T12:00:00+00:00",
    )
    for campo in (
        "hash_sha256_original", "bytes", "fonte", "url",
        "coletado_em_utc", "manifesto_gerado_em_utc",
    ):
        assert campo in m
    assert m["coletado_em_utc"] == "2026-07-29T12:00:00+00:00"


@requer_ffmpeg
def test_extracao_de_audio_registra_comando(midia, tmp_path):
    reg = proveniencia.extrair_audio(midia, tmp_path / "out" / "a.wav")
    assert (tmp_path / "out" / "a.wav").exists()
    assert reg["taxa_amostragem"] == 16_000
    assert reg["canais"] == 1
    assert "ffmpeg" in reg["comando"]
    assert len(reg["hash_audio_extraido"]) == 64


# --- pipeline ---------------------------------------------------------------

@requer_ffmpeg
def test_sem_diarizacao_exige_revisao(midia, tmp_path):
    t = pipeline.processar(
        midia,
        fonte="youtube",
        saida=tmp_path / "saida",
        modelo=ModeloFalso(),
        usar_diarizacao=False,
    )
    assert t.diarizacao_disponivel is False
    assert t.exige_revisao_humana is True
    assert any("diarizacao" in a for a in t.avisos)


@requer_ffmpeg
def test_diarizacao_indisponivel_nao_falha_silenciosamente(
    midia, tmp_path, monkeypatch
):
    def explode(*a, **k):
        raise mod_diarizar.DiarizacaoIndisponivel("HF_TOKEN ausente")

    monkeypatch.setattr(mod_diarizar, "diarizar", explode)
    t = pipeline.processar(
        midia, fonte="youtube", saida=tmp_path / "s", modelo=ModeloFalso()
    )
    assert t.diarizacao_disponivel is False
    assert t.exige_revisao_humana is True
    assert t.proveniencia["diarizacao"]["disponivel"] is False


@requer_ffmpeg
def test_dois_falantes_sao_separados_e_exigem_revisao(
    midia, tmp_path, monkeypatch
):
    monkeypatch.setattr(
        mod_diarizar,
        "diarizar",
        lambda *a, **k: [Turno(0.0, 3.0, "SPEAKER_00"), Turno(3.0, 6.0, "SPEAKER_01")],
    )
    t = pipeline.processar(
        midia, fonte="debate", saida=tmp_path / "s", modelo=ModeloFalso()
    )
    assert t.diarizacao_disponivel is True
    assert t.falantes == ["SPEAKER_00", "SPEAKER_01"]
    assert t.multi_falante is True
    assert t.exige_revisao_humana is True  # regra travada: multi falante revisa
    # cada segmento tem um unico falante
    assert all(s.pureza_falante == 1.0 for s in t.segmentos if s.palavras)


@requer_ffmpeg
def test_falante_unico_com_diarizacao_pode_passar(midia, tmp_path, monkeypatch):
    monkeypatch.setattr(
        mod_diarizar, "diarizar", lambda *a, **k: [Turno(0.0, 6.0, "SPEAKER_00")]
    )
    t = pipeline.processar(
        midia, fonte="youtube", saida=tmp_path / "s", modelo=ModeloFalso()
    )
    assert t.multi_falante is False
    assert t.diarizacao_disponivel is True
    assert t.exige_revisao_humana is False


@requer_ffmpeg
def test_alucinacao_e_descartada(midia, tmp_path, monkeypatch):
    monkeypatch.setattr(
        mod_diarizar, "diarizar", lambda *a, **k: [Turno(0.0, 6.0, "SPEAKER_00")]
    )
    t = pipeline.processar(
        midia, fonte="instagram", saida=tmp_path / "s", modelo=ModeloRuidoso()
    )
    status = [s.status for s in t.segmentos]
    assert Status.DESCARTADO in status
    descartado = next(s for s in t.segmentos if s.status is Status.DESCARTADO)
    assert "amara" in descartado.texto.lower()


@requer_ffmpeg
def test_mapa_de_falantes_renomeia(midia, tmp_path, monkeypatch):
    monkeypatch.setattr(
        mod_diarizar, "diarizar", lambda *a, **k: [Turno(0.0, 6.0, "SPEAKER_00")]
    )
    t = pipeline.processar(
        midia,
        fonte="youtube",
        saida=tmp_path / "s",
        modelo=ModeloFalso(),
        mapa_falantes={"SPEAKER_00": "candidato_teste"},
    )
    assert t.falantes == ["candidato_teste"]


@requer_ffmpeg
def test_arquivos_de_saida_sao_json_valido(midia, tmp_path, monkeypatch):
    monkeypatch.setattr(
        mod_diarizar, "diarizar", lambda *a, **k: [Turno(0.0, 6.0, "SPEAKER_00")]
    )
    saida = tmp_path / "s"
    pipeline.processar(
        midia, fonte="youtube", saida=saida, modelo=ModeloFalso()
    )
    tj = saida / "video_original.transcricao.json"
    fj = saida / "video_original.fila_revisao.json"
    assert tj.exists() and fj.exists()

    dados = json.loads(tj.read_text(encoding="utf-8"))
    assert dados["proveniencia"]["fonte"] == "youtube"
    assert isinstance(dados["segmentos"], list)
    assert all(isinstance(s["status"], str) for s in dados["segmentos"])

    fila = json.loads(fj.read_text(encoding="utf-8"))
    assert "hash_sha256_original" in fila
    assert "itens" in fila and "resumo" in fila
    # descartados nao entram na fila
    assert all(i["status"] != "descartado" for i in fila["itens"])


@requer_ffmpeg
def test_fila_traz_timestamp_para_conferencia(midia, tmp_path, monkeypatch):
    monkeypatch.setattr(
        mod_diarizar, "diarizar", lambda *a, **k: [Turno(0.0, 6.0, "SPEAKER_00")]
    )
    t = pipeline.processar(
        midia, fonte="youtube", saida=tmp_path / "s", modelo=ModeloFalso()
    )
    fila = pipeline.fila_de_verificacao(t)
    assert fila["itens"]
    for item in fila["itens"]:
        assert item["timestamp"].count(":") == 2
        assert "inicio" in item


def test_hms_formata_certo():
    assert pipeline._hms(0) == "00:00:00"
    assert pipeline._hms(61) == "00:01:01"
    assert pipeline._hms(3671) == "01:01:11"
