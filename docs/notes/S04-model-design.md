# S04. Desain model dan paket serah-terima GPU

## Apa yang dilakukan
Kami menulis kode model LSTM dan GRU, kode pelatihan, dan paket untuk teman yang punya GPU: satu skrip (`train_all.ps1`) yang melatih kedua model lalu menyimpan hasilnya untuk di-`git push`. Semua sudah dites di CPU laptop Nafi. Kami juga menghitung tiga pembanding sederhana (baseline) tanpa jaringan saraf.

## Kenapa dilakukan begitu
- **Tugas model: menebak event berikutnya.** Model membaca event 1 sampai 19 dalam satu jendela dan menebak event 2 sampai 20. Analogi: orang yang sudah lama membaca catatan harian mesin bisa menebak kalimat berikutnya. Supaya bisa menebak, model harus "memahami" pola jendela itu, dan pemahaman itulah (keadaan dalam/hidden state) yang kami pakai sebagai sidik jari jendela untuk klastering di S06. Tidak perlu label alert.
- **Bentuk model:** Embedding (event menjadi 64 angka) → LSTM atau GRU (2 lapis, 128 unit) → lapisan keluaran. Sekitar 278 ribu parameter, jadi kecil.
- **Pembanding (baseline)** wajib ada. Kalau model saraf tidak mengalahkannya, laporan harus mengatakannya.

## Hasil utama
Sumber: `reports/results.json` bagian `dl`.
- Baseline top-1 pada data uji, semua jendela / jendela tanpa UNK: tebak event terbanyak **0,0% / 0,0%**; bigram **96,3% / 95,4%**; ulang event sebelumnya **95,8% / 94,3%**.
- Angka top-1 terlihat tinggi karena log sangat repetitif. Karena itu kami menambah ukuran yang lebih ketat: akurasi pada posisi di mana event berikutnya **berbeda** dari sebelumnya. Di situ "ulang event sebelumnya" selalu 0% dan bigram hanya 18,7% (semua) / 30,1% (tanpa UNK).
- Event terbanyak di data latih (`generating core`, 51% target latih) tidak pernah muncul di data validasi dan uji; itu sebabnya baseline "event terbanyak" bernilai 0%.
- Uji coba CPU (1 epoch, LSTM, hanya sebagai pilot, bukan model akhir): satu epoch memakan 153 detik; pada jendela uji tanpa UNK top-1 = 92,6% dan pada posisi berubah = 38,0% (bigram 30,1%). Pada semua jendela uji, loss sangat besar (5,59) karena 60% target adalah UNK yang tidak pernah dilatih.

## Yang harus bisa dijelaskan teman satu tim
1. "Menebak event berikutnya" adalah latihan tanpa label; hasil sampingannya adalah sidik jari tiap jendela.
2. LSTM dan GRU sama-sama jaringan berurutan yang punya "ingatan"; GRU lebih sederhana, LSTM punya satu memori tambahan.
3. Kenapa ada dua versi hasil uji (semua jendela dan tanpa UNK): lihat catatan S02.

## Pertanyaan dosen yang mungkin
- Kenapa baseline sederhana dikalahkan atau tidak? → Lihat `dl` di `results.json` setelah pelatihan GPU (S05); kami melaporkan keduanya apa adanya.
- Kenapa perlu GPU? → Rencananya begitu; pilot CPU menunjukkan model kecil ini sebenarnya bisa dilatih di CPU dalam sekitar 1 sampai 2 jam, jadi GPU mempercepat tetapi bukan syarat mutlak.

## Hal yang tidak berjalan sesuai rencana
- Tes menemukan satu bug: `--resume` dengan jumlah epoch lebih besar tidak melanjutkan latihan. Sudah diperbaiki dan dites.
- Ditambahkan baseline "ulang event sebelumnya" dan ukuran "akurasi pada posisi berubah" yang tidak ada di spesifikasi, karena top-1 biasa menyesatkan pada log yang repetitif.
