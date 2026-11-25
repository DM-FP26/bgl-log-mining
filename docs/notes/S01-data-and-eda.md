# S01. Data dan EDA

## Apa yang dilakukan
Kami mengunduh log BGL (4.747.963 baris), memecah setiap baris menjadi kolom (label, waktu, node, komponen, level, pesan), lalu mengukur seberapa "kotor" datanya. Hasilnya 8 gambar EDA dan 5 tabel. Tahap ini hanya mengukur; tidak ada data yang dibersihkan atau dibuang.

## Kenapa dilakukan begitu
- Baris yang gagal dibaca tidak dibuang diam-diam, tetapi ditandai `parse_ok=False`. Ternyata jumlahnya 0.
- Format baris ada variasi (kolom node kedua kadang hilang, pesan kadang kosong), jadi parser dibuat toleran dan variasi itu dihitung sebagai temuan.
- Alternatif yang tidak dipilih: membersihkan sekarang. Keputusan pembersihan ditunda ke S02 supaya semua bisa dipertanggungjawabkan.

## Hasil utama
Sumber: `reports/results.json`, `reports/tables/dataset_summary.csv`, `reports/tables/dirty_data_audit.csv`.
- 4.747.963 baris; 348.460 baris alert (7,34%); persis sama dengan angka publikasi.
- Rentang waktu: 3 Juni 2005 sampai 4 Januari 2006. 41 tag alert berbeda; 20 di antaranya kurang dari 100 baris.
- Struktur rapi: 0 baris rusak, 0 waktu mundur, 0 selisih `ts` vs `time_full`.
- Tapi isinya berantakan: 34.470 baris pesan kosong, 116.659 baris tanpa node yang jelas (`-`, `NULL`, `UNKNOWN_LOCATION`), 8 baris berisi karakter korup, 1.005 jeda waktu lebih dari 1 jam, hanya 4 baris duplikat persis.
- Gambar: `eda_alert_ratio.png`, `eda_alert_tags.png`, `eda_lines_per_day.png`, `eda_alert_bursts.png`, `eda_level_by_alert.png`, `eda_component.png`, `eda_top_nodes.png`, `eda_msg_length.png`.

### Tiga temuan paling mengejutkan
1. **Level FATAL bukan label alert.** Dari 855.501 baris FATAL, 507.103 (59,3%) bukan alert. Jadi level tidak boleh dipakai sebagai label.
2. **Alert sangat menggerombol.** 99,6% alert ada di gelombang berisi minimal 10 baris (820 gelombang, terbesar 152.183 baris). Satu node, `R30-M0-N9-C:J16-U01`, menghasilkan 43,7% semua alert, dan 64,6% alert terjadi pada Juni 2005. Akibatnya pembagian data berdasarkan waktu (S02) akan membuat proporsi alert di train dan test berbeda; ini harus dilaporkan jujur.
3. **Rapi secara struktur, kotor secara isi.** Tidak ada baris rusak, tetapi ada pesan kosong, node hilang, dan baris korup. "Kotor" di sini berarti isi pesan, bukan format kolom.

## Yang harus bisa dijelaskan teman satu tim
1. Satu baris log terdiri dari header terstruktur ditambah pesan teks bebas; yang kita analisis adalah pesannya.
2. Kenapa alert dihitung per baris dan per gerombol: alert datang berkelompok, bukan tersebar merata.
3. Kenapa FATAL tidak sama dengan alert.

## Pertanyaan dosen yang mungkin
- Apakah data ini benar-benar tidak terstruktur? → Headernya terstruktur, tetapi pesan (isi utama, 1 sampai 93 kata, median 26 karakter) berupa teks bebas yang strukturnya baru kita bentuk di S02.
- Berapa banyak data yang kotor? → Lihat `dirty_data_audit.csv`: 34.470 pesan kosong (0,73%), 116.659 node hilang (2,46%), dan 59,3% baris FATAL yang bukan alert.

## Hal yang tidak berjalan sesuai rencana
- Spesifikasi memperkirakan format kolom yang tetap; kenyataannya kolom node kedua kadang hilang (324 baris) dan beberapa baris korup (8 baris) menghasilkan nilai kolom `type`/`component`/`level` yang aneh. Parser menanganinya; baris korup dicatat di `reports/tables/field_values.csv` dan dibahas di S02.
- Mode `--sample` memakai offset 3.000.000 (10% alert) supaya irisan berisi alert.
