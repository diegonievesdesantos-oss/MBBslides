"""Human-reference evaluation: blind pairwise (A/B) preference between two renders of a slide.

This is the THIRD, independent signal (docs/EVALS.md). It is never folded into the
automatic score: its purpose is to tell whether a higher automatic score actually
corresponds to a composition people prefer.

    cpe human build  -o evals/human_reference/rounds/r1  --pair v1.1.1=out/a v1.2=out/b [--pair …] [--n 40]
    cpe human serve  evals/human_reference/rounds/r1      # local blind A/B page, http://localhost:8765
    cpe human import evals/human_reference/rounds/r1 votes.jsonl   # votes collected elsewhere
    cpe human report evals/human_reference/rounds/r1 [--record]

A round directory holds
    pairs.json   what the PAGE sees: pair id + two anonymous image names. No version, layout,
                 score or side meaning.
    key.json     what the REPORT sees: which image is baseline / challenger, the comparison,
                 slide and scores. The server never serves it.
    img/         the renders under random names
    votes/       one JSONL per anonymous evaluator: {pair, left, right, choice: left|right|tie, ms, ts}

Blinding: images get random names; left/right is randomised per evaluator and pair; pair order is
randomised per evaluator (seeded by the evaluator id, so a resumed session keeps its order);
the page shows no version, layout name, composition or QA score.

Statistics (report): challenger wins / baseline wins / ties; preference rate among decisive votes
with a Wilson 95% interval; ties-as-half rate; per comparison; number of comparisons and
evaluators; left-side bias; agreement between evaluators on shared pairs (percent agreement and
Fleiss' kappa over {baseline, challenger, tie}); consistency on repeated (side-swapped) pairs.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import secrets
import shutil
import time
from pathlib import Path

ROUNDS = Path(__file__).resolve().parents[2] / "evals" / "human_reference" / "rounds"


# ── building a round ────────────────────────────────────────────────────────────

def _run_slides(run_dir: Path) -> dict:
    """slide id → {png, score, archetype} for a pipeline output directory."""
    res = json.loads((run_dir / "resolved.json").read_text())
    rep = json.loads((run_dir / "qa_report.json").read_text()) if (run_dir / "qa_report.json").exists() else {}
    comp = {c["slide_id"]: c for c in (rep.get("composition") or {}).get("slides", [])}
    pngs = sorted((run_dir / "renders").glob("slide-*.png"))
    out = {}
    for s, png in zip(res["slides"], pngs):
        c = comp.get(s.get("id")) or {}
        out[s.get("id")] = {"png": png, "score": c.get("score"), "archetype": c.get("archetype"), "kind": s.get("kind", "content"),
                            "layout": ((s.get("_plan") or {}).get("layout") or {}).get("id")}
    return out


def _digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def candidate_pairs(name: str, base_root: Path, chal_root: Path) -> list[dict]:
    """Every slide present in both roots (matched by deck directory + slide id) whose renders differ."""
    out = []
    for bdir in sorted(p for p in base_root.iterdir() if (p / "resolved.json").exists()):
        cdir = chal_root / bdir.name
        if not (cdir / "resolved.json").exists():
            continue
        b, c = _run_slides(bdir), _run_slides(cdir)
        for sid in b:
            if sid in c and b[sid]["kind"] in ("content", "exec_summary", "statement") and _digest(b[sid]["png"]) != _digest(c[sid]["png"]):
                out.append({"comparison": name, "deck": bdir.name, "slide": sid, "baseline": b[sid], "challenger": c[sid]})
    return out


def build_round(out_dir: str | Path, pairs_spec: list[tuple[str, str, str]], n: int = 40, repeats: int = 2, seed: int = 7) -> dict:
    """pairs_spec: [(comparison name, baseline root, challenger root)]. Samples up to n pairs
    (balanced across comparisons), plus `repeats` side-swapped duplicates for consistency."""
    out = Path(out_dir)
    if (out / "votes").exists() and any((out / "votes").iterdir()):
        raise SystemExit(f"{out} already has votes: build a new round instead of overwriting one")
    rng = random.Random(seed)
    pools = [candidate_pairs(name, Path(b), Path(c)) for name, b, c in pairs_spec]
    for p in pools:
        rng.shuffle(p)
    chosen: list[dict] = []
    while len(chosen) < n - repeats and any(pools):
        for p in pools:
            if p and len(chosen) < n - repeats:
                chosen.append(p.pop())
    (out / "img").mkdir(parents=True, exist_ok=True)
    (out / "votes").mkdir(exist_ok=True)
    pairs, key = [], {}
    for i, c in enumerate(chosen):
        pid = f"p{i + 1:03d}"
        names = {}
        for role in ("baseline", "challenger"):
            nm = secrets.token_hex(6) + ".png"
            shutil.copy(c[role]["png"], out / "img" / nm)
            names[role] = nm
        a, b = [names["baseline"], names["challenger"]]
        if rng.random() < 0.5:
            a, b = b, a
        pairs.append({"id": pid, "images": [a, b]})
        key[pid] = {"comparison": c["comparison"], "deck": c["deck"], "slide": c["slide"], "baseline": names["baseline"], "challenger": names["challenger"],
                    "archetype": c["challenger"]["archetype"], "baseline_score": c["baseline"]["score"], "challenger_score": c["challenger"]["score"],
                    "baseline_layout": c["baseline"]["layout"], "challenger_layout": c["challenger"]["layout"]}
    for j, src in enumerate(rng.sample(pairs, min(repeats, len(pairs)))):
        pid = f"r{j + 1:03d}"
        pairs.append({"id": pid, "images": list(reversed(src["images"]))})
        key[pid] = {**key[src["id"]], "repeat_of": src["id"]}
    comparisons = sorted({k["comparison"] for k in key.values()})
    meta = {"created": time.strftime("%Y-%m-%d"), "pairs": len(pairs),  # comparison names stay in key.json: they would unblind
            "instructions": "Which slide communicates its message better? Judge clarity, hierarchy and use of space — not the wording. Pick A, B or Tie."}
    (out / "pairs.json").write_text(json.dumps({"meta": meta, "pairs": pairs}, indent=2))
    (out / "key.json").write_text(json.dumps(key, indent=2))
    (out / "index.html").write_text(PAGE)
    return {"pairs": len(pairs), "by_comparison": {n_: sum(1 for k in key.values() if k["comparison"] == n_) for n_ in comparisons}}


# ── collecting votes ────────────────────────────────────────────────────────────

def _valid_evaluator(e: str) -> bool:
    return 1 <= len(e) <= 40 and all(ch.isalnum() or ch in "-_" for ch in e)


def record_vote(round_dir: Path, vote: dict) -> None:
    pairs = {p["id"]: p for p in json.loads((round_dir / "pairs.json").read_text())["pairs"]}
    e = str(vote.get("evaluator", ""))
    if not _valid_evaluator(e) or vote.get("pair") not in pairs or vote.get("choice") not in ("left", "right", "tie"):
        raise ValueError("invalid vote")
    p = pairs[vote["pair"]]
    if sorted([vote.get("left"), vote.get("right")]) != sorted(p["images"]):
        raise ValueError("images do not match the pair")
    rec = {k: vote.get(k) for k in ("pair", "left", "right", "choice", "ms")}
    rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(round_dir / "votes" / f"{e}.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")


def done_pairs(round_dir: Path, evaluator: str) -> list[str]:
    f = round_dir / "votes" / f"{evaluator}.jsonl"
    return [json.loads(line)["pair"] for line in f.read_text().splitlines() if line.strip()] if f.exists() else []


def import_votes(round_dir: str | Path, path: str | Path) -> int:
    """Import votes collected elsewhere: JSONL lines {evaluator, pair, left, right, choice}."""
    n = 0
    for line in Path(path).read_text().splitlines():
        if line.strip():
            record_vote(Path(round_dir), json.loads(line))
            n += 1
    return n


def serve(round_dir: str | Path, port: int = 8765, host: str = "127.0.0.1") -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, urlparse

    root = Path(round_dir).resolve()

    class H(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

        def do_GET(self):
            u = urlparse(self.path)
            if u.path in ("/", "/index.html"):
                return self._send(200, (root / "index.html").read_text(), "text/html; charset=utf-8")
            if u.path == "/pairs.json":
                return self._send(200, (root / "pairs.json").read_text())
            if u.path == "/state":
                e = (parse_qs(u.query).get("evaluator") or [""])[0]
                return self._send(200, json.dumps({"done": done_pairs(root, e) if _valid_evaluator(e) else []}))
            if u.path.startswith("/img/"):
                name = u.path[5:]
                if "/" in name or ".." in name or not (root / "img" / name).exists():
                    return self._send(404, "{}")
                return self._send(200, (root / "img" / name).read_bytes(), "image/png")
            return self._send(404, "{}")  # key.json and votes/ are never served

        def do_POST(self):
            if urlparse(self.path).path != "/vote":
                return self._send(404, "{}")
            try:
                n = int(self.headers.get("Content-Length", "0"))
                record_vote(root, json.loads(self.rfile.read(min(n, 4096))))
            except (ValueError, json.JSONDecodeError) as e:
                return self._send(400, json.dumps({"error": str(e)}))
            return self._send(200, "{}")

    srv = ThreadingHTTPServer((host, port), H)
    print(f"Blind A/B round {root.name}: open http://{host}:{port}  (Ctrl+C to stop; votes in {root / 'votes'})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


# ── statistics ──────────────────────────────────────────────────────────────────

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float | None, float | None]:
    """Wilson score interval for a binomial proportion (good coverage for small n and p near 0/1)."""
    if n == 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)


def fleiss_kappa(items: list[list[str]], cats=("baseline", "challenger", "tie")) -> float | None:
    """Fleiss' kappa over items rated by the same number (≥2) of raters."""
    items = [it for it in items if len(it) >= 2]
    if not items:
        return None
    m = min(len(it) for it in items)
    items = [it[:m] for it in items]
    N = len(items)
    pj = {c: sum(it.count(c) for it in items) / (N * m) for c in cats}
    Pi = [(sum(it.count(c) ** 2 for c in cats) - m) / (m * (m - 1)) for it in items]
    Pbar = sum(Pi) / N
    Pe = sum(v * v for v in pj.values())
    return None if Pe >= 1 else round((Pbar - Pe) / (1 - Pe), 3)


