import copy
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"

HAS_SOFFICE = shutil.which("soffice") is not None or shutil.which("libreoffice") is not None
needs_render = pytest.mark.skipif(not HAS_SOFFICE, reason="LibreOffice not installed")


@pytest.fixture
def alvora():
    return json.loads((EXAMPLES / "alvora" / "deck.json").read_text())


@pytest.fixture
def gallery():
    return json.loads((EXAMPLES / "gallery" / "deck.json").read_text())


def mini_spec(slides, deck_type="strategy_deck"):
    return {
        "meta": {"title": "Test deck", "deck_type": deck_type, "theme": "meridian"},
        "storyline": {"framework": "SCR", "governing_thought": "Test decks prove the engine works", "key_line": [{"id": "K1", "role": "situation", "message": "x"}, {"id": "K2", "role": "resolution", "message": "y"}]},
        "slides": copy.deepcopy(slides),
    }


def content_slide(**kw):
    s = {
        "id": "t1", "section": "K1", "purpose": "test", "headline": "Revenue grew 12% as volume rose in every region",
        "message_type": "trend", "evidence": [{"claim": "rev", "values": [100, 112]}],
        "visual": {"type": "column", "title": "Revenue", "unit": "€M", "data": {"categories": ["2024", "2025"], "series": [{"name": "Revenue", "values": [100, 112]}]}},
        "source": "Test data",
    }
    s.update(kw)
    return s
