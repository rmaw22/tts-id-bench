# Results

Judges: faster-whisper `large-v3-turbo` and `indonesian-nlp/wav2vec2-indonesian-javanese-sundanese` (no language model).
Figures are character error rates in percent, lower is better. See README for how to read them.

## Overall: raw text versus hand-normalized text

| Engine | License | Voice | RTF | Raw | Normalized |
|---|---|---|---|---|---|
| [zonos3-mini](https://huggingface.co/Zyphra/ZONOS3-Mini) | Apache-2.0 | cloned from Piper reference clip | 0.16 | 1.8 | 0.6 |
| [piper-id-news-medium](https://huggingface.co/rhasspy/piper-voices/tree/main/id/id_ID) | MIT (voice dataset provenance unclear) | id_ID-news_tts-medium | 0.025 | 7.4 | 0.8 |
| [supertonic-3](https://huggingface.co/Supertone/supertonic-3) | OpenRAIL-M | preset F1 | 0.232 | 8.2 | 0.5 |
| [omnivoice](https://huggingface.co/k2-fsa/OmniVoice) | CC-BY-NC (weights) | cloned from Piper reference clip | 3.093 | 14.8 | 0.3 |

## By category: raw text

| Engine | plain | number | currency | datetime | unit | abbrev | homograph | codeswitch | long | informal |
|---|---|---|---|---|---|---|---|---|---|---|
| zonos3-mini | 0.0 | 0.6 | 0.0 | 7.3 | 1.9 | 4.4 | 0.0 | 0.0 | 0.3 | 9.4 |
| piper-id-news-medium | 0.0 | 1.1 | 19.4 | 19.2 | 16.8 | 18.2 | 0.0 | 2.7 | 0.3 | 9.4 |
| supertonic-3 | 0.0 | 7.4 | 27.1 | 13.9 | 14.8 | 21.2 | 0.9 | 0.7 | 0.0 | 10.6 |
| omnivoice | 0.0 | 29.9 | 40.3 | 43.7 | 22.6 | 19.7 | 0.0 | 0.0 | 0.0 | 8.2 |

## By category: normalized text

| Engine | plain | number | currency | datetime | unit | abbrev | homograph | codeswitch | long | informal |
|---|---|---|---|---|---|---|---|---|---|---|
| zonos3-mini | 0.0 | 0.6 | 0.0 | 0.7 | 1.9 | 2.9 | 0.0 | 0.0 | 0.3 | 0.0 |
| piper-id-news-medium | 0.0 | 1.1 | 1.4 | 0.0 | 1.3 | 1.5 | 0.0 | 2.7 | 0.3 | 0.0 |
| supertonic-3 | 0.0 | 1.7 | 0.7 | 0.0 | 0.0 | 1.5 | 0.9 | 0.7 | 0.0 | 1.2 |
| omnivoice | 0.0 | 0.6 | 0.0 | 0.0 | 0.6 | 1.5 | 0.0 | 0.0 | 0.0 | 1.2 |
