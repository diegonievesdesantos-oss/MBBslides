"""Stand-alone blind A/B voting server (Python standard library only).

Shipped inside a voting package (`cpe human package`) next to pairs.json, index.html and img/.
Evaluators run it without the MBBslides repository. It serves the page and images, and appends
votes to votes/<evaluator>.jsonl. It never needs, reads or serves a key.

    python3 vote_server.py [--port 8765]
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent


def _ok_id(e):
    return 1 <= len(e) <= 40 and all(ch.isalnum() or ch in "-_" for ch in e)


def _pairs():
    return {p["id"]: p for p in json.loads((ROOT / "pairs.json").read_text(encoding="utf-8"))["pairs"]}


def _done(e):
    f = ROOT / "votes" / f"{e}.jsonl"
    return [json.loads(x)["pair"] for x in f.read_text(encoding="utf-8").splitlines() if x.strip()] if f.exists() else []


def _record(v):
    pairs = _pairs()
    e = str(v.get("evaluator", ""))
    if not _ok_id(e) or v.get("pair") not in pairs or v.get("choice") not in ("left", "right", "tie"):
        raise ValueError("invalid vote")
    if sorted([v.get("left"), v.get("right")]) != sorted(pairs[v["pair"]]["images"]):
        raise ValueError("images do not match the pair")
    rec = {k: v.get(k) for k in ("pair", "left", "right", "choice", "ms")}
    rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (ROOT / "votes").mkdir(exist_ok=True)
    with open(ROOT / "votes" / f"{e}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
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
            return self._send(200, (ROOT / "index.html").read_text(encoding="utf-8"), "text/html; charset=utf-8")
        if u.path == "/pairs.json":
            return self._send(200, (ROOT / "pairs.json").read_text(encoding="utf-8"))
        if u.path == "/state":
            e = (parse_qs(u.query).get("evaluator") or [""])[0]
            return self._send(200, json.dumps({"done": _done(e) if _ok_id(e) else []}))
        if u.path.startswith(("/img/", "/txt/")):
            folder, name = u.path[1:4], u.path[5:]
            f = ROOT / folder / name
            if "/" in name or ".." in name or not f.exists():
                return self._send(404, "{}")
            return self._send(200, f.read_bytes(), "image/png" if folder == "img" else "text/plain; charset=utf-8")
        return self._send(404, "{}")

    def do_POST(self):
        if urlparse(self.path).path != "/vote":
            return self._send(404, "{}")
        try:
            n = int(self.headers.get("Content-Length", "0"))
            _record(json.loads(self.rfile.read(min(n, 4096))))
        except (ValueError, json.JSONDecodeError) as e:
            return self._send(400, json.dumps({"error": str(e)}))
        return self._send(200, "{}")


def main():
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8765
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"Voting server: open http://127.0.0.1:{port}   (close this window when you are done)", flush=True)
    print(f"Votes are saved in {ROOT / 'votes'}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
