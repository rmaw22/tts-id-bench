"""Run every test sentence through the selected engines.

Usage: uv run python -m tts_id_bench.synth [engine ...]

Each sentence is synthesized twice: "raw" (text as written) and "normalized"
(hand-written spoken form, i.e. what a perfect text normalizer would produce).
Writes out/<engine>/<variant>/<sentence-id>.wav and out/<engine>/synth.json (timings).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import soundfile as sf

from .engines import ENGINES

ROOT = Path(__file__).resolve().parents[2]
SENTENCES = ROOT / "data" / "sentences.json"
OUT = ROOT / "out"
VARIANTS = {"raw": "text", "normalized": "normalized"}


def run(engine_name: str) -> None:
    sentences = json.loads(SENTENCES.read_text())
    engine = ENGINES[engine_name]()

    t0 = time.perf_counter()
    engine.load()
    load_s = time.perf_counter() - t0

    rows = []
    try:
        for variant, field in VARIANTS.items():
            out_dir = OUT / engine_name / variant
            out_dir.mkdir(parents=True, exist_ok=True)
            for s in sentences:
                path = out_dir / f"{s['id']}.wav"
                if variant == "normalized" and s[field] == s["text"]:
                    # Nothing to normalize: reuse the raw audio instead of synthesizing it again.
                    path.write_bytes((OUT / engine_name / "raw" / path.name).read_bytes())
                    continue
                t0 = time.perf_counter()
                engine.synthesize(s[field], path)
                synth_s = time.perf_counter() - t0
                audio_s = sf.info(str(path)).duration
                rows.append({"id": s["id"], "variant": variant, "synth_s": round(synth_s, 3), "audio_s": round(audio_s, 3)})
                print(f"{engine_name} {variant} {s['id']}: {audio_s:.1f}s audio in {synth_s:.2f}s", flush=True)
    finally:
        engine.close()

    # The first call includes warm-up, so it is left out of the speed figure.
    timed = rows[1:]
    summary = {
        "engine": engine_name,
        "license": engine.license,
        "url": engine.url,
        "voice": engine.voice,
        "load_s": round(load_s, 2),
        # Real-time factor: below 1 means faster than real time.
        "rtf": round(sum(r["synth_s"] for r in timed) / sum(r["audio_s"] for r in timed), 3),
        "sentences": rows,
    }
    (OUT / engine_name / "synth.json").write_text(json.dumps(summary, indent=2))
    print(f"{engine_name}: RTF {summary['rtf']}, load {summary['load_s']}s", flush=True)


def main() -> None:
    names = sys.argv[1:] or list(ENGINES)
    for name in names:
        run(name)


if __name__ == "__main__":
    main()
