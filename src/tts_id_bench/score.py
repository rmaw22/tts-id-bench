"""Score synthesized audio by transcribing it back to text (ASR round trip).

Usage: uv run python -m tts_id_bench.score

Two judges listen to every clip:

- Whisper: accurate, but tidies what it hears ("lima belas ribu rupiah" and
  "er pe lima belas ribu" can both come back as "Rp15.000"), so on its own it
  cannot tell a correct reading of an abbreviation from a wrong one.
- A character-level wav2vec2 model without a language model: noisier spelling,
  but it writes what was actually said ("er pe", "garis miring").

A clip's error is the lower of the two judges' character error rates against the
expected spoken form, spaces ignored. A correct reading is credited if either
judge hears it; a wrong reading is caught because neither does.

This measures intelligibility and correct verbalization, not naturalness.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import jiwer
import numpy as np
import soundfile as sf
import torch
from faster_whisper import WhisperModel
from num2words import num2words
from scipy.signal import resample_poly
from transformers import AutoModelForCTC, Wav2Vec2Processor

from .synth import VARIANTS

ROOT = Path(__file__).resolve().parents[2]
SENTENCES = ROOT / "data" / "sentences.json"
OUT = ROOT / "out"

WHISPER_MODEL = "large-v3-turbo"
# Nudges Whisper to spell numbers out instead of writing digits.
WHISPER_PROMPT = "Harganya lima belas ribu rupiah, dua puluh lima persen, tahun dua ribu dua puluh enam."
LITERAL_MODEL = "indonesian-nlp/wav2vec2-indonesian-javanese-sundanese"

# The literal model writes a spelled-out letter as e.g. "rletter"; turn it into the letter's Indonesian name.
LETTER_NAMES = dict(
    zip(
        "abcdefghijklmnopqrstuvwxyz",
        "a be ce de e ef ge ha i je ka el em en o pe ki er es te u ve we eks ye zet".split(),
    )
)


def load_16k(path: Path) -> np.ndarray:
    """Mono float32 at 16 kHz, the format both judges expect."""
    audio, rate = sf.read(str(path), dtype="float32", always_2d=True)
    return resample_poly(audio.mean(axis=1), 16000, rate).astype(np.float32)


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\b([a-z])letter\b", lambda m: f" {LETTER_NAMES[m.group(1)]} ", text)
    # Whisper still writes some digits; verbalize plain integers so they compare fairly.
    text = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", text)
    text = re.sub(r"\d+", lambda m: f" {num2words(int(m.group()), lang='id')} ", text)
    text = text.replace("%", " persen ").replace("-", " ")
    text = re.sub(r"[^a-z\s]", " ", text)
    return " ".join(text.split())


def cer(expected: str, heard: str) -> float:
    """Character error rate with spaces ignored ("wi fi" and "wifi" are the same reading)."""
    return jiwer.cer(expected.replace(" ", ""), heard.replace(" ", "") or "-")


class Judges:
    def __init__(self) -> None:
        self.whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        self.processor = Wav2Vec2Processor.from_pretrained(LITERAL_MODEL)
        self.literal = AutoModelForCTC.from_pretrained(LITERAL_MODEL).eval()

    def hear(self, audio: np.ndarray) -> dict[str, str]:
        segments, _ = self.whisper.transcribe(audio, language="id", initial_prompt=WHISPER_PROMPT, beam_size=5)
        with torch.no_grad():
            logits = self.literal(**self.processor(audio, sampling_rate=16000, return_tensors="pt")).logits
        return {
            "whisper": normalize(" ".join(seg.text.strip() for seg in segments)),
            "literal": normalize(self.processor.batch_decode(logits.argmax(-1))[0]),
        }


def main() -> None:
    sentences = json.loads(SENTENCES.read_text())
    judges = Judges()

    results = []
    for engine_dir in sorted(p for p in OUT.iterdir() if (p / "synth.json").exists()):
        synth = json.loads((engine_dir / "synth.json").read_text())
        rows = []
        for variant in VARIANTS:
            for s in sentences:
                expected = normalize(s["spoken"])
                heard = judges.hear(load_16k(engine_dir / variant / f"{s['id']}.wav"))
                errors = {judge: round(cer(expected, text), 3) for judge, text in heard.items()}
                rows.append(
                    {
                        "id": s["id"],
                        "category": s["category"],
                        "variant": variant,
                        "expected": expected,
                        "heard": heard,
                        "cer_by_judge": errors,
                        "cer": min(errors.values()),
                    }
                )
                print(f"{synth['engine']} {variant} {s['id']}: CER {rows[-1]['cer']}", flush=True)
        results.append({**{k: synth[k] for k in ("engine", "license", "url", "voice", "rtf")}, "sentences": rows})

    (OUT / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    (ROOT / "RESULTS.md").write_text(render(results))


def mean_cer(rows: list[dict]) -> float:
    """Length-weighted, so a long sentence counts for more than a short one."""
    chars = [len(r["expected"].replace(" ", "")) for r in rows]
    return sum(r["cer"] * n for r, n in zip(rows, chars)) / sum(chars)


def render(results: list[dict]) -> str:
    categories = list(dict.fromkeys(r["category"] for r in results[0]["sentences"]))

    def pick(r: dict, variant: str, category: str | None = None) -> list[dict]:
        return [x for x in r["sentences"] if x["variant"] == variant and category in (None, x["category"])]

    lines = [
        "# Results",
        "",
        f"Judges: faster-whisper `{WHISPER_MODEL}` and `{LITERAL_MODEL}` (no language model).",
        "Figures are character error rates in percent, lower is better. See README for how to read them.",
        "",
        "## Overall: raw text versus hand-normalized text",
        "",
        "| Engine | License | Voice | RTF | Raw | Normalized |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda r: mean_cer(pick(r, "raw"))):
        raw, norm = mean_cer(pick(r, "raw")), mean_cer(pick(r, "normalized"))
        lines.append(
            f"| [{r['engine']}]({r['url']}) | {r['license']} | {r['voice']} | {r['rtf']} | {raw:.1%} | {norm:.1%} |"
        )
    for variant in VARIANTS:
        lines += [
            "",
            f"## By category: {variant} text",
            "",
            "| Engine | " + " | ".join(categories) + " |",
            "|---|" + "---|" * len(categories),
        ]
        for r in sorted(results, key=lambda r: mean_cer(pick(r, "raw"))):
            cells = " | ".join(f"{mean_cer(pick(r, variant, c)):.1%}" for c in categories)
            lines.append(f"| {r['engine']} | {cells} |")
    return "\n".join(lines).replace("%", "") + "\n"


if __name__ == "__main__":
    main()
