# Kerangka Laporan (Bahasa Indonesia)

Panduan untuk Claude Code (S09) dan tim: isi setiap bagian dari file hasil nyata. Placeholder `{{...}}` harus diganti angka dari `reports/results.json`. Jangan menulis angka yang tidak ada di file hasil. Tulis dengan bahasa formal dan ringkas; satu paragraf hasil = temuan + angka + rujukan gambar/tabel + satu kalimat interpretasi.

---

## Halaman Judul

- **Judul:** Klasterisasi dan Penambangan Pola pada Log Sistem Superkomputer Blue Gene/L Menggunakan Embedding LSTM/GRU
- Mata kuliah: Data Mining · Final Project (FP)
- Kelompok: {{nomor kelompok}} · Anggota: {{5 nama + NRP}}
- Dosen pengampu: {{nama dosen}} · Departemen Informatika · Tahun {{tahun}}

## Abstrak (150–250 kata)

Latar singkat → data (BGL, {{n_lines}} baris log mentah) → metode (Drain3, jendela {{window_size}} kejadian, LSTM/GRU, K-Means/HDBSCAN, FP-Growth/PrefixSpan) → hasil utama ({{silhouette terbaik}}, {{NMI terbaik}}, {{jumlah aturan}}) → kesimpulan. Kata kunci: log sistem, klasterisasi, penambangan pola, LSTM, GRU, Blue Gene/L.

---

## Bab I Pendahuluan

| Subbab | Isi yang harus ada | Sumber |
|---|---|---|
| 1.1 Latar Belakang | Log sistem = catatan kejadian mesin; volumenya besar dan tak terstruktur; pentingnya memahami pola kegagalan di sistem HPC; kenapa penambangan data cocok | ref [2], [5] |
| 1.2 Rumusan Masalah | (1) Bagaimana mengubah log mentah menjadi urutan kejadian? (2) Apakah embedding LSTM/GRU menghasilkan klaster yang lebih bermakna dibanding representasi non-deep? (3) Pola kejadian apa yang sering mendahului alert? | n/a |
| 1.3 Tujuan | Jawaban atas tiap rumusan masalah | n/a |
| 1.4 Batasan Masalah | Satu dataset (BGL); tanpa prediksi real-time; label alert hanya untuk validasi; jendela tetap {{window_size}} | `configs/default.yaml` |
| 1.5 Manfaat | Untuk operator sistem, peneliti, dan sebagai pembelajaran data mining | n/a |

## Bab II Tinjauan Pustaka

| Subbab | Isi | Sumber |
|---|---|---|
| 2.1 Log sistem dan analisis log | Definisi, tantangan data tak terstruktur, ringkasan survei deep learning untuk log | [2] |
| 2.2 Penguraian log (log parsing) | Ide template dan Drain (pohon berkedalaman tetap), masking angka/ID | Drain (lihat `docs/references.md` bagian B) |
| 2.3 LSTM dan GRU | Cara kerja singkat, prediksi kejadian berikutnya, embedding dari hidden state | [2], [3] |
| 2.4 Klasterisasi | K-Means, HDBSCAN, UMAP; metrik silhouette, Davies–Bouldin, Calinski–Harabasz, NMI, ARI | [4] |
| 2.5 Penambangan pola | Itemset, support, confidence, lift, FP-Growth, PrefixSpan | n/a |
| 2.6 Penelitian terkait | Tabel perbandingan lima referensi: peneliti, tahun, data, metode, temuan, relevansi dengan penelitian ini | [1]–[5] |

## Bab III Metodologi

| Subbab | Isi | Sumber |
|---|---|---|
| 3.1 Alur penelitian | Diagram alur (EDA → pra-pemrosesan → pola → model → klaster → evaluasi → aplikasi); sebut CRISP-DM/KDD sebagai kerangka | `docs/00-overview.md` |
| 3.2 Dataset | Sumber Loghub/Zenodo, asal BGL (LLNL, 131.072 prosesor), format baris, kolom alert, ukuran {{n_lines}}, mengapa tak terstruktur, mengapa "kotor" (ringkas hasil audit) | `dataset_summary.csv`, `dirty_data_audit.csv` |
| 3.3 Pra-pemrosesan | Pembersihan, Drain3 + masking, jendela {{window_size}}/{{window_step}}, pembagian kronologis {{split}}, vocab dari data latih | `preprocessing_summary.csv`, `prep_window_diagram.png` |
| 3.4 Perancangan model | Embedding → LSTM/GRU → Linear; prediksi kejadian berikutnya; hiperparameter | `configs/train.yaml` |
| 3.5 Skenario pengujian dan metrik | Pembagian latih/validasi/uji; pemilihan k pada validasi; metrik DL dan klaster; baseline; uji sanity label diacak | S06 |
| 3.6 Lingkungan | Perangkat keras (laptop GPU RTX 5060 untuk pelatihan), Python {{versi}}, paket utama dan versinya | `results.json.env` |

## Bab IV Hasil dan Pembahasan

| Subbab | Isi | Gambar/Tabel |
|---|---|---|
| 4.1 EDA | Rasio alert, tag alert, pola harian, sifat "burst", level/komponen/node, panjang pesan, temuan data kotor | `eda_*.png`, `dirty_data_audit.csv` |
| 4.2 Hasil pra-pemrosesan | Jumlah template {{n_templates}}, contoh baris → template → ID, distribusi frekuensi template, jumlah jendela per split | `prep_*.png` |
| 4.3 Penambangan pola | Aturan asosiasi dan pola sekuensial terbaik, contoh yang mudah dibaca, uji kestabilan | `pat_*.png`, `association_rules.csv` |
| 4.4 Pelatihan model DL | Kurva loss, perbandingan LSTM vs GRU vs baseline (top-1 {{...}}), perangkat yang dipakai | `dl_loss_curves.png`, `dl_model_comparison.csv` |
| 4.5 Klasterisasi | Pemilihan k, perbandingan representasi, peta UMAP, profil klaster | `clu_*.png`, `clustering_metrics.csv`, `cluster_profiles.csv` |
| 4.6 Evaluasi | Metrik internal dan eksternal pada data uji, rata-rata ± simpangan baku 3 seed, uji label diacak, sensitivitas ukuran jendela | `eval_*.png`, `final_summary.csv` |
| 4.7 Analisis hasil | Klaster yang berhasil dan yang gagal, tag alert yang mudah/sulit dipisah, contoh nyata, kenapa val dan uji berbeda | catatan S07 |
| 4.8 Implementasi aplikasi | Tangkapan layar tiap halaman Streamlit dan cara memakainya | `app_*.png` |

## Bab V Penutup

- **5.1 Kesimpulan:** jawab tiap rumusan masalah dengan angka.
- **5.2 Keterbatasan:** dari `docs/limitations.md`.
- **5.3 Saran:** tiga saran realistis (misalnya dataset lain, model berbasis Transformer, pemrosesan online).

## Daftar Pustaka

Gaya IEEE bernomor. Isi dari `docs/references.md` (lima jurnal + sitasi dataset). Pastikan semua nomor tersitasi di teks.

## Lampiran

- A. Pembagian tugas anggota (lihat `docs/defense-pack-id.md`)
- B. Tautan repositori dan cara menjalankan aplikasi
- C. Struktur proyek
- D. Tabel dan gambar tambahan
