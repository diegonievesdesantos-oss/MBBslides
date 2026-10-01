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
                 slide and scores. The server never serves it. Since v1.5 a new round keeps it
                 OUTSIDE the bundle, in .private/human_reference/keys/<round>/key.json (gitignored);
                 the bundle carries only key.sha256, a commitment checked when the key is used.
                 `cpe human close` reveals the key into the round once voting is over.
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

ROOT = Path(__file__).resolve().parents[2]
ROUNDS = ROOT / "evals" / "human_reference" / "rounds"
KEYS = ROOT / ".private" / "human_reference" / "keys"
# what an evaluator receives; nothing in it may reveal version, role, layout, score or mapping
BUNDLE = ("STATUS.json", "pairs.json", "index.html", "img", "votes", "key.sha256")


def _read(p: Path) -> str:
    return Path(p).read_text(encoding="utf-8")


def _write(p: Path, text: str) -> None:
    Path(p).write_text(text, encoding="utf-8")


def default_key_path(round_dir: str | Path) -> Path:
    return KEYS / Path(round_dir).name / "key.json"


def key_path(round_dir: str | Path, key: str | Path | None = None) -> Path:
    """The key of a round: an explicit path, a revealed/legacy key.json in the round (r1, r2), or
    the private default location."""
    if key:
        return Path(key)
    rd = Path(round_dir)
    return rd / "key.json" if (rd / "key.json").exists() else default_key_path(rd)


def load_key(round_dir: str | Path, key: str | Path | None = None) -> dict:
    kp = key_path(round_dir, key)
    if not kp.exists():
        raise SystemExit(f"no key for {Path(round_dir).name}: expected {kp} (pass --key PATH)")
    raw = kp.read_bytes()
    commit = Path(round_dir) / "key.sha256"
    if commit.exists() and hashlib.sha256(raw).hexdigest() != _read(commit).split()[0]:
        raise SystemExit(f"{kp} does not match the round's key.sha256 commitment")
    return json.loads(raw.decode("utf-8"))


# ── building a round ────────────────────────────────────────────────────────────

def _run_slides(run_dir: Path) -> dict:
    """slide id → {png, score, archetype} for a pipeline output directory."""
    res = json.loads((run_dir / "resolved.json").read_text(encoding="utf-8"))
    rep = json.loads((run_dir / "qa_report.json").read_text(encoding="utf-8")) if (run_dir / "qa_report.json").exists() else {}
    comp = {c["slide_id"]: c for c in (rep.get("composition") or {}).get("slides", [])}
    if (run_dir / "composition_measure.json").exists():  # re-measured with ONE scorer (cpe measure): comparable across engine versions
        comp = {c["slide_id"]: c for c in json.loads((run_dir / "composition_measure.json").read_text(encoding="utf-8"))["slides"]}
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


