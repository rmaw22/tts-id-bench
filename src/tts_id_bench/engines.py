"""Engine adapters. Each one turns Indonesian text into a WAV file.

To add a model: subclass Engine, implement load() and synthesize(), register it in ENGINES.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import time
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = ROOT / "models"

# Voice-cloning engines have no Indonesian preset voice, so they all clone this one clip.
# It is synthesized by Piper's Indonesian voice: reproducible, and no real person's recording is needed.
REF_TEXT = "Selamat datang. Hari ini kita akan membahas perkembangan teknologi suara di Indonesia."
REF_WAV = MODELS_DIR / "ref" / "reference.wav"


class Engine:
    name: str
    license: str
    url: str
    voice: str

    def load(self) -> None:
        raise NotImplementedError

    def synthesize(self, text: str, out_path: Path) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class PiperId(Engine):
    name = "piper-id-news-medium"
    license = "MIT voice, GPL-3.0 runtime (voice dataset provenance unclear)"
    url = "https://huggingface.co/rhasspy/piper-voices/tree/main/id/id_ID"
    voice = "id_ID-news_tts-medium"

    def load(self) -> None:
        from piper import PiperVoice
        from piper.download_voices import download_voice

        voice_dir = MODELS_DIR / "piper"
        voice_dir.mkdir(parents=True, exist_ok=True)
        model = voice_dir / f"{self.voice}.onnx"
        if not model.exists():
            download_voice(self.voice, voice_dir)
        self._voice = PiperVoice.load(model)

    def synthesize(self, text: str, out_path: Path) -> None:
        with wave.open(str(out_path), "wb") as f:
            self._voice.synthesize_wav(text, f)


def reference_clip() -> Path:
    if not REF_WAV.exists():
        REF_WAV.parent.mkdir(parents=True, exist_ok=True)
        piper = PiperId()
        piper.load()
        piper.synthesize(REF_TEXT, REF_WAV)
    return REF_WAV


class Supertonic3(Engine):
    name = "supertonic-3"
    license = "OpenRAIL-M"
    url = "https://huggingface.co/Supertone/supertonic-3"
    voice = "preset F1"

    def load(self) -> None:
        from supertonic import TTS

        self._tts = TTS(model="supertonic-3")
        self._style = self._tts.get_voice_style("F1")

    def synthesize(self, text: str, out_path: Path) -> None:
        wav, _ = self._tts.synthesize(text, voice_style=self._style, lang="id")
        self._tts.save_audio(wav, str(out_path))


class OmniVoice(Engine):
    name = "omnivoice"
    license = "CC-BY-NC (weights)"
    url = "https://huggingface.co/k2-fsa/OmniVoice"
    voice = "cloned from Piper reference clip"

    def load(self) -> None:
        import torch
        from omnivoice import OmniVoice as Model

        self._model = Model.from_pretrained("k2-fsa/OmniVoice", device_map="mps", dtype=torch.float16)
        self._prompt = self._model.create_voice_clone_prompt(ref_audio=str(reference_clip()), ref_text=REF_TEXT)

    def synthesize(self, text: str, out_path: Path) -> None:
        import soundfile as sf

        # normalize_text stays off: the benchmark measures what the model does with raw text.
        audio = self._model.generate(text=text, language="id", voice_clone_prompt=self._prompt)
        sf.write(str(out_path), audio[0], 24000)


class Zonos3Mini(Engine):
    """Talks to ZONOS3-Mini's own MLX server, started from vendor/ZONOS3-Mini (see README)."""

    name = "zonos3-mini"
    license = "Apache-2.0"
    url = "https://huggingface.co/Zyphra/ZONOS3-Mini"
    voice = "cloned from Piper reference clip"
    repo = ROOT / "vendor" / "ZONOS3-Mini"
    base = "http://127.0.0.1:1919"

    def load(self) -> None:
        self._ref = base64.b64encode(reference_clip().read_bytes()).decode()
        self._server = subprocess.Popen(
            [str(self.repo / "servers/mlx/scripts/serve.sh")],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        for _ in range(180):
            try:
                urllib.request.urlopen(f"{self.base}/v2/speakers", timeout=2)
                return
            except OSError:
                if self._server.poll() is not None:
                    raise RuntimeError("ZONOS3-Mini server exited during startup")
                time.sleep(1)
        raise RuntimeError("ZONOS3-Mini server did not become ready")

    def synthesize(self, text: str, out_path: Path) -> None:
        import numpy as np
        import soundfile as sf

        body = {"text": text, "language": "id", "stream": False, "seed": 42, "speaker_audio_base64": self._ref}
        req = urllib.request.Request(
            f"{self.base}/v2/generate", json.dumps(body).encode(), {"Content-Type": "application/json"}
        )
        pcm = urllib.request.urlopen(req, timeout=600).read()
        sf.write(str(out_path), np.frombuffer(pcm, dtype="<f4"), 44100)

    def close(self) -> None:
        os.killpg(self._server.pid, 15)


ENGINES: dict[str, type[Engine]] = {e.name: e for e in (PiperId, Supertonic3, OmniVoice, Zonos3Mini)}
