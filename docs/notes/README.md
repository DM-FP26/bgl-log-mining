# Notes format (written by Claude Code, in simple Indonesian)

One note per stage: `docs/notes/Sxx-<name>.md`. The audience is the five teammates, two of whom did not write any code. Keep each note to one page.

Required structure:

```markdown
# Sxx. <judul>

## Apa yang dilakukan
(3–5 kalimat, bahasa sederhana, tanpa istilah yang belum dijelaskan)

## Kenapa dilakukan begitu
(alasan pilihan utama; sebut alternatif yang tidak dipilih dan kenapa)

## Hasil utama
(angka asli dari reports/results.json atau tabel di reports/tables; sebutkan nama file)

## Yang harus bisa dijelaskan teman satu tim
1. ...
2. ...
3. ...

## Pertanyaan dosen yang mungkin
- Pertanyaan → jawaban satu kalimat

## Hal yang tidak berjalan sesuai rencana
(penyimpangan dari spesifikasi dan alasannya; kosongkan jika tidak ada)
```

Rules:
- Numbers must come from result files. Never type a number you did not read from a file.
- Use an everyday analogy for each new concept (see the concept dictionary in `docs/defense-pack-id.md`).
- If you changed a default in the spec, say so under "Hal yang tidak berjalan sesuai rencana" and add a row to the decisions log in `docs/PROGRESS.md`.