def _load_votes(round_dir: Path) -> list[dict]:
    out = []
    for f in sorted((round_dir / "votes").glob("*.jsonl")):
        latest = {}
        for line in f.read_text().splitlines():
            if line.strip():
                v = json.loads(line)
                latest[v["pair"]] = v  # a re-vote replaces the earlier one
        out += [{**v, "evaluator": f.stem} for v in latest.values()]
    return out


def outcome(v: dict, key: dict) -> str:
    if v["choice"] == "tie":
        return "tie"
    picked = v["left"] if v["choice"] == "left" else v["right"]
    return "challenger" if picked == key[v["pair"]]["challenger"] else "baseline"


def report(round_dir: str | Path) -> dict:
    rd = Path(round_dir)
    key = json.loads((rd / "key.json").read_text())
    votes = [v for v in _load_votes(rd) if v["pair"] in key]
    main = [v for v in votes if not key[v["pair"]].get("repeat_of")]

    def summary(vs):
        o = [outcome(v, key) for v in vs]
        cw, bw, t = o.count("challenger"), o.count("baseline"), o.count("tie")
        lo, hi = wilson(cw, cw + bw)
        return {"comparisons": len(vs), "challenger_wins": cw, "baseline_wins": bw, "ties": t,
                "challenger_preference": round(cw / (cw + bw), 3) if cw + bw else None, "challenger_preference_ci95": [lo, hi],
                "ties_as_half": round((cw + 0.5 * t) / len(vs), 3) if vs else None}

    res = {"round": rd.name, "evaluators": len({v["evaluator"] for v in votes}), **summary(main)}
    res["by_comparison"] = {c: summary([v for v in main if key[v["pair"]]["comparison"] == c]) for c in sorted({k["comparison"] for k in key.values()})}
    res["by_archetype"] = {a: summary([v for v in main if key[v["pair"]]["archetype"] == a]) for a in sorted({key[v["pair"]]["archetype"] or "?" for v in main})}
    # does the automatic score agree with people? (the question this signal exists to answer)
    agree = [v for v in main if outcome(v, key) != "tie" and key[v["pair"]]["baseline_score"] is not None and key[v["pair"]]["challenger_score"] is not None
             and abs(key[v["pair"]]["challenger_score"] - key[v["pair"]]["baseline_score"]) >= 1]
    hits = sum(1 for v in agree if (outcome(v, key) == "challenger") == (key[v["pair"]]["challenger_score"] > key[v["pair"]]["baseline_score"]))
    res["score_agreement"] = {"decisive_votes_with_score_gap": len(agree), "agree": hits, "rate": round(hits / len(agree), 3) if agree else None, "ci95": list(wilson(hits, len(agree)))}
    dec = [v for v in main if v["choice"] != "tie"]
    res["left_bias"] = {"left_share": round(sum(1 for v in dec if v["choice"] == "left") / len(dec), 3) if dec else None, "ci95": list(wilson(sum(1 for v in dec if v["choice"] == "left"), len(dec)))}
    by_pair: dict[str, list[str]] = {}
    for v in main:
        by_pair.setdefault(v["pair"], []).append(outcome(v, key))
    shared = [o for o in by_pair.values() if len(o) >= 2]
    res["inter_rater"] = {"shared_pairs": len(shared),
                          "percent_agreement": round(sum(1 for o in shared if len(set(o)) == 1) / len(shared), 3) if shared else None,
                          "fleiss_kappa": fleiss_kappa(shared)} if res["evaluators"] > 1 else {"note": "one evaluator: agreement needs ≥2"}
    rep = [v for v in votes if key[v["pair"]].get("repeat_of")]
    cons = []
    for v in rep:
        orig = next((w for w in main if w["pair"] == key[v["pair"]]["repeat_of"] and w["evaluator"] == v["evaluator"]), None)
        if orig:
            cons.append(outcome(v, key) == outcome(orig, key))
    res["self_consistency"] = {"repeated_pairs": len(cons), "consistent": sum(cons)}
    res["method"] = ("Preference = challenger wins / decisive votes, Wilson 95% interval (ties excluded; ties-as-half also shown). "
                     "Agreement: percent agreement and Fleiss' kappa over {baseline, challenger, tie} on pairs rated by ≥2 evaluators. "
                     "Human preference is an independent signal and is never part of the automatic composition score.")
    return res