def build_round(out_dir: str | Path, pairs_spec: list[tuple[str, str, str]], n: int = 40, repeats: int = 2, seed: int = 7,
                quotas: dict | None = None, purpose: str = "", key_out: str | Path | None = None, private_key: bool = True,
                identical_controls: int = 0) -> dict:
    """pairs_spec: [(comparison name, baseline root, challenger root)]. Samples up to n pairs
    (balanced across comparisons), plus `repeats` side-swapped duplicates for consistency.
    `quotas` {archetype: k} (v1.4, round r2): first take k pairs of each named archetype, then fill
    the rest from the other archetypes (control cases) — balanced where the engine changed most."""
    out = Path(out_dir)
    if (out / "votes").exists() and any((out / "votes").iterdir()):
        raise SystemExit(f"{out} already has votes: build a new round instead of overwriting one")
    rng = random.Random(seed)
    pools = [candidate_pairs(name, Path(b), Path(c)) for name, b, c in pairs_spec]
    for p in pools:
        rng.shuffle(p)
    chosen: list[dict] = []
    if quotas:
        flat = [c for p in pools for c in p]
        for arch, k in quotas.items():
            take = [c for c in flat if c["challenger"]["archetype"] == arch][:k]
            chosen += take
            flat = [c for c in flat if c not in take]
        rest = [c for c in flat if c["challenger"]["archetype"] not in quotas]
        while len(chosen) < n - repeats and rest:
            chosen.append(rest.pop())
        for c in chosen:
            c["control"] = c["challenger"]["archetype"] not in quotas
    while len(chosen) < n - repeats and any(pools):
        for p in pools:
            p[:] = [c for c in p if c not in chosen]
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
                    "baseline_layout": c["baseline"]["layout"], "challenger_layout": c["challenger"]["layout"], "control": bool(c.get("control"))}
    # v1.6: identical-image controls — the same render twice under two random names. The rational
    # answer is "tie"; the tie rate estimates evaluator noise. Never part of the preference statistics.
    pool = [c for p_ in pools for c in p_] + chosen
    for j, c in enumerate(rng.sample(pool, min(identical_controls, len(pool)))):
        pid = f"c{j + 1:03d}"
        a, b = secrets.token_hex(6) + ".png", secrets.token_hex(6) + ".png"
        for nm in (a, b):
            shutil.copy(c["challenger"]["png"], out / "img" / nm)
        pairs.append({"id": pid, "images": [a, b]})
        key[pid] = {"comparison": "identical control", "deck": c["deck"], "slide": c["slide"], "baseline": a, "challenger": b,
                    "archetype": c["challenger"]["archetype"], "baseline_score": c["challenger"]["score"], "challenger_score": c["challenger"]["score"],
                    "baseline_layout": c["challenger"]["layout"], "challenger_layout": c["challenger"]["layout"], "control": True, "identical_control": True}
    for j, src in enumerate(rng.sample([p_ for p_ in pairs if p_["id"].startswith("p")], min(repeats, len(chosen)))):
        pid = f"r{j + 1:03d}"
        pairs.append({"id": pid, "images": list(reversed(src["images"]))})
        key[pid] = {**key[src["id"]], "repeat_of": src["id"]}
    comparisons = sorted({k["comparison"] for k in key.values()})
    meta = {"created": time.strftime("%Y-%m-%d"), "pairs": len(pairs),  # comparison names stay in key.json: they would unblind
            "instructions": "Which slide communicates its message better? Judge clarity, hierarchy and use of space — not the wording. Pick A, B or Tie."}
    _write(out / "pairs.json", json.dumps({"meta": meta, "pairs": pairs}, indent=2))
    key_doc = json.dumps(key, indent=2)
    if private_key:  # v1.5: the key never sits next to what evaluators receive
        kp = Path(key_out) if key_out else default_key_path(out)
        kp.parent.mkdir(parents=True, exist_ok=True)
        _write(kp, key_doc)
        _write(kp.parent / "PURPOSE.txt", purpose + "\n")  # the purpose names the versions compared
        _write(out / "key.sha256", hashlib.sha256(key_doc.encode("utf-8")).hexdigest() + "  key.json\n")
    else:
        _write(out / "key.json", key_doc)
    _write(out / "index.html", PAGE)
    write_status(out, {"round": out.name, "created": meta["created"], "purpose": "blind A/B round" if private_key else purpose, "blind": True,
                       "used_for_calibration": False, "status": "awaiting human votes", "key": "private" if private_key else "in round"})
    return {"pairs": len(pairs), "key": str(kp) if private_key else str(out / "key.json"),
            "by_comparison": {n_: sum(1 for k in key.values() if k["comparison"] == n_) for n_ in comparisons}}


