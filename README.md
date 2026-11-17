# tts-id-bench

Benchmark model text-to-speech open-weight untuk **bahasa Indonesia**, dijalankan di laptop (Apple M2, 16 GB).

Hasil terbaru ada di [RESULTS.md](RESULTS.md).

## Cara kerja

1. `data/sentences.json` berisi kalimat uji per kategori. Tiap kalimat punya tiga bentuk:
   - `text`: teks apa adanya, mis. `Harganya Rp15.000 per porsi.`
   - `normalized`: ditulis tangan seperti hasil normalizer yang sempurna, mis. `Harganya lima belas ribu rupiah per porsi.`
   - `spoken`: cara baca yang benar, dipakai sebagai kunci jawaban.
2. `synth` menjalankan `text` (varian **raw**) dan `normalized` (varian **normalized**) ke tiap engine.
3. `score` mentranskrip tiap audio kembali ke teks dengan dua juri, lalu membandingkannya dengan `spoken`.

Kategori: `plain`, `number`, `currency`, `datetime`, `unit`, `abbrev`, `homograph`, `codeswitch`, `long`, `informal`.

Selisih antara kolom raw dan normalized menunjukkan seberapa banyak kesalahan model berasal dari teks yang
belum dinormalisasi, bukan dari kemampuan bicaranya.

## Menjalankan

```sh
uv sync
uv run python -m tts_id_bench.synth          # semua engine, atau sebut nama engine
uv run python -m tts_id_bench.score          # tulis out/results.json dan RESULTS.md
```

ZONOS3-Mini dijalankan lewat server MLX miliknya sendiri, yang harus dipasang dulu:

```sh
git clone --recurse-submodules https://github.com/Zyphra/ZONOS3-Mini.git vendor/ZONOS3-Mini
cd vendor/ZONOS3-Mini
uv sync --locked --package zonos3-mlx
uv run --package zonos3-mlx hf download Zyphra/ZONOS3-Mini --include 'gguf/*' --local-dir servers/ggml
```

## Membaca hasilnya

- **CER** (character error rate): persentase huruf yang berbeda antara yang didengar juri dan `spoken`, spasi diabaikan.
  Makin kecil makin baik. Ini mengukur kejelasan dan ketepatan baca, **bukan** kenaturalan suara.
- **RTF** (real-time factor): waktu sintesis dibagi durasi audio. Di bawah 1 berarti lebih cepat dari waktu nyata.

### Kenapa dua juri

Whisper akurat, tapi merapikan apa yang didengarnya: "lima belas ribu rupiah" dan "er pe lima belas ribu" bisa
sama-sama ditulis `Rp15.000`. Dengan Whisper saja, pembacaan singkatan yang benar dan yang salah tidak bisa dibedakan.

Juri kedua adalah model wav2vec2 tingkat karakter tanpa language model. Ejaannya lebih berantakan, tapi ia menulis
bunyi yang benar-benar diucapkan ("er pe", "garis miring").

Skor tiap klip adalah CER terendah dari kedua juri. Pembacaan yang benar diakui kalau salah satu juri mendengarnya;
pembacaan yang salah tetap tertangkap karena tidak ada juri yang mendengar bentuk benarnya. Transkrip kedua juri
disimpan di `out/results.json` supaya bisa diperiksa.

### Keterbatasan

- Mengambil skor terbaik dari dua juri membuat angka sedikit optimistis. Itu berlaku sama untuk semua engine.
- Homograf (`apel`, `teras`, `memerah`) tidak terukur: kedua juri menulis ejaan yang sama untuk pepet dan taling.
  Kategori ini harus dinilai dengan telinga.
- Engine voice cloning (OmniVoice, ZONOS3-Mini) meniru satu klip acuan yang disintesis Piper, karena tidak punya
  suara bawaan bahasa Indonesia. Hasilnya bisa berbeda dengan klip acuan lain.
- Kalimat uji masih sedikit (28) dan disusun satu orang. Tiap kalimat disintesis sekali.

## Menambah engine

Tambah subclass `Engine` di `src/tts_id_bench/engines.py` dan daftarkan di `ENGINES`.
