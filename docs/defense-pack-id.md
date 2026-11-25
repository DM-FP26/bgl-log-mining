# Paket Persiapan Presentasi dan Tanya Jawab (Bahasa Indonesia)

Tujuan: setiap anggota bisa menjelaskan bagiannya dengan percaya diri dan menjawab pertanyaan dosen. Claude Code mengganti semua `{{...}}` dengan angka asli di S09. Jangan menghafal angka; pahami alurnya, angka bisa dilihat di laporan.

## Cara memakai paket ini

1. Baca "Cerita proyek dalam 60 detik" sampai bisa menceritakannya tanpa membaca.
2. Baca kartu peran milikmu dan kamus konsep.
3. Latihan bicara 2 menit tentang bagianmu, 3 kali, ke teman satu tim.
4. Latihan tanya jawab: satu orang bertanya dari daftar di bawah, yang lain menjawab bergantian.
5. Jangan menebak jawaban. Pakai naskah "kalau tidak tahu" di bagian akhir.

## Cerita proyek dalam 60 detik

Superkomputer Blue Gene/L mencatat setiap kejadian ke dalam log, jutaan baris teks yang berantakan. Kami mengambil {{n_lines}} baris log itu dari Loghub, lalu mengubah teks tersebut menjadi urutan kejadian: baris yang mirip dikelompokkan menjadi satu "template" ({{n_templates}} template). Urutan kejadian dipotong menjadi jendela berisi {{window_size}} kejadian. Model LSTM dan GRU dilatih menebak kejadian berikutnya, dan "ingatan" internalnya dipakai sebagai sidik jari tiap jendela. Sidik jari itu kami klasterkan dengan K-Means ({{k}} klaster), dibandingkan dengan cara sederhana tanpa deep learning, dan dicek dengan label alert asli yang tidak dipakai saat belajar. Terakhir, kami menambang pola kejadian yang sering muncul sebelum alert, lalu membuat aplikasi Streamlit untuk mencoba semuanya.

## Pembagian peran

| Anggota | Peran saat presentasi | Bagian yang wajib dikuasai |
|---|---|---|
| {{Nafi}} | Ketua, alur end-to-end, tanya jawab teknis | Arsitektur, rancangan model, hasil akhir |
| {{Teman GPU}} | Pelatihan model | LSTM/GRU, kurva loss, GPU dan kenapa dipakai |
| {{Anggota C}} | Data dan pra-pemrosesan | Dataset BGL, EDA, data kotor, Drain3, jendela |
| {{Anggota D}} | Pola dan klaster | FP-Growth, aturan, K-Means/HDBSCAN, profil klaster |
| {{Anggota E}} | Evaluasi dan demo | Metrik, hasil uji, aplikasi Streamlit, kesimpulan dan keterbatasan |

## Kamus konsep (penjelasan sederhana)

| Istilah | Penjelasan sederhana |
|---|---|
| Log | Catatan harian mesin: tiap kejadian satu baris teks |
| BGL (Blue Gene/L) | Superkomputer di LLNL dengan 131.072 prosesor; lognya dipublikasikan untuk penelitian |
| Alert / non-alert | Kolom pertama log: tanda `-` berarti bukan alert, selain itu berarti alert dengan kode kategori |
| Data tak terstruktur | Teks bebas tanpa kolom rapi yang siap dihitung; harus diolah dulu |
| Template (Drain3) | "Cetakan kalimat": angka dan ID diganti penanda sehingga kalimat yang mirip menjadi satu jenis kejadian |
| Jendela (window) | Potongan {{window_size}} kejadian berturut-turut, seperti satu halaman cerita |
| LSTM / GRU | Jaringan saraf yang membaca urutan dan mengingat konteks; GRU versi lebih ringkas dari LSTM |
| Prediksi kejadian berikutnya | Tugas latihan model: diberi awal urutan, tebak kejadian selanjutnya; tidak butuh label |
| Embedding | Deretan angka yang menjadi "sidik jari" satu jendela |
| Klasterisasi | Mengelompokkan jendela yang sidik jarinya mirip, tanpa diberi tahu kelompok yang benar |
| K-Means / HDBSCAN | K-Means membagi ke k kelompok; HDBSCAN mencari kelompok padat dan boleh menandai sebagian data sebagai noise |
| UMAP | Cara menggambar data berdimensi tinggi menjadi peta 2D untuk dilihat |
| Silhouette | Seberapa jelas klaster terpisah (−1 sampai 1, makin besar makin baik) |
| Davies–Bouldin | Seberapa tumpang tindih klaster (makin kecil makin baik) |
| NMI / ARI | Kecocokan klaster dengan label alert asli (0 ≈ kebetulan, 1 = sama persis) |
| Support / confidence / lift | Seberapa sering pola muncul / seberapa sering pola diikuti alert / seberapa jauh lebih sering dari kebetulan (lift > 1 berarti lebih sering dari kebetulan) |
| Class imbalance | Alert jarang dibanding non-alert, sehingga akurasi saja menyesatkan |
| Split kronologis | Data latih dari waktu paling awal, uji dari waktu paling akhir, supaya tidak ada "bocoran" dari masa depan |
| Baseline | Cara sederhana sebagai pembanding; kalau model canggih tidak lebih baik, itu juga temuan |