def build_text_round(out_dir: str | Path, pairs_spec: list[tuple[str, str, str]], context_dir: str | Path | None = None, repeats: int = 2,
                     seed: int = 7, kind: str = "storyline", key_out: str | Path | None = None, purpose: str = "") -> dict:
    """Blind A/B of REASONING, before any rendering (v1.7): two storylines (or two deck outlines) of the
    same case, as text. pairs_spec: [(comparison, dir_A_baseline, dir_B_challenger)]; each dir holds
    <case>.md; `context_dir` may hold <case>.md with the business question and a short source summary.
    Same blinding, private key and voting package as slide rounds."""
    out = Path(out_dir)
    if (out / "votes").exists() and any((out / "votes").iterdir()):
        raise SystemExit(f"{out} already has votes: build a new round instead of overwriting one")
    rng = random.Random(seed)
    (out / "txt").mkdir(parents=True, exist_ok=True)
    (out / "votes").mkdir(exist_ok=True)
    pairs, key = [], {}
    for comp, a_dir, b_dir in pairs_spec:
        for fa in sorted(Path(a_dir).glob("*.md")):
            fb = Path(b_dir) / fa.name
            if not fb.exists() or _read(fa).strip() == _read(fb).strip():
                continue
            names = {}
            for role, f in (("baseline", fa), ("challenger", fb)):
                nm = secrets.token_hex(6) + ".md"
                _write(out / "txt" / nm, _read(f))
                names[role] = nm
            ctx = None
            if context_dir and (Path(context_dir) / fa.name).exists():
                ctx = secrets.token_hex(6) + ".md"
                _write(out / "txt" / ctx, _read(Path(context_dir) / fa.name))
            a, b = names["baseline"], names["challenger"]
            if rng.random() < 0.5:
                a, b = b, a
            pid = f"p{len(pairs) + 1:03d}"
            pairs.append({"id": pid, "images": [a, b], **({"context": ctx} if ctx else {})})
            key[pid] = {"comparison": comp, "deck": fa.stem, "slide": kind, "baseline": names["baseline"], "challenger": names["challenger"],
                        "archetype": kind, "baseline_score": None, "challenger_score": None, "control": False}
    for j, src in enumerate(rng.sample(pairs, min(repeats, len(pairs)))):
        pid = f"r{j + 1:03d}"
        pairs.append({**src, "id": pid, "images": list(reversed(src["images"]))})
        key[pid] = {**key[src["id"]], "repeat_of": src["id"]}
    q = {"storyline": "Which storyline would you take to the client? Judge the answer, the logic, the prioritisation and how useful it is for the decision — not the wording.",
         "outline": "Which deck outline would you take to the client? Judge the argument the headlines make, what is included and what is left out — not the wording."}
    meta = {"created": time.strftime("%Y-%m-%d"), "pairs": len(pairs), "kind": "text", "instructions": q.get(kind, q["storyline"])}
    _write(out / "pairs.json", json.dumps({"meta": meta, "pairs": pairs}, indent=2))
    key_doc = json.dumps(key, indent=2)
    kp = Path(key_out) if key_out else default_key_path(out)
    kp.parent.mkdir(parents=True, exist_ok=True)
    _write(kp, key_doc)
    _write(kp.parent / "PURPOSE.txt", purpose + "\n")
    _write(out / "key.sha256", hashlib.sha256(key_doc.encode("utf-8")).hexdigest() + "  key.json\n")
    _write(out / "index.html", PAGE)
    write_status(out, {"round": out.name, "created": meta["created"], "purpose": f"blind A/B of {kind}s", "blind": True, "used_for_calibration": False,
                       "status": "awaiting human votes", "key": "private"})
    return {"pairs": len(pairs), "key": str(kp)}


def close_round(round_dir: str | Path, key: str | Path | None = None) -> dict:
    """End voting and reveal the key into the round (after which the round is no longer blind
    for anyone who reads the repository)."""
    rd = Path(round_dir)
    k = load_key(rd, key)  # verifies the commitment
    _write(rd / "key.json", json.dumps(k, indent=2))
    st = read_status(rd)
    st.update(blind=False, key="revealed", closed=time.strftime("%Y-%m-%d"), status=st.get("status", "") + "; voting closed, key revealed")
    write_status(rd, st)
    return st


# ── collecting votes ────────────────────────────────────────────────────────────

def _valid_evaluator(e: str) -> bool:
    return 1 <= len(e) <= 40 and all(ch.isalnum() or ch in "-_" for ch in e)


