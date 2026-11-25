# S06. Klasterisasi jendela log

## Apa yang dilakukan
Kami mengelompokkan jendela log berdasarkan embedding, yaitu sidik jari angka dari urutan event. K-Means membagi jendela menjadi sejumlah kelompok; ibarat mengelompokkan daftar belanja yang mirip tanpa diberi nama kelompok sejak awal. Kami membandingkan embedding LSTM dan GRU dengan bag-of-events dan TF-IDF+SVD. HDBSCAN dipakai sebagai pemeriksaan tambahan, sedangkan peta UMAP membantu melihat sampel data.

## Kenapa dilakukan begitu
Nilai k dipilih dari data validasi, bukan data tes, agar pengujian tetap adil. Silhouette mengukur seberapa terpisah kelompok—seperti jarak antarmeja—sedangkan NMI/ARI membandingkan kelompok dengan label alert asli. Silhouette LSTM dan GRU berbeda kurang dari 0,01, jadi aturan spesifikasi memilih yang NMI tag alert validasinya lebih tinggi: LSTM.

## Hasil utama
Sumber angka: `reports/results.json`, `reports/tables/clustering_metrics.csv`, `reports/tables/cluster_profiles.csv`, dan `artifacts/clusters/cluster_profiles.json`.

| Representasi | k | Silhouette tes | NMI tag alert | NMI alert, 3 seed (rata-rata ± SD) | ARI alert, 3 seed (rata-rata ± SD) |
|---|---:|---:|---:|---:|---:|
| Bag-of-events | 24 | 0,8294 | 0,0407 | 0,0326 ± 0,0001 | -0,0740 ± 0,0015 |
| TF-IDF+SVD | 24 | 0,8906 | 0,0364 | 0,0328 ± 0,0002 | -0,0771 ± 0,0002 |
| LSTM | 48 | 0,8468 | 0,0959 | 0,0476 ± 0,0082 | -0,0575 ± 0,0173 |
| GRU | 32 | 0,8104 | 0,0787 | 0,0461 ± 0,0110 | -0,0340 ± 0,0024 |

Semua baris di atas memakai data tes; 8,43% jendela tes ber-alert. LSTM memberi NMI tag tertinggi, tetapi nilainya masih rendah. Silhouette tinggi tidak otomatis berarti kelompok cocok dengan alert. Label acak memberi NMI tag paling tinggi hanya 0,0019. HDBSCAN pada embedding LSTM menemukan 113 kelompok; 21,46% label tes menjadi noise dan 1,44% tidak mendapat proyeksi UMAP.

Contoh profil LSTM:
1. Cluster 34 berisi 43.870 jendela; 11,08% ber-alert. Isinya sering mencakup debugger mati dan error memori yang dapat dikoreksi.
2. Cluster 30 berisi 9.307 jendela tanpa alert; event yang sering muncul adalah `iar <*> dear <*>`, yaitu catatan alamat instruksi dan data.
3. Cluster 38 berisi 518 jendela dan semuanya ber-alert; 512 bertag `KERNTERM`, dengan event utama tentang kernel yang dihentikan.

## Yang harus bisa dijelaskan teman satu tim
1. Cluster seperti meja-meja untuk jendela log dengan sidik jari yang mirip; label alert tidak dipakai saat model dilatih.
2. Kami memilih k memakai validasi. LSTM menang atas GRU pada aturan tie-break, bukan karena melihat hasil tes.
3. Hasil label alert masih lemah: NMI tag LSTM 0,0959 dan ARI alert rata-rata negatif. Purity 92,30% juga harus dibaca bersama porsi non-alert yang besar.

## Pertanyaan dosen yang mungkin
- Mengapa silhouette TF-IDF lebih tinggi tetapi LSTM dipilih? → Silhouette mengukur bentuk kelompok; pilihan representasi deep memakai validasi LSTM-vs-GRU dan tie-break NMI tag alert.
- Apakah kelompok bisa langsung memprediksi alert? → Belum; kesesuaian dengan label alert masih rendah dan clustering dipakai untuk analisis, bukan klaim prediksi.

## Hal yang tidak berjalan sesuai rencana
Data lokal awalnya belum tersedia dan unduhan Zenodo terhalang DNS; setelah BGL.log diberikan, preprocessing lokal menyelesaikan prasyarat S06. Dari sampel peta 30.000 jendela, 29.976 punya koordinat UMAP yang bisa digambar; titik yang tidak terproyeksi dikeluarkan dari gambar.