## Kartu peran

Setiap kartu: 5 hal yang harus diingat dan 3 tanya-jawab. Claude Code melengkapi angka di S09.

### Kartu: Ketua ({{Nafi}})
- Alur: EDA → pra-pemrosesan → pola → model → klaster → evaluasi → aplikasi
- Pilihan utama dan alasannya: BGL, tanpa supervised, LSTM/GRU, split kronologis
- Hasil utama: {{hasil utama}}
- Satu keterbatasan terbesar: {{keterbatasan utama}}
- Kolaborasi: pelatihan GPU di laptop teman, sisanya di CPU
- **T:** Kenapa tidak klasifikasi saja karena ada label? **J:** Tujuan kami memahami struktur dan pola tanpa bergantung pada label; label dipakai untuk memeriksa apakah klaster bermakna.
- **T:** Apa kontribusi utama proyek? **J:** Alur lengkap dari log mentah ke klaster dan pola yang bisa dijelaskan, dengan perbandingan jujur terhadap baseline, plus aplikasi demo.
- **T:** Kalau diulang, apa yang diubah? **J:** {{saran perbaikan}}

### Kartu: Pelatihan model ({{Teman GPU}})
- Tugas model: menebak kejadian berikutnya di setiap posisi jendela
- Arsitektur: Embedding → LSTM/GRU ({{layers}} lapis, hidden {{hidden}}) → Linear
- Pelatihan memakai data latih, early stopping pada validasi, uji hanya sekali di akhir
- Hasil: top-1 LSTM {{lstm_top1}}, GRU {{gru_top1}}, baseline bigram {{bigram_top1}}
- GPU dipakai karena data latih {{n_train_windows}} jendela dan banyak epoch; hasilnya dikirim lewat GitHub
- **T:** Kenapa LSTM dan GRU? **J:** Keduanya standar untuk urutan; GRU lebih ringan, jadi kami bandingkan; hasilnya {{perbandingan}}.
- **T:** Apa itu early stopping? **J:** Pelatihan dihentikan saat loss validasi tidak membaik lagi supaya model tidak menghafal data latih.
- **T:** Apakah model melihat label alert saat belajar? **J:** Tidak. Hanya urutan kejadian.

### Kartu: Data dan pra-pemrosesan ({{Anggota C}})
- Dataset: BGL dari Loghub, {{n_lines}} baris, {{alert_ratio}} berupa alert
- Kenapa tak terstruktur dan kotor: {{contoh dari audit data kotor}}
- Drain3: baris mirip → satu template; {{n_templates}} template
- Jendela {{window_size}} dengan geser {{window_step}}; split kronologis {{split}}
- Vocab hanya dari data latih supaya tidak bocor
- **T:** Apa yang dibersihkan? **J:** {{ringkasan pembersihan}}; baris rusak dicatat, tidak dibuang diam-diam.
- **T:** Kenapa window 20? **J:** Cukup panjang untuk konteks dan cukup pendek untuk tetap spesifik; ukuran lain diuji di analisis sensitivitas ({{hasil sensitivitas}}).
- **T:** Kenapa tidak diacak saat membagi data? **J:** Urutan waktu penting; acak membuat jendela yang tumpang tindih bocor ke data uji.