def to_markdown(r: dict) -> str:
    def row(name, s):
        ci = s["challenger_preference_ci95"]
        return f"| {name} | {s['comparisons']} | {s['challenger_wins']} | {s['baseline_wins']} | {s['ties']} | {s['challenger_preference']} | {ci[0]}–{ci[1]} | {s['ties_as_half']} |"
    L = [f"# Human A/B preference — round {r['round']}", "", f"Evaluators: {r['evaluators']} · comparisons: {r['comparisons']}", "",
         "| scope | n | challenger wins | baseline wins | ties | challenger preference | 95% CI (Wilson) | ties as ½ |", "|---|---|---|---|---|---|---|---|",
         row("all", r)]
    L += [row(f"comparison `{k}`", v) for k, v in r["by_comparison"].items()]
    L += [row(f"archetype {k}", v) for k, v in r["by_archetype"].items() if v["comparisons"]]
    sa = r["score_agreement"]
    L += ["", f"**Does the automatic score agree with people?** {sa['agree']}/{sa['decisive_votes_with_score_gap']} decisive votes (rate {sa['rate']}, 95% CI {sa['ci95'][0]}–{sa['ci95'][1]})",
          f"**Left-side bias:** left chosen in {r['left_bias']['left_share']} of decisive votes (95% CI {r['left_bias']['ci95'][0]}–{r['left_bias']['ci95'][1]})",
          f"**Inter-rater:** {json.dumps(r['inter_rater'])}", f"**Self-consistency on repeated pairs:** {r['self_consistency']['consistent']}/{r['self_consistency']['repeated_pairs']}",
          "", f"_Method:_ {r['method']}"]
    return "\n".join(L) + "\n"