def record_vote(round_dir: Path, vote: dict) -> None:
    pairs = {p["id"]: p for p in json.loads(_read(round_dir / "pairs.json"))["pairs"]}
    e = str(vote.get("evaluator", ""))
    if not _valid_evaluator(e) or vote.get("pair") not in pairs or vote.get("choice") not in ("left", "right", "tie"):
        raise ValueError("invalid vote")
    p = pairs[vote["pair"]]
    if sorted([vote.get("left"), vote.get("right")]) != sorted(p["images"]):
        raise ValueError("images do not match the pair")
    rec = {k: vote.get(k) for k in ("pair", "left", "right", "choice", "ms")}
    rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (round_dir / "votes").mkdir(exist_ok=True)  # git does not keep empty folders
    with open(round_dir / "votes" / f"{e}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def undo_last_vote(round_dir: Path, evaluator: str) -> str | None:
    """Remove the evaluator's most recent vote (a mis-click) and return its pair id, so the page can
    show that pair again. Only the last vote can be undone, one at a time."""
    f = Path(round_dir) / "votes" / f"{evaluator}.jsonl"
    if not _valid_evaluator(evaluator) or not f.exists():
        return None
    lines = [ln for ln in _read(f).splitlines() if ln.strip()]
    if not lines:
        return None
    last = json.loads(lines[-1])["pair"]
    _write(f, "".join(ln + "\n" for ln in lines[:-1]))
    return last


def done_pairs(round_dir: Path, evaluator: str) -> list[str]:
    f = round_dir / "votes" / f"{evaluator}.jsonl"
    return [json.loads(line)["pair"] for line in _read(f).splitlines() if line.strip()] if f.exists() else []


def import_votes(round_dir: str | Path, path: str | Path) -> int:
    """Import votes collected elsewhere: JSONL lines {evaluator, pair, left, right, choice}. A file
    returned from a voting package (votes/<evaluator>.jsonl, lines without "evaluator") takes the
    evaluator id from its file name. Lines already present for that evaluator are skipped."""
    n = 0
    path = Path(path)
    for line in _read(path).splitlines():
        if line.strip():
            v = json.loads(line)
            v.setdefault("evaluator", path.stem)
            if v["pair"] in done_pairs(Path(round_dir), v["evaluator"]):
                continue
            record_vote(Path(round_dir), v)
            n += 1
    return n


def package_round(round_dir: str | Path, out_zip: str | Path) -> dict:
    """A self-contained voting package for evaluators who must NOT receive the repository (the key of
    a closed round is in its history): the evaluator bundle + a stdlib-only server + instructions.
    Refuses to include anything but the bundle."""
    import zipfile

    rd = Path(round_dir)
    files = [rd / "pairs.json", rd / "index.html", *sorted((rd / "img").glob("*.png")), *sorted((rd / "txt").glob("*.md"))]
    out = Path(out_zip)
    out.parent.mkdir(parents=True, exist_ok=True)
    server = (Path(__file__).parent / "vote_server.py").read_text(encoding="utf-8")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, f"{rd.name}/{f.relative_to(rd).as_posix()}")
        z.writestr(f"{rd.name}/votes/.keep", "")
        z.writestr(f"{rd.name}/vote_server.py", server)
        z.writestr(f"{rd.name}/VOTAR_WINDOWS.bat", "@echo off\r\ncd /d %~dp0\r\nstart http://127.0.0.1:8765\r\npy vote_server.py\r\npause\r\n")
        z.writestr(f"{rd.name}/LEEME_README.txt", PACKAGE_README)
    names = zipfile.ZipFile(out).namelist()
    assert not any(n.endswith(("key.json", "key.sha256", "STATUS.json", "PURPOSE.txt", "report.json", "report.md")) for n in names)
    return {"zip": str(out), "files": len(names), "images": len([f for f in files if f.suffix == ".png"]), "texts": len([f for f in files if f.suffix == ".md"])}


PACKAGE_README = """Blind slide comparison — voting package / Paquete de votación

ES
1. Descomprime esta carpeta en cualquier sitio (por ejemplo, el Escritorio).
2. Windows: doble clic en VOTAR_WINDOWS.bat (abre el navegador y arranca el servidor).
   Mac/Linux: abre una terminal en la carpeta y ejecuta:  python3 vote_server.py
   y abre http://127.0.0.1:8765
   (Necesitas Python 3.8 o superior. No hace falta instalar nada más.)
3. Pon un identificador anónimo (o deja el sugerido) y pulsa Start.
4. En cada pareja elige la slide que comunica mejor su mensaje (claridad, jerarquía, uso del
   espacio; no la redacción), o Tie si no ves diferencia. Algunas parejas se repiten o son
   iguales a propósito: vota lo que veas.
5. Al terminar ("Done — thank you") cierra la ventana negra del servidor.
6. Envía de vuelta el archivo que hay en la carpeta votes/ (se llama <tu-id>.jsonl).
No compartas tus votos con otros evaluadores antes de que voten.

EN
1. Unzip anywhere. 2. Windows: double-click VOTAR_WINDOWS.bat; macOS/Linux: python3 vote_server.py
and open http://127.0.0.1:8765 (Python 3.8+, nothing else). 3. Choose an anonymous id, Start.
4. Pick the slide that communicates its message better, or Tie. 5. Close the server window when done.
6. Send back the file in votes/ (<your-id>.jsonl). Do not discuss your votes with other evaluators first.
"""


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
                return self._send(200, _read(root / "index.html"), "text/html; charset=utf-8")
            if u.path == "/pairs.json":
                return self._send(200, _read(root / "pairs.json"))
            if u.path == "/state":
                e = (parse_qs(u.query).get("evaluator") or [""])[0]
                return self._send(200, json.dumps({"done": done_pairs(root, e) if _valid_evaluator(e) else []}))
            if u.path.startswith(("/img/", "/txt/")):
                folder, name = u.path[1:4], u.path[5:]
                if "/" in name or ".." in name or not (root / folder / name).exists():
                    return self._send(404, "{}")
                return self._send(200, (root / folder / name).read_bytes(), "image/png" if folder == "img" else "text/plain; charset=utf-8")
            return self._send(404, "{}")  # key.json and votes/ are never served

        def do_POST(self):
            if urlparse(self.path).path == "/undo":
                try:
                    n = int(self.headers.get("Content-Length", "0"))
                    e = str(json.loads(self.rfile.read(min(n, 1024))).get("evaluator", ""))
                except (ValueError, json.JSONDecodeError):
                    return self._send(400, "{}")
                return self._send(200, json.dumps({"pair": undo_last_vote(root, e)}))
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
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                v = json.loads(line)
                latest[v["pair"]] = v  # a re-vote replaces the earlier one
        out += [{**v, "evaluator": f.stem} for v in latest.values()]
    return out


