# S05. Hasil training GPU

## Apa yang dilakukan
Model LSTM dan GRU dilatih untuk menebak event berikutnya dari urutan log. Training memakai PyTorch CUDA di laptop RTX 5060. Setelah selesai, bobot model dipindahkan ke folder artefak dan setiap jendela diubah menjadi embedding, yaitu ringkasan angka dari urutannya. Ibarat sidik jari, embedding ini akan dipakai untuk mengelompokkan pola pada S06.

## Kenapa dilakukan begitu
Data latih, validasi, dan tes tetap mengikuti pembagian waktu S02; tes hanya dipakai untuk evaluasi akhir. Training dihentikan ketika hasil validasi tidak membaik, agar model tidak terus belajar dari data yang sama. Nilai pada semua jendela dan subset tanpa token UNK dilaporkan terpisah karena banyak event tes yang belum dikenal saat training.

## Hasil utama
Sumber angka: `handoff/results/{lstm,gru}/metrics.json`, `history.csv`, `env.json`, `artifacts/embeddings/`, dan `reports/tables/dl_model_comparison.csv`.

| Model | Epoch terbaik | Top-1 tes semua jendela | Top-1 tes tanpa UNK | Top-1 bigram |
|---|---:|---:|---:|---:|
| LSTM | 9 | 95,77% | 96,03% | 96,27% |
| GRU | 7 | 96,03% | 96,02% | 96,27% |

Kedua model belum mengalahkan baseline bigram pada semua jendela, tetapi melampauinya pada subset tanpa UNK. Skor saat event berubah adalah 31,72% untuk LSTM dan 32,72% untuk GRU. GPU terdeteksi sebagai NVIDIA GeForce RTX 5060 Laptop GPU; pemeriksaan CUDA dan `sm_120` lulus. Embedding berukuran 128 nilai tersedia untuk train (332.356), validasi (71.219), dan tes (71.216).

## Yang harus bisa dijelaskan teman satu tim
1. Prediksi event berikutnya melatih model tanpa label alert; hidden state menjadi ringkasan urutan.
2. Skor semua jendela dipengaruhi event UNK, jadi hasil subset tanpa UNK ditampilkan terpisah.
3. Bigram masih sedikit lebih kuat pada top-1 semua jendela; hasil ini dilaporkan apa adanya.

## Pertanyaan dosen yang mungkin
- Mengapa hasil semua jendela berbeda dari subset tanpa UNK? → Banyak event baru muncul setelah periode training dan tidak ada di kosakata yang dipelajari model.
- Apakah model deep learning mengalahkan baseline? → Belum pada top-1 semua jendela; pada subset tanpa UNK, kedua model melampaui bigram.

## Hal yang tidak berjalan sesuai rencana
Panduan awal belum memasang paket lokal proyek dan pandas. Keduanya ditambahkan ke langkah setup agar script training dapat diimpor pada instalasi baru. Training pertama sempat berakhir dengan kode non-zero setelah metrik tersimpan; pengulangan dengan `-Resume` selesai dengan kode sukses. S06 tertahan karena unduhan Zenodo gagal akibat DNS; detail pertanyaan ada di `docs/BLOCKERS.md`.
