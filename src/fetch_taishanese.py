#!/usr/bin/env python3
"""Fetch en.wiktionary pages carrying a Taishanese reading (|c-t=) in {{zh-pron}}.

Resumable + append-only: rerun any number of times, coverage accumulates.
Paced for the anonymous API rate limit.  Writes TSV: title<TAB>c-t values
"""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sources", "taishanese_ct.tsv")
UA = "taishanese-g2p-build/1.0 (local research; contact: andrew)"
API = "https://en.wiktionary.org/w/api.php"
SEARCH = 'insource:/\\|c-t=/'
CT_RE = re.compile(r"\|\s*c-t\s*=\s*([^|\n}]+)")
ZHP = re.compile(r"\{\{zh-pron(.{0,4000}?)\}\}", re.S)
PACE = 1.3          # seconds between API calls


def call(params, tries=10):
    url = API + "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                wait = min(2 ** i + 1, 60)
                print(f"  [{e.code}] backoff {wait}s", flush=True)
                time.sleep(wait)
                continue
            raise
        except Exception as e:
            print("  err", e, flush=True)
            time.sleep(3 + i)
    return None


def load():
    seen = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            for line in f:
                if "\t" in line:
                    t, v = line.rstrip("\n").split("\t", 1)
                    seen[t] = v.split("|")
    return seen


def save(seen):
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for t in sorted(seen):
            f.write(t + "\t" + "|".join(seen[t]) + "\n")
    os.replace(tmp, OUT)


def extract(txt):
    vals = []
    for blk in ZHP.finditer(txt):
        m = CT_RE.search(blk.group(1))
        if m:
            vals.append(m.group(1).strip())
    if not vals:
        m = CT_RE.search(txt)
        if m:
            vals.append(m.group(1).strip())
    return vals


def main():
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 600.0   # seconds
    t0 = time.time()
    seen = load()
    start_n = len(seen)
    print(f"resuming from {start_n} entries", flush=True)

    cont = {}
    batch = 0
    while time.time() - t0 < budget:
        params = {
            "action": "query", "format": "json", "formatversion": 2,
            "generator": "search", "gsrsearch": SEARCH, "gsrnamespace": 0,
            "gsrlimit": 50, "prop": "revisions", "rvprop": "content",
            "rvslots": "main",
        }
        params.update(cont)
        d = call(params)
        if not d:
            print("stopping: request failed after retries", flush=True)
            break
        for p in d.get("query", {}).get("pages", []):
            try:
                txt = p["revisions"][0]["slots"]["main"]["content"]
            except Exception:
                continue
            v = extract(txt)
            if v:
                seen[p["title"]] = v
        batch += 1
        if batch % 5 == 0:
            save(seen)
            print(f"batch {batch}: total={len(seen)} (+{len(seen)-start_n}) "
                  f"elapsed={time.time()-t0:.0f}s", flush=True)
        cont = d.get("continue") or {}
        if not cont:
            print("reached end of search results", flush=True)
            break
        time.sleep(PACE)

    save(seen)
    print(f"WROTE {len(seen)} entries (+{len(seen)-start_n} this run) -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