# ── round status: a round that has been used to change the engine is development data ──────────

def read_status(round_dir: Path) -> dict:
    f = Path(round_dir) / "STATUS.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"round": Path(round_dir).name, "blind": True, "used_for_calibration": False}


def write_status(round_dir: Path, st: dict) -> None:
    (Path(round_dir) / "STATUS.json").write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def mark_used_for_calibration(round_dir: str | Path, change: str) -> dict:
    """Once a round's votes drive an engine or profile change, it can no longer validate that
    engine: it becomes development data (and says so in every report)."""
    st = read_status(Path(round_dir))
    st.update(blind=False, used_for_calibration=True, status="development data (used for calibration)")
    st.setdefault("calibration_changes", []).append({"change": change, "date": time.strftime("%Y-%m-%d")})
    write_status(Path(round_dir), st)
    return st


def kendall_tau_b(x: list[float], y: list[float]) -> float | None:
    """Kendall's tau-b (handles ties on both sides, e.g. human outcomes in {-1, 0, +1})."""
    n = len(x)
    if n < 3:
        return None
    conc = disc = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx, dy = x[i] - x[j], y[i] - y[j]
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                tx += 1
            elif dy == 0:
                ty += 1
            elif (dx > 0) == (dy > 0):
                conc += 1
            else:
                disc += 1
    den = math.sqrt((conc + disc + tx) * (conc + disc + ty))
    return round((conc - disc) / den, 3) if den else None


def bootstrap_ci(x: list[float], y: list[float], stat=kendall_tau_b, b: int = 2000, seed: int = 11) -> list:
    """Percentile bootstrap 95% interval (resampling pairs); honest width for small n."""
    if len(x) < 5:
        return [None, None]
    rng = random.Random(seed)
    vals = []
    for _ in range(b):
        idx = [rng.randrange(len(x)) for _ in x]
        v = stat([x[i] for i in idx], [y[i] for i in idx])
        if v is not None:
            vals.append(v)
    vals.sort()
    return [round(vals[int(0.025 * len(vals))], 3), round(vals[int(0.975 * len(vals)) - 1], 3)] if vals else [None, None]


def pair_verdicts(votes: list[dict], key: dict, min_gap: float = 1.0) -> list[dict]:
    """Per pair: automatic scores, human majority, and whether the scorer agrees with people.
    human_pref: +1 challenger, −1 baseline, 0 tie/split. agreement: agree | disagree | tie
    (humans tied, or the scorer sees no meaningful difference)."""
    by: dict[str, list[str]] = {}
    for v in votes:
        by.setdefault(v["pair"], []).append(outcome(v, key))
    out = []
    for pid, os_ in sorted(by.items()):
        k = key[pid]
        cw, bw = os_.count("challenger"), os_.count("baseline")
        pref = 1 if cw > bw else -1 if bw > cw else 0
        bs, cs = k.get("baseline_score"), k.get("challenger_score")
        delta = round(cs - bs, 1) if bs is not None and cs is not None else None
        if pref == 0 or delta is None or abs(delta) < min_gap:
            ag = "tie"
        else:
            ag = "agree" if (delta > 0) == (pref > 0) else "disagree"
        out.append({"pair": pid, "archetype": k.get("archetype"), "deck": k.get("deck"), "slide": k.get("slide"), "baseline_score": bs, "challenger_score": cs,
                    "score_delta": delta, "votes": len(os_), "challenger_votes": cw, "baseline_votes": bw, "human_pref": pref, "agreement": ag,
                    "control": k.get("control", False), "images": {"baseline": k.get("baseline"), "challenger": k.get("challenger")}})
    return out


