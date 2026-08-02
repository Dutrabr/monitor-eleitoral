import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.modelos import Palavra, Segmento, Status
from transcricao import qualidade


def seg(
    texto="o compromisso e' com a educacao publica de qualidade",
    inicio=0.0,
    fim=4.0,
    avg_logprob=-0.25,
    no_speech_prob=0.02,
    compression_ratio=1.4,
    palavras=None,
    falante="SPEAKER_00",
    pureza=1.0,
):
    if palavras is None:
        partes = texto.split()
        passo = (fim - inicio) / max(len(partes), 1)
        palavras = [
            Palavra(
                inicio=inicio + i * passo,
                fim=inicio + (i + 1) * passo,
                texto=" " + w,
                probabilidade=0.95,
                falante=falante,
            )
            for i, w in enumerate(partes)
        ]
    return Segmento(
        inicio=inicio,
        fim=fim,
        texto=texto,
        avg_logprob=avg_logprob,
        no_speech_prob=no_speech_prob,
        compression_ratio=compression_ratio,
        palavras=palavras,
        falante=falante,
        pureza_falante=pureza,
    )


def test_segmento_limpo_fica_ok():
    s = qualidade.avaliar_segmento(seg())
    assert s.status is Status.OK
    assert s.motivos == []


def test_no_speech_alto_descarta():
    s = qualidade.avaliar_segmento(seg(no_speech_prob=0.91))
    assert s.status is Status.DESCARTADO
    assert any("no_speech_prob" in m for m in s.motivos)


def test_logprob_baixo_vira_revisar():
    s = qualidade.avaliar_segmento(seg(avg_logprob=-1.6))
    assert s.status is Status.REVISAR


def test_compression_ratio_alto_vira_revisar():
    s = qualidade.avaliar_segmento(seg(compression_ratio=3.1))
    assert s.status is Status.REVISAR


def test_alucinacao_conhecida_descarta():
    s = qualidade.avaliar_segmento(seg(texto="Legendas pela comunidade Amara.org"))
    assert s.status is Status.DESCARTADO


def test_texto_vazio_descarta():
    s = qualidade.avaliar_segmento(seg(texto="   "))
    assert s.status is Status.DESCARTADO


def test_repeticao_em_loop_descarta():
    s = qualidade.avaliar_segmento(
        seg(texto="obrigado obrigado obrigado obrigado obrigado")
    )
    assert s.status is Status.DESCARTADO


def test_bigrama_repetido_descarta():
    s = qualidade.avaliar_segmento(
        seg(texto="vamos la vamos la vamos la vamos la vamos la", fim=8.0)
    )
    assert s.status is Status.DESCARTADO


def test_muitas_palavras_fracas_vira_revisar():
    palavras = [
        Palavra(inicio=i * 0.5, fim=(i + 1) * 0.5, texto=f" p{i}", probabilidade=0.2)
        for i in range(8)
    ]
    s = qualidade.avaliar_segmento(seg(palavras=palavras))
    assert s.status is Status.REVISAR
    assert any("probabilidade baixa" in m for m in s.motivos)


def test_taxa_de_chars_implausivel_vira_revisar():
    texto = "a" * 400
    s = qualidade.avaliar_segmento(seg(texto=texto, inicio=0.0, fim=2.0))
    assert s.status is Status.REVISAR
    assert any("chars/s" in m for m in s.motivos)


def test_segmento_curto_nao_aplica_taxa():
    s = qualidade.avaliar_segmento(seg(texto="sim", inicio=0.0, fim=0.4))
    assert s.status is Status.OK


def test_pureza_baixa_vira_revisar():
    s = qualidade.avaliar_segmento(seg(pureza=0.5))
    assert s.status is Status.REVISAR
    assert any("mistura falantes" in m for m in s.motivos)


def test_sem_falante_vira_revisar():
    s = qualidade.avaliar_segmento(seg(falante=None))
    assert s.status is Status.REVISAR
    assert any("sem falante" in m for m in s.motivos)


def test_repeticoes_consecutivas_descartadas():
    base = "vamos construir mais escolas tecnicas no pais"
    segs = [seg(texto=base, inicio=i * 4.0, fim=(i + 1) * 4.0) for i in range(4)]
    segs = qualidade.avaliar(segs)
    # primeiro e segundo passam; do terceiro em diante e' loop
    assert segs[0].status is Status.OK
    assert segs[2].status is Status.DESCARTADO
    assert segs[3].status is Status.DESCARTADO


def test_resumo_conta_certo():
    # textos distintos de proposito: texto igual acionaria a regra de
    # repeticao consecutiva e mudaria a classificacao esperada
    segs = qualidade.avaliar(
        [
            seg(texto="vamos ampliar a rede de creches em todo o pais"),
            seg(texto="a proposta inclui reforma do sistema tributario", no_speech_prob=0.99),
            seg(texto="o investimento em saude basica sera prioridade", avg_logprob=-2.0),
        ]
    )
    r = qualidade.resumo(segs)
    assert r == {"total": 3, "ok": 1, "revisar": 1, "descartado": 1}


def test_regra_de_repeticao_nao_afeta_textos_distintos():
    segs = qualidade.avaliar(
        [
            seg(texto="primeiro ponto do programa de governo apresentado"),
            seg(texto="segundo ponto trata da seguranca publica nacional"),
            seg(texto="terceiro ponto aborda a politica de habitacao"),
        ]
    )
    assert all(s.status is Status.OK for s in segs)
