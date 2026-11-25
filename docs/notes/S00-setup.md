# S00. Setup dan kerangka proyek

## Apa yang dilakukan
Kami menyiapkan "rumah" proyek: folder-folder yang rapi, file konfigurasi (`configs/default.yaml`), paket kode `src/bgllog/`, lingkungan Python 3.12, dan satu tes sederhana yang memastikan semua library bisa dipakai. Setelah itu semuanya diunggah ke GitHub di organisasi `DM-FP26`. Data mentah BGL (743 MB) sudah diunduh ke `data/raw/`, tetapi tidak ikut diunggah.

## Kenapa dilakukan begitu
- Semua angka dan pengaturan ada di satu file config, jadi tidak ada "angka ajaib" yang tersebar di kode. Analogi: seperti satu papan pengumuman untuk semua aturan.
- Repo dibuat publik (keputusan Nafi, tugas kuliah). Blueprint awalnya menyebut privat. Email commit memakai alamat noreply GitHub supaya email asli tidak tampil.
- PyTorch versi CPU dipakai di laptop Nafi karena di sini hanya untuk tes, ekstraksi embedding, dan aplikasi. Pelatihan GPU dilakukan teman di laptop RTX 5060.

## Hasil utama
- 20 tes lulus (`pytest -q`), Python 3.12.16, torch 2.15.0 CPU (lihat `reports/results.json` bagian `env`).
- Daftar versi library tersimpan di `requirements.lock.txt`.

## Yang harus bisa dijelaskan teman satu tim
1. Struktur folder: `src/bgllog/` kode, `scripts/` skrip per tahap, `configs/` pengaturan, `artifacts/` hasil kecil yang boleh diunggah, `reports/` angka, gambar, laporan, `data/` data besar (tidak diunggah).
2. Kenapa data besar tidak masuk GitHub: ukurannya ratusan MB, dan bisa diunduh ulang dari Zenodo.
3. Seed 42 dipakai di mana-mana supaya hasil bisa diulang.

## Pertanyaan dosen yang mungkin
- Apakah hasilnya bisa direproduksi? → Ya, seed tetap 42, versi library dikunci di `requirements.lock.txt`, dan semua skrip membaca config yang sama.

## Hal yang tidak berjalan sesuai rencana
- Repo publik, bukan privat (keputusan Nafi).
- Blueprint ditulis untuk Windows; Nafi memakai Linux, jadi perintah penyiapan memakai `uv` dan venv Linux. Isi kode tetap lintas-platform (`pathlib`).
- Dua tugas tambahan dari dosen (slide dan "rusak sengaja") dicatat di `docs/04-lecturer-additions.md`.