def disagreements_markdown(verdicts: list[dict], round_name: str, strong: float = 10.0) -> str:
    """The cases worth more than the mean: the scorer strongly prefers one slide, people the other."""
    rows = [v for v in verdicts if v["agreement"] == "disagree"]
    rows.sort(key=lambda v: -abs(v["score_delta"] or 0))
    L = [f"# Scorer vs human disagreements — round {round_name}", "",
         f"Pairs where the automatic scorer and the human majority disagree, strongest score gap first (≥ {strong:g} points marked **strong**). "
         "Look for PATTERNS (an archetype, a metric, whitespace, density) — never add an exception for one slide (docs/EVALS.md#calibration).", ""]
    if not rows:
        L.append("_No disagreements (or no votes yet)._")
    else:
        L += ["| pair | archetype | deck / slide | baseline score | challenger score | Δ | humans (challenger–baseline) | |", "|---|---|---|---|---|---|---|---|"]
        for v in rows:
            L.append(f"| {v['pair']} | {v['archetype']} | {v['deck']}/{v['slide']} | {v['baseline_score']} | {v['challenger_score']} | {v['score_delta']:+} | "
                     f"{v['challenger_votes']}–{v['baseline_votes']} | {'**strong**' if abs(v['score_delta']) >= strong else ''} |")
    return "\n".join(L) + "\n"


def outcome(v: dict, key: dict) -> str:
    if v["choice"] == "tie":
        return "tie"
    picked = v["left"] if v["choice"] == "left" else v["right"]
    return "challenger" if picked == key[v["pair"]]["challenger"] else "baseline"


def report(round_dir: str | Path, key_file: str | Path | None = None) -> dict:
    rd = Path(round_dir)
    key = load_key(rd, key_file)
    # one vote per (evaluator, pair): a re-vote replaces the earlier one, so several clicks by the
    # same person never count as several raters
    last: dict[tuple, dict] = {}
    for v in _load_votes(rd):
        if v["pair"] in key:
            last[(v["evaluator"], v["pair"])] = v
    votes = list(last.values())
    ident = [v for v in votes if key[v["pair"]].get("identical_control")]
    votes = [v for v in votes if not key[v["pair"]].get("identical_control")]
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
    res["self_consistency"] = {"repeated_pairs": len(cons), "consistent": sum(cons),
                               "note": "WITHIN-rater: the same person on a side-swapped repeat; not between-rater agreement"}
    if res.get("inter_rater") and "note" not in res["inter_rater"]:
        res["inter_rater"]["note"] = "BETWEEN-rater: different people on the same pair"
    # identical-image controls: evaluator noise, reported, never used to drop a rater
    if any(k.get("identical_control") for k in key.values()):
        ties = [v for v in ident if v["choice"] == "tie"]
        res["identical_controls"] = {"pairs": sum(1 for k in key.values() if k.get("identical_control")), "votes": len(ident),
                                     "tie_rate": round(len(ties) / len(ident), 3) if ident else None, "ci95": list(wilson(len(ties), len(ident))),
                                     "by_rater": {e: round(sum(1 for v in ident if v["evaluator"] == e and v["choice"] == "tie") /
                                                           max(1, sum(1 for v in ident if v["evaluator"] == e)), 3) for e in sorted({v["evaluator"] for v in ident})}}
    # v1.5: every rater on their own, then pooled (above). Pooled votes of one rater are ONE rater.
    res["by_rater"] = {}
    for e in sorted({v["evaluator"] for v in votes}):
        mine = [v for v in main if v["evaluator"] == e]
        d = [v for v in mine if v["choice"] != "tie"]
        rc = [outcome(v, key) == outcome(o, key) for v in votes if v["evaluator"] == e and key[v["pair"]].get("repeat_of")
              for o in mine if o["pair"] == key[v["pair"]]["repeat_of"]]
        res["by_rater"][e] = {**summary(mine), "left_share": round(sum(1 for v in d if v["choice"] == "left") / len(d), 3) if d else None,
                              "self_consistency": {"repeated_pairs": len(rc), "consistent": sum(rc)}}
    # v1.4: per-pair scorer/human agreement, its correlation with the score gap, and its status
    verdicts = pair_verdicts(main, key)
    dec_v = [v for v in verdicts if v["agreement"] != "tie"]
    ag = sum(1 for v in dec_v if v["agreement"] == "agree")
    xs = [v["score_delta"] for v in verdicts if v["score_delta"] is not None]
    ys = [v["human_pref"] for v in verdicts if v["score_delta"] is not None]
    bins = {}
    for lo, hi, name in ((0, 5, "|Δ| < 5"), (5, 15, "5 ≤ |Δ| < 15"), (15, 999, "|Δ| ≥ 15")):
        sel = [v for v in dec_v if lo <= abs(v["score_delta"]) < hi]
        k = sum(1 for v in sel if v["agreement"] == "agree")
        bins[name] = {"pairs": len(sel), "agree": k, "rate": round(k / len(sel), 3) if sel else None, "ci95": list(wilson(k, len(sel)))}
    res["pair_agreement"] = {"pairs_with_votes": len(verdicts), "decisive_pairs": len(dec_v), "agree": ag, "disagree": len(dec_v) - ag,
                             "ties": len(verdicts) - len(dec_v), "rate": round(ag / len(dec_v), 3) if dec_v else None, "ci95": list(wilson(ag, len(dec_v))),
                             "by_score_gap": bins}
    res["score_human_correlation"] = {"method": "Kendall tau-b between score delta (challenger − baseline) and human majority (+1/0/−1), percentile bootstrap 95% CI",
                                      "n": len(xs), "tau_b": kendall_tau_b(xs, ys), "ci95": bootstrap_ci(xs, ys)}
    res["controls"] = summary([v for v in main if key[v["pair"]].get("control")]) if any(k.get("control") for k in key.values()) else None
    res["status"] = read_status(rd)
    res["verdicts"] = verdicts
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
          ]
    pa = r.get("pair_agreement") or {}
    if pa:
        L += ["", f"**When the scorer prefers one slide, do people agree?** {pa['agree']}/{pa['decisive_pairs']} decisive pairs (rate {pa['rate']}, 95% CI {pa['ci95'][0]}–{pa['ci95'][1]}); "
              f"{pa['ties']} ties or no meaningful score gap", "", "| score gap | pairs | agree | rate | 95% CI |", "|---|---|---|---|---|"]
        L += [f"| {k} | {v['pairs']} | {v['agree']} | {v['rate']} | {v['ci95'][0]}–{v['ci95'][1]} |" for k, v in pa["by_score_gap"].items()]
        c = r["score_human_correlation"]
        L += ["", f"**Score gap vs human preference:** Kendall τ-b {c['tau_b']} (95% CI {c['ci95'][0]}–{c['ci95'][1]}, n={c['n']} pairs). "
              "With n this small, read the interval, not the point estimate."]
    st = r.get("status") or {}
    L += ["", f"**Round status:** {'BLIND — independent validation' if st.get('blind', True) else 'DEVELOPMENT DATA — used for calibration, not unbiased validation'}",
          "", f"_Method:_ {r['method']}"]
    return "\n".join(L) + "\n"


