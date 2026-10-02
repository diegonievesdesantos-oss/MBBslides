"""Editorial Logic Layer (v3.1): Action Title Engine + Parallel Wording Guarantee.

    proposition   the slide's semantic contract (what it asserts)        proposition.py
    ATE           proposition → accepted action title                     action_titles.py
    PWG           sibling messages written as siblings                    parallel.py, signatures.py
    horizontal    the argument read from the titles alone                 qa.py
    compiler      the orchestration, before compose() and plan()          compiler.py
    artifacts     editorial_report, headline_strip, editorial ghost deck  report.py

See docs/EDITORIAL_LAYER.md.
"""
from .compiler import MODES, compile_editorial, strip_editorial

__all__ = ["MODES", "compile_editorial", "strip_editorial"]