### Kartu: Pola dan klaster ({{Anggota D}})
- Pola: FP-Growth dan aturan asosiasi pada jendela sebelum alert vs jendela kontrol; PrefixSpan untuk urutan
- Klaster: K-Means (utama), HDBSCAN (eksploratif), k dipilih di validasi
- Pembanding: bag-of-events dan TF-IDF+SVD
- Contoh pola nyata: {{contoh aturan}}
- Contoh klaster nyata: {{contoh klaster}}
- **T:** Bagaimana memilih k? **J:** Menjalankan beberapa k, memilih silhouette tertinggi di data validasi; k terpilih {{k}}.
- **T:** Apa arti lift {{lift contoh}}? **J:** Pola itu {{lift contoh}} kali lebih sering terjadi sebelum alert daripada kebetulan.
- **T:** Apakah klasternya bermakna? **J:** NMI {{nmi}} terhadap tag alert, jauh di atas label acak ({{nmi_acak}}); klaster {{x}} berisi {{keterangan}}.

### Kartu: Evaluasi dan demo ({{Anggota E}})
- Metrik internal (silhouette, DB, CH) dan eksternal (NMI, ARI) pada data uji
- Rata-rata ± simpangan baku dari 3 seed: {{ringkasan seed}}
- Uji sanity: label diacak menghasilkan NMI ≈ {{nmi_acak}}
- Demo Streamlit: urutan klik di `docs/notes/S08-app.md`
- Keterbatasan: {{daftar singkat dari limitations}}
- **T:** Kenapa hasil validasi dan uji berbeda? **J:** {{penjelasan dari S07}}
- **T:** Apakah model ini bisa memprediksi kegagalan? **J:** Tidak; kami menunjukkan hubungan antara klaster/pola dan alert, bukan prediksi.
- **T:** Apa yang ditampilkan aplikasi? **J:** Ringkasan, EDA, peta klaster, pola, dan halaman coba model yang menugaskan klaster untuk log yang ditempel.

## Tanya jawab umum (tambahan)

1. **Kenapa dataset ini?** Log mentah tak terstruktur, jutaan baris, berasal dari sistem nyata, dipublikasikan dengan paper (Loghub, IEEE ISSRE 2023), bukan dari Kaggle.
2. **Kenapa deep learning di tugas klasterisasi?** Untuk mendapatkan representasi urutan yang menangkap konteks; hasilnya dibandingkan dengan baseline: {{ringkasan perbandingan}}.
3. **Apa peran lima referensi?** Survei log dengan deep learning [2], masalah imbalance [1], alternatif BERT [3], pendekatan klaster [4], pendekatan tanpa label [5].
4. **Apa itu data kotor di sini?** {{contoh dari audit}}.
5. **Kenapa HDBSCAN tidak dipakai di aplikasi?** Tidak punya fungsi prediksi untuk data baru; dipakai sebagai analisis eksploratif.
6. **Apa risiko kebocoran data (leakage)?** Kami membagi secara kronologis dengan jeda, vocab dari data latih, scaler dan klaster di-fit hanya di data latih.
7. **Kenapa alert tidak dijadikan target?** Karena alert jarang dan berkelompok dalam waktu; kami fokus pada struktur dan pola, lalu memakai alert untuk validasi.
8. **Berapa lama pelatihan, perangkat apa?** {{lama}} di laptop RTX 5060; semuanya dapat diulang dengan seed 42.
9. **Apa kelemahan terbesar?** {{keterbatasan utama}}.
10. **Apa langkah lanjutan?** {{saran}}.

## Kalau tidak tahu jawabannya

Jangan menebak. Ucapkan: "Untuk detail bagian itu, saya ingin memastikan jawabannya benar. Secara garis besar yang kami lakukan adalah {{satu kalimat tentang bagian itu}}, dan detailnya ada di laporan Bab {{bab}}. Boleh saya teruskan ke rekan saya yang mengerjakannya?"

## Tips cepat

- Mulai jawaban dengan satu kalimat inti, baru detail.
- Gunakan analogi dari kamus konsep.
- Kalau ditanya angka, sebut angkanya dan arti sederhananya.
- Jangan membela hasil yang lemah; jelaskan kenapa temuan itu tetap valid.
