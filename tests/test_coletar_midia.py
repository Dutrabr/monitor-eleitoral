import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.coletar_midia import (
    PlataformaNaoSuportada,
    detectar_plataforma,
    textos_ja_coletados,
)


@pytest.mark.parametrize(
    "url,esperado",
    [
        ("https://www.youtube.com/watch?v=abc", "youtube"),
        ("https://youtu.be/abc", "youtube"),
        ("https://www.instagram.com/reel/XYZ/", "instagram"),
        ("https://www.tiktok.com/@perfil/video/123", "tiktok"),
        ("https://www.facebook.com/reel/123", "facebook"),
        ("https://fb.watch/abc/", "facebook"),
    ],
)
def test_detecta_plataforma(url, esperado):
    assert detectar_plataforma(url) == esperado


def test_kwai_falha_explicitamente_em_vez_de_adivinhar():
    """Kwai nao tem extractor no yt-dlp. Gravar fonte errada na
    proveniencia seria pior que falhar na hora."""
    with pytest.raises(PlataformaNaoSuportada, match="Kwai"):
        detectar_plataforma("https://www.kwai.com/@candidato")


def test_url_desconhecida_falha():
    with pytest.raises(PlataformaNaoSuportada):
        detectar_plataforma("https://exemplo.com/video/1")


def test_textos_ja_coletados_le_a_fila(tmp_path):
    (tmp_path / "vid1.fila_revisao.json").write_text(
        json.dumps({"itens": [{"texto": "primeira parte"}, {"texto": "segunda parte"}]})
    )
    (tmp_path / "quebrado.fila_revisao.json").write_text("{nao e' json")
    textos = textos_ja_coletados(tmp_path)
    assert textos["vid1"] == "primeira parte segunda parte"
    assert "quebrado" not in textos  # arquivo ilegivel nao derruba a coleta