def record(r: dict, path: Path | None = None) -> None:
    """Human results go to latest.json under human_reference.rounds.<round>, never into the score."""
    from .evals import LATEST

    path = path or LATEST
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    hr = data.setdefault("human_reference", {})
    hr.pop("status", None)
    hr.pop("round", None)
    hr.pop("pairs", None)
    st = r.get("status") or {}
    hr.setdefault("rounds", {})[r["round"]] = {
        **{k: r.get(k) for k in ("evaluators", "comparisons", "challenger_wins", "baseline_wins", "ties", "challenger_preference", "challenger_preference_ci95",
                                 "ties_as_half", "by_comparison", "score_agreement", "pair_agreement", "score_human_correlation", "inter_rater", "self_consistency",
                                 "left_bias", "method")},
        "blind": st.get("blind", True), "used_for_calibration": st.get("used_for_calibration", False),
        "status": "votes received" if r.get("comparisons") else "awaiting human votes"}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def record_status(round_dir: str | Path, path: Path | None = None) -> None:
    """Record a round that has no votes yet (status only): never invents numbers."""
    from .evals import LATEST

    path = path or LATEST
    rd = Path(round_dir)
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    hr = data.setdefault("human_reference", {})
    for k in ("status", "round", "pairs"):
        hr.pop(k, None)
    st = read_status(rd)
    n = len(json.loads((rd / "pairs.json").read_text(encoding="utf-8"))["pairs"])
    hr.setdefault("rounds", {})[rd.name] = {"pairs": n, "blind": st.get("blind", True), "used_for_calibration": st.get("used_for_calibration", False),
                                            "status": f"{st.get('status', 'awaiting human votes')} — {n} blind pairs built, 0 votes"}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
