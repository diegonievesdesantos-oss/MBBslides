import itertools

from cpe.charts.numfmt import excel_code, fmt, nice_scale
from cpe.design import text_metrics as tm
from cpe.design.tokens import GRID, SLIDE_W, available_themes, contrast_ratio, load_profile, load_theme
from cpe.layout.engine import load_library, resolve_zones


def test_text_metrics_are_real_and_monotonic():
    w10 = tm.text_width_in("Revenue growth slowed", 10)
    w20 = tm.text_width_in("Revenue growth slowed", 20)
    assert 0.8 < w10 < 1.8 and abs(w20 - 2 * w10) < 0.05
    assert tm.text_width_in("MMMM", 12) > tm.text_width_in("iiii", 12)
    assert tm.text_width_in("Bold", 12, bold=True) > tm.text_width_in("Bold", 12)
    lines = tm.wrap_lines("one two three four five six seven eight nine ten", 1.0, 12)
    assert len(lines) > 2 and all(tm.text_width_in(l, 12) <= 1.0 + 1e-6 for l in lines)


def test_themes_load_and_have_all_roles():
    roles = {"primary", "secondary", "highlight", "positive", "negative", "neutral", "muted", "background", "text", "text_muted"}
    for name in available_themes():
        th = load_theme(name)
        assert roles <= set(th.colors), name
        assert contrast_ratio(th.c("text"), th.c("background")) >= 7
        assert contrast_ratio(th.c("text_muted"), th.c("background")) >= 4.5


def test_profiles_map_deck_types():
    assert load_profile("board_presentation")["name"] == "board"
    assert load_profile("commercial_due_diligence")["name"] == "analytical"
    assert load_profile("unknown")["name"] == "standard"


def test_layout_library_is_consistent():
    lib = load_library()
    assert len(lib) >= 40
    families = {l.family for l in lib.values()}
    assert len(families) == 16
    for lay in lib.values():
        for tk in (False, True):
            zones = resolve_zones(lay, with_takeaway=tk)
            for z in zones.values():
                b = z.box
                assert b.x >= GRID.margin_l - 1e-6 and b.r <= SLIDE_W - GRID.margin_r + 1e-6, lay.id
                assert b.h > 0.3 and b.w > 0.5, (lay.id, z.name)
            for a, c in itertools.combinations(zones.values(), 2):
                assert a.box.intersection(c.box) < 1e-6, (lay.id, a.name, c.name)
        assert lay.when_to_use and lay.description, lay.id


def test_number_formatting():
    f = {"decimals": 1, "prefix": "€", "suffix": "M", "percent": False, "thousands": True, "plus": False}
    assert fmt(1234.56, f) == "€1,234.6M"
    assert fmt(-3.21, f) == "−€3.2M"
    assert fmt(5, f, plus=True) == "+€5.0M"
    assert excel_code(f) == '"€"#,##0.0"M";-"€"#,##0.0"M"'
    lo, hi, step = nice_scale(3, 97)
    assert lo == 0 and hi >= 97 and step in (10, 20, 25)
