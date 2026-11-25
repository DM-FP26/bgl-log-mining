# S09. Report draft, defense pack and final check

## Goal
Produce the Indonesian report draft from real results, finish the defense pack so all five members can answer the lecturer's questions, tidy the repo, and tick the requirements list.

## Depends on
S07, S08.

## Outputs
- `scripts/s09_build_report_data.py`: reads `reports/results.json` and the tables, writes `reports/report_data.md` (a flat list of every number with its meaning, to copy from) and `reports/FIGURES-INDEX.md` (figure file → caption in Indonesian → chapter).
- `reports/laporan-draft.md`: the Indonesian report following `docs/report-skeleton-id.md`, every placeholder `{{...}}` replaced with real numbers and every figure/table referenced by file name.
- `docs/defense-pack-id.md`: the seed in this repo, finalised with real numbers (all `{{...}}` filled), plus one cheat card per team member.
- `docs/mock-viva.md` (Indonesian): 20 hard questions with answers using real numbers.
- `docs/references.md`: re-verified (see below).
- Final tidy: README updated with real results and screenshots, `requirements.lock.txt` current, `.gitignore` check, tag `v1.0`.

## Steps

1. **Report data.** Run the builder script. Fail if any number needed by the skeleton is missing in `results.json`.
2. **Reference check.** For each of the five references in `docs/references.md`, open the DOI link. If a browser/connection is available, confirm title, authors, journal, year, volume/pages. Otherwise mark "not re-verified" and list what the humans must check. Fill in any unknown field (the file says which). **Never invent a bibliographic detail.**
3. **Report draft.** Write chapter by chapter from the skeleton. Use formal Indonesian. Each result paragraph must: state the finding with the number, point to the figure/table by file name, and give a one-sentence interpretation. Cite the five references where the skeleton says so (IEEE or consistent numeric style).
4. **Defense pack.** Replace placeholders; make sure each member's cheat card matches what the report says (same numbers, same wording for definitions). Add the "if you do not know the answer" fallback script.
5. **Mock viva.** Write 20 hard questions (data, preprocessing choices, why LSTM and GRU, why chronological split, how k was chosen, what the clusters mean, what the limits are, what the GPU was used for, what the app does, what the references say). Answers must use real numbers from `results.json`.
6. **Cross-consistency pass.** Compare report vs defense pack vs app vs `results.json`: every shared number must match. List mismatches in `docs/final-check.md` and fix them.
7. **Repo tidy.** Remove dead code and temp files; run `pytest -q`; confirm a fresh clone can run the app; update `README.md`; tag `v1.0`; push.
8. **Final check** (tick in `docs/final-check.md`, copy of the list below).

## Final check list

- [ ] Requirement a: dataset is unstructured (documented in report chapter III.2).
- [ ] Requirement b: sample counts stated (≥ 5000 text samples; actual numbers in report).
- [ ] Requirement c: deep learning used and documented.
- [ ] Requirement d: five references from IEEE/ScienceDirect journals within the last five years, cited in chapter II, listed in the bibliography.
- [ ] Requirement e: EDA, preprocessing, training, testing/evaluation, results analysis all present as report sections.
- [ ] Requirement f1: Streamlit app runs from a fresh clone.
- [ ] Requirement f2: report draft complete (humans will polish and format).
- [ ] Requirement f3: source code in the repo, README with run instructions.
- [ ] Defense pack complete; every member has a cheat card.
- [ ] No number in any document disagrees with `reports/results.json`.
- [ ] `pytest -q` passes; `requirements.lock.txt` current; no large files committed.

## Pitfalls
- Don't write results the experiments did not produce. If a result is weak, the report says so and the defense pack explains why that is still a valid finding.
- Don't copy-paste long passages from papers. Paraphrase and cite.
- Keep the report draft in plain Markdown so the humans can paste it into Word or Docs and format it.

## Note to write
None for S09 beyond `docs/final-check.md`.