.txt{white-space:pre-wrap;font:14px/1.45 system-ui,sans-serif;margin:0;padding:12px;max-height:70vh;overflow:auto;text-align:left}
.ctx{border:1px dashed var(--line);border-radius:8px;margin-bottom:12px;max-height:30vh}
progress{width:220px}.done{text-align:center;padding:60px 16px}input{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}
</style></head><body>
<header><strong>Blind comparison</strong><span id="who"></span><span><button id="undo" title="Undo the last vote (U)">↶ Undo last vote / Deshacer último voto</button> <progress id="prog" value="0" max="1"></progress> <span id="count"></span></span></header>
<main id="app"></main>
<script>
const app=document.getElementById('app');let data,order=[],i=0,shownAt=0,ev='',busy=false;
function rng(seed){let h=2166136261;for(const c of seed){h^=c.charCodeAt(0);h=Math.imul(h,16777619)}return()=>{h^=h<<13;h^=h>>>17;h^=h<<5;return((h>>>0)%1e6)/1e6}}
function shuffle(a,r){for(let k=a.length-1;k>0;k--){const j=Math.floor(r()*(k+1));[a[k],a[j]]=[a[j],a[k]]}return a}
function getId(){let e='';try{e=localStorage.getItem('ab-evaluator')||''}catch(_){}return e}
function setId(e){try{localStorage.setItem('ab-evaluator',e)}catch(_){}}
async function start(){data=await (await fetch('pairs.json')).json();ev=getId();if(!ev)return ask();begin()}
function ask(){const sug='r-'+Math.random().toString(36).slice(2,7);app.innerHTML=`<div class="done"><p>${data.meta.instructions}</p>
<p>Your anonymous evaluator id (keep it to resume later):</p><p><input id="eid" value="${sug}" maxlength="40"> <button id="go">Start</button></p></div>`;
document.getElementById('go').onclick=()=>{const v=document.getElementById('eid').value.trim().replace(/[^A-Za-z0-9_-]/g,'');if(!v)return;ev=v;setId(v);begin()}}
async function begin(first){document.getElementById('who').textContent='evaluator '+ev;const r=rng(ev);
const st=await (await fetch('state?evaluator='+encodeURIComponent(ev))).json();const done=new Set(st.done);
order=shuffle(data.pairs.map(p=>({...p,images:(r()<0.5?[...p.images]:[...p.images].reverse())})),r).filter(p=>!done.has(p.id));
if(first){const k=order.findIndex(p=>p.id===first);if(k>0)order.unshift(order.splice(k,1)[0])}i=0;show()}
async function undo(){if(!ev||busy)return;busy=true;try{const r=await fetch('undo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({evaluator:ev})});
const j=await r.json();if(j.pair){await begin(j.pair)}else alert('Nothing to undo / Nada que deshacer')}catch(e){alert('Undo failed (is the server running?)')}busy=false}
document.getElementById('undo').onclick=undo;
function show(){const total=data.pairs.length,left=order.length-i;document.getElementById('prog').max=total;document.getElementById('prog').value=total-left;
document.getElementById('count').textContent=(total-left)+' / '+total;if(i>=order.length){app.innerHTML='<div class="done"><h2>Done — thank you.</h2><p>You can close this page.</p></div>';return}
const p=order[i];const txt=data.meta.kind==='text';
const cell=(n,k)=>txt?`<pre class="txt" data-src="txt/${n}">…</pre>`:`<img src="img/${n}" alt="Slide ${k}">`;
app.innerHTML=`<p class="q">${data.meta.instructions}</p>${txt&&p.context?'<pre class="txt ctx" data-src="txt/'+p.context+'">…</pre>':''}<div class="pair">
<figure data-c="left">${cell(p.images[0],'A')}<figcaption>A <kbd>←</kbd> <kbd>1</kbd></figcaption></figure>
<figure data-c="right">${cell(p.images[1],'B')}<figcaption>B <kbd>→</kbd> <kbd>2</kbd></figcaption></figure></div>
<div class="bar"><button data-c="left">A is better</button><button data-c="tie">Tie <kbd>T</kbd> <kbd>↓</kbd></button><button data-c="right">B is better</button></div>`;
app.querySelectorAll('[data-c]').forEach(el=>el.onclick=()=>vote(el.dataset.c));
app.querySelectorAll('pre[data-src]').forEach(el=>fetch(el.dataset.src).then(r=>r.text()).then(t=>{el.textContent=t}));shownAt=performance.now()}
async function vote(c){if(busy||i>=order.length)return;busy=true;const p=order[i];
const body={evaluator:ev,pair:p.id,left:p.images[0],right:p.images[1],choice:c,ms:Math.round(performance.now()-shownAt)};
try{const r=await fetch('vote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(r.ok){i++;show()}else alert('Vote not saved: '+r.status)}
catch(e){alert('Vote not saved (is the server running?)')}busy=false}
document.addEventListener('keydown',e=>{if(!order.length)return;const k=e.key.toLowerCase();
if(k==='u'){undo();return}if(k==='arrowleft'||k==='1'||k==='a')vote('left');else if(k==='arrowright'||k==='2'||k==='b')vote('right');else if(k==='t'||k==='arrowdown'||k==='0')vote('tie')});
start();
</script></body></html>
"""