def record(r: dict) -> None:
    from .evals import record_result

    record_result("human_reference", {k: r[k] for k in ("round", "evaluators", "comparisons", "challenger_wins", "baseline_wins", "ties",
                                                         "challenger_preference", "challenger_preference_ci95", "ties_as_half", "by_comparison",
                                                         "score_agreement", "inter_rater", "method")})


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blind slide comparison</title>
<style>
:root{--bg:#f4f5f7;--fg:#1d232b;--muted:#5b6673;--card:#fff;--line:#d9dde3;--acc:#0b5cad}
@media (prefers-color-scheme:dark){:root{--bg:#15181c;--fg:#e8ebef;--muted:#9aa5b1;--card:#1e2328;--line:#343b43;--acc:#6aa9ff}}
*{box-sizing:border-box}body{margin:0;font:15px/1.4 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
header{display:flex;gap:16px;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid var(--line)}
main{padding:16px;max-width:1600px;margin:0 auto}.q{color:var(--muted);margin:0 0 12px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media (max-width:900px){.pair{grid-template-columns:1fr}}
figure{margin:0;background:var(--card);border:2px solid var(--line);border-radius:8px;padding:8px;cursor:pointer}
figure:hover{border-color:var(--acc)}figure img{width:100%;display:block;border:1px solid var(--line)}
figcaption{text-align:center;font-weight:600;padding-top:6px}
.bar{display:flex;gap:12px;justify-content:center;margin:16px 0}button{font:inherit;padding:10px 22px;border-radius:6px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}
button:hover{border-color:var(--acc)}kbd{border:1px solid var(--line);border-radius:4px;padding:0 5px;font-size:12px}
progress{width:220px}.done{text-align:center;padding:60px 16px}input{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}
</style></head><body>
<header><strong>Blind slide comparison</strong><span id="who"></span><span><progress id="prog" value="0" max="1"></progress> <span id="count"></span></span></header>
<main id="app"></main>
<script>
const app=document.getElementById('app');let data,order=[],i=0,shownAt=0,ev='';
function rng(seed){let h=2166136261;for(const c of seed){h^=c.charCodeAt(0);h=Math.imul(h,16777619)}return()=>{h^=h<<13;h^=h>>>17;h^=h<<5;return((h>>>0)%1e6)/1e6}}
function shuffle(a,r){for(let k=a.length-1;k>0;k--){const j=Math.floor(r()*(k+1));[a[k],a[j]]=[a[j],a[k]]}return a}
function getId(){let e='';try{e=localStorage.getItem('ab-evaluator')||''}catch(_){}return e}
function setId(e){try{localStorage.setItem('ab-evaluator',e)}catch(_){}}
async function start(){data=await (await fetch('pairs.json')).json();ev=getId();if(!ev)return ask();begin()}
function ask(){const sug='r-'+Math.random().toString(36).slice(2,7);app.innerHTML=`<div class="done"><p>${data.meta.instructions}</p>
<p>Your anonymous evaluator id (keep it to resume later):</p><p><input id="eid" value="${sug}" maxlength="40"> <button id="go">Start</button></p></div>`;
document.getElementById('go').onclick=()=>{const v=document.getElementById('eid').value.trim().replace(/[^A-Za-z0-9_-]/g,'');if(!v)return;ev=v;setId(v);begin()}}
async function begin(){document.getElementById('who').textContent='evaluator '+ev;const r=rng(ev);
const st=await (await fetch('state?evaluator='+encodeURIComponent(ev))).json();const done=new Set(st.done);
order=shuffle(data.pairs.map(p=>({...p,images:(r()<0.5?[...p.images]:[...p.images].reverse())})),r).filter(p=>!done.has(p.id));i=0;show()}
function show(){const total=data.pairs.length,left=order.length-i;document.getElementById('prog').max=total;document.getElementById('prog').value=total-left;
document.getElementById('count').textContent=(total-left)+' / '+total;if(i>=order.length){app.innerHTML='<div class="done"><h2>Done — thank you.</h2><p>You can close this page.</p></div>';return}
const p=order[i];app.innerHTML=`<p class="q">${data.meta.instructions}</p><div class="pair">
<figure data-c="left"><img src="img/${p.images[0]}" alt="Slide A"><figcaption>A <kbd>←</kbd> <kbd>1</kbd></figcaption></figure>
<figure data-c="right"><img src="img/${p.images[1]}" alt="Slide B"><figcaption>B <kbd>→</kbd> <kbd>2</kbd></figcaption></figure></div>
<div class="bar"><button data-c="left">A is better</button><button data-c="tie">Tie <kbd>T</kbd> <kbd>↓</kbd></button><button data-c="right">B is better</button></div>`;
app.querySelectorAll('[data-c]').forEach(el=>el.onclick=()=>vote(el.dataset.c));shownAt=performance.now()}
let busy=false;async function vote(c){if(busy||i>=order.length)return;busy=true;const p=order[i];
const body={evaluator:ev,pair:p.id,left:p.images[0],right:p.images[1],choice:c,ms:Math.round(performance.now()-shownAt)};
try{const r=await fetch('vote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(r.ok){i++;show()}else alert('Vote not saved: '+r.status)}
catch(e){alert('Vote not saved (is the server running?)')}busy=false}
document.addEventListener('keydown',e=>{if(!order.length)return;const k=e.key.toLowerCase();
if(k==='arrowleft'||k==='1'||k==='a')vote('left');else if(k==='arrowright'||k==='2'||k==='b')vote('right');else if(k==='t'||k==='arrowdown'||k==='0')vote('tie')});
start();
</script></body></html>
"""
