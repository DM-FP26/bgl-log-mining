# S02. Preprocessing: template, jendela, pembagian data

## Apa yang dilakukan
Pesan log yang berupa teks bebas diubah menjadi "jenis kejadian" (event) lewat Drain3, yaitu algoritma yang mengenali bahwa pesan yang hanya beda angka sebenarnya satu jenis. Lalu aliran event dipotong menjadi jendela 20 event (digeser 10 event tiap kali), dan jendela dibagi menurut waktu: 70% paling awal untuk latihan, 15% berikutnya untuk validasi, 15% paling akhir untuk uji. Tidak ada pengacakan.

## Kenapa dilakukan begitu
- Angka, alamat memori (hex), alamat IP, dan lokasi node ditutup (masking) sebelum Drain3 bekerja. Analogi: kalau dua surat hanya beda nomor, kita tetap menganggapnya satu jenis surat. Tanpa masking, jumlah template meledak.
- Pembagian menurut waktu mencegah kebocoran: model tidak boleh "mengintip masa depan". Dua jendela dibuang di antara tiap bagian supaya tidak ada baris yang dipakai bersama.
- Kamus event (vocab) hanya dibuat dari data latih. Event yang tidak dikenal menjadi UNK. Alternatif yang tidak dipilih: memasukkan semua event ke kamus; itu membocorkan informasi dari data uji.

## Hasil utama
Sumber: `reports/results.json` (bagian `preprocessing`), `reports/tables/preprocessing_summary.csv`, `data/processed/templates.csv`.
- 4.747.963 baris menjadi **396 template**; 102 template saja sudah menutupi 99% baris; 21 template hanya muncul sekali.
- **474.795 jendela** (40.514 mengandung alert). Pembagian: latih 332.356, validasi 71.219, uji 71.216, dibuang 4.
- Persentase jendela beralert: latih 9,00%, validasi 6,47%, uji 8,43%.
- Kamus: 241 entri (239 event + PAD + UNK).
- **Temuan penting:** pada data uji, **60,5% token adalah UNK** (latih 0,002%, validasi 2,2%). Hanya 25.356 jendela uji (35,6%) bebas UNK, dan hanya 1.056 di antaranya mengandung alert. Gambar: `prep_unk_ratio.png`.

### Contoh dari awal sampai akhir
Baris mentah pertama: `- 1117838570 2005.06.03 R02-M1-N0-C:J12-U11 2005-06-03-15.42.50.363779 R02-M1-N0-C:J12-U11 RAS KERNEL INFO instruction cache parity error corrected`
→ pesan: `instruction cache parity error corrected` → template yang sama, **event_id 1** (muncul 105.924 kali) → indeks kamus **8** → masuk **jendela 0** (baris 0 sampai 19, bagian latih), dengan isi `[8, 8, 8, 8, ...]`. Jendela 0 tidak mengandung alert, jadi `has_alert=False`.

## Yang harus bisa dijelaskan teman satu tim
1. Template = pesan setelah angka/alamat diganti penanda (`<NUM>`, `<HEX>`, `<IP>`, `<NODE>`).
2. Jendela 20 baris geser 10: dua jendela bertetangga berbagi 10 baris, makanya ada jeda antar bagian data.
3. Kenapa data uji punya 60% UNK: pada 1 sampai 4 Desember 2005 seluruh mesin (65.533 node) mencetak dua jenis laporan penghitung yang tidak pernah muncul sebelumnya (masing-masing 135.092 baris). Ini bukan kesalahan kode; ini pergeseran perilaku sistem dari waktu ke waktu (concept drift).

## Pertanyaan dosen yang mungkin
- Kenapa tidak mengacak data? → Log adalah deret waktu kejadian; mengacak membuat data uji bocor ke latih dan hasil tampak lebih bagus dari kenyataan.
- Kenapa UNK data uji begitu tinggi? → Perilaku mesin berubah; event baru muncul setelah periode latih. Kami melaporkannya apa adanya dan menilai juga pada jendela tanpa UNK.
- Berapa template-nya? → 396, sangat dekat dengan perkiraan literatur (sekitar 320 pada Loghub-2.0).

## Hal yang tidak berjalan sesuai rencana
- Masking pertama (HEX, IP, NODE, PATH, NUM) menghasilkan 1.126 template dengan 630 template satu-kali, karena dump register berisi kata hex tanpa awalan `0x`. Setelah ditambah masker `HEXW`, template turun menjadi 396.
- Drain3 hanya diberi pesan unik (358.360 dari 4,7 juta) agar cepat (sekitar 21 detik); hasil klaster sama karena pesan identik tidak membuat template baru.
- Pergeseran data uji (60% UNK) tidak diperkirakan blueprint; dicatat sebagai keputusan di `docs/PROGRESS.md`.
