# S03. Pattern mining: apa yang muncul sebelum alert?

## Apa yang dilakukan
Kami mencari kombinasi event yang sering muncul tepat sebelum alert, dibandingkan dengan periode tenang. Ada dua jenis temuan: (1) **aturan asosiasi** (FP-Growth): "kalau event A dan B muncul bersama dalam 20 baris, kemungkinan besar alert akan menyusul", dan (2) **pola berurutan** (PrefixSpan): "A lalu B lalu C, dalam urutan itu".
Dua kelompok jendela dibandingkan: **pra-alert** (20 baris tepat sebelum alert pertama sebuah gelombang) dan **kontrol** (20 baris dari waktu yang jauh, minimal 60 menit, dari alert mana pun). Jumlah keduanya sama.

## Kenapa dilakukan begitu
- Gelombang alert dihitung per gelombang, bukan per baris, karena alert datang bergerombol (temuan S01). Kalau per baris, satu badai 152 ribu baris akan mendominasi.
- Jendela pra-alert yang masih memuat alert dari gelombang sebelumnya dibuang (214 dari 820), supaya pola tidak "mencontek" alert itu sendiri.
- Aturan tidak boleh dipercaya begitu saja, jadi dicek empat cara (lihat di bawah).

## Hasil utama
Sumber: `reports/results.json` bagian `patterns`, `reports/tables/*.csv`, gambar `pat_*.png`.
- 820 gelombang alert; 606 jendela pra-alert yang bersih; 606 jendela kontrol; tidak ada yang tumpang tindih.
- 196 itemset sering, **83 aturan**, **293 pola berurutan** pada ambang bawaan (tidak perlu menurunkan ambang).
- Semua aturan teratas berisi pesan **koreksi galat memori** (`ddr errors detected and corrected`, `CE sym`, `bit sparing`, `redundant bit steering`). Alert yang menyusul paling sering bertag `KERNMC` (machine check): 247 dari 606 jendela pra-alert.
- Aturan terbaik: *"MidplaneSwitchController bit sparing" + "total of N ddr error(s) detected and corrected"*: **confidence 100%**, **lift 2,0**, muncul di **8,4%** jendela pra-alert. Artinya: setiap kali kombinasi ini muncul dalam data kami, alert menyusul, tetapi hanya sekitar 1 dari 12 gelombang alert didahului kombinasi ini.
- Pola berurutan terbaik muncul di 11,4% jendela pra-alert dan 0% jendela kontrol.

### Arti support, confidence, lift (dengan contoh nyata)
- **Support** = seberapa sering kombinasi itu muncul di seluruh data (aturan terbaik: 4,2% dari semua jendela).
- **Confidence** = dari jendela yang memuat kombinasi, berapa persen yang berada sebelum alert (100%).
- **Lift** = confidence dibanding peluang dasar. Data kami seimbang (50% pra-alert), jadi lift maksimum 2,0; lift 1 berarti kombinasi itu tidak berhubungan dengan alert.

### Empat pemeriksaan kejujuran
1. **Apakah aturan hanya berisi pesan yang sudah terlihat "fatal"?** Tidak: hanya 10% dari 20 aturan teratas berisi pesan berlevel error, dan 0% berisi event yang berlabel alert. Sebagian besar pesan berlevel INFO (galat yang sudah dikoreksi).
2. **Stabilitas (kontrol diambil ulang dengan seed 43):** 16 dari 20 aturan teratas tetap di 20 teratas, dan 20 dari 20 tetap ditemukan.
3. **Kontrol disamakan bulannya** (karena kontrol acak banyak berasal dari Juni dan Juli): 20 dari 20 aturan teratas tetap lift 2,0. Jadi bukan efek waktu.
4. **Uji waktu (tambang pada 70% awal, uji pada 30% akhir):** median lift 1,77 pada data akhir; 60% dari 20 aturan teratas tetap memiliki lift di atas 1,2. Pola mengikuti waktu sebagian, tidak sempurna.

## Yang harus bisa dijelaskan teman satu tim
1. Cara kerja pra-alert vs kontrol, dan kenapa jumlahnya sama.
2. Kenapa pola memori masuk akal: galat memori yang berulang bisa meningkat menjadi machine check (ini penafsiran kami, bukan hasil pengujian).
3. Keterbatasan: pola presisi tinggi tetapi cakupan rendah; kami tidak bisa memprediksi sebagian besar alert dari pola ini.

## Pertanyaan dosen yang mungkin
- Apakah pola ini bisa dipakai untuk memprediksi? → Sebagian: presisinya tinggi pada contoh yang tercakup, tetapi cakupannya rendah (aturan terbaik hanya 8,4% jendela pra-alert).
- Kenapa lift maksimum 2? → Karena jumlah jendela pra-alert dan kontrol sama (peluang dasar 50%).

## Hal yang tidak berjalan sesuai rencana
- Spesifikasi hanya melarang jendela memuat baris dari gelombang itu sendiri; kami juga membuang jendela yang memuat alert dari gelombang sebelumnya (214 jendela).
- Ukuran itemset dibatasi 4 event; pola berurutan 2 sampai 5 event, dan pengulangan beruntun dilebur (A A A B menjadi A B).
- Dukungan di kontrol dihitung langsung (bukan lewat PrefixSpan kedua), karena itu lebih akurat; rasio pola berurutan dibatasi oleh epsilon 0,001 sehingga angka rasio ~100 berarti "tidak pernah muncul di kontrol".
- Dua pemeriksaan tambahan di luar spesifikasi: kontrol disamakan bulannya, dan uji waktu 70/30.
