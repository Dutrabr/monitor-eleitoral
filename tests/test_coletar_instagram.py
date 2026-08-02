from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.coletar_instagram import ColetaIndisponivel, _iso_utc, extrair_shortcode


def test_extrai_shortcode_de_url_reel():
    assert extrair_shortcode("https://www.instagram.com/reel/Cxyz123AbC/") == "Cxyz123AbC"


def test_extrai_shortcode_de_url_reels_plural():
    assert extrair_shortcode("https://www.instagram.com/reels/Cxyz123AbC/") == "Cxyz123AbC"


def test_extrai_shortcode_com_query_string():
    url = "https://www.instagram.com/reel/Cxyz123AbC/?igsh=abc123"
    assert extrair_shortcode(url) == "Cxyz123AbC"


def test_rejeita_post_comum():
    with pytest.raises(ColetaIndisponivel):
        extrair_shortcode("https://www.instagram.com/p/Cxyz123AbC/")


def test_rejeita_story():
    with pytest.raises(ColetaIndisponivel):
        extrair_shortcode("https://www.instagram.com/stories/algumcanal/123456/")


def test_rejeita_perfil():
    with pytest.raises(ColetaIndisponivel):
        extrair_shortcode("https://www.instagram.com/algumcanal/")


def test_iso_utc_marca_offset_quando_naive():
    dt = datetime(2026, 7, 29, 21, 0, 0)
    assert _iso_utc(dt) == "2026-07-29T21:00:00+00:00"


def test_iso_utc_preserva_quando_ja_tem_tz():
    dt = datetime(2026, 7, 29, 21, 0, 0, tzinfo=timezone.utc)
    assert _iso_utc(dt) == "2026-07-29T21:00:00+00:00"
