# 04. Lecturer additions (received 2026-11-25)

These two items came after the blueprint was written. They are **requirements**, not nice-to-haves. Read this file at the start of every session (CLAUDE.md points here).

## A. Presentation slides (new stage S10)

- **Requirement:** the team must present the project with slides.
- **When:** after the Streamlit app (S08) is done. Do not spend time on slides before that.
- **How:** Nafi will send a `.pptx` template. Claude Code fills and modifies that template (use the `pptx` skill). Do not invent a new design.
- **Content source:** the slides use only numbers and figures from `reports/results.json`, `reports/figures/` and `reports/tables/` (same "never fabricate numbers" rule as everything else). App screenshots come from S08.
- **Language:** ask Nafi when the template arrives (the report and defense pack are Indonesian, so the default is Indonesian).
- **Open:** slide count and time limit are unknown. Ask Nafi when the template arrives.

## B. "Break it on purpose" demos (new stage S11)

- **Requirement:** each of the five students (Nafi included) must **deliberately break the project in one way** and demonstrate what happens. Example from the lecturer: "what if we skip a phase?"
- **Scenarios:** not decided yet. Nafi will tell Claude Code which scenario each student takes. **Do not pick scenarios on your own.**
- **When to decide:** after the Streamlit app works (S08). One thing is needed now, though: keep the code easy to break cleanly (see "Design hooks" below).

### Design hooks to keep in mind while building S01 to S08

1. Every phase has switches in `configs/default.yaml` (for example masking on or off, chronological or random split, window size, which representation is clustered). Do not bury a choice in code where a config flag would do.
2. A broken run must **never overwrite the main results**. When S11 starts, broken runs write to `reports/ablations/<scenario-name>/` and have their own mini `results.json`. The main `reports/results.json` stays untouched.
3. Every script already supports `--sample`. A broken run on `--sample` should finish in minutes on CPU so a student can run it live.
4. Anything that needs retraining the LSTM/GRU needs the GPU teammate. Scenarios that only touch preprocessing, splitting, clustering or pattern mining run on CPU. Tell Nafi which is which when scenarios are chosen, so the GPU teammate is booked early.

### Candidate scenarios (suggestions only, for Nafi to choose from)

| Break | What should go wrong | Needs GPU? |
|---|---|---|
| Skip the number/hex/IP masking before Drain3 | Template count explodes (tens of thousands instead of a few hundred to low thousands); the vocabulary is useless | No |
| Random split instead of chronological | Overlapping windows leak across train and test; scores look better than they are | No (affects training data, so full effect needs retraining) |
| Skip the dirty-data audit (S01) | Empty-message lines, rows with a missing node, and FATAL lines that are not alerts go unnoticed | No |
| Use the `FATAL` level as the "alert" label | About 59% of FATAL lines are not alerts (506,260 of 854,658 FATAL lines, measured on the raw file), so the label is wrong | No |
| Skip the deep model, cluster bag-of-events directly | Shows what the LSTM/GRU embedding adds (or does not add) | No |
| Tiny window size (for example 2) or huge window size | Windows lose meaning, or alerts are smeared across windows | Yes for a full retrain, no for pattern mining |
| Choose k for K-Means without any selection | Clusters look random; NMI/ARI collapse | No |
| Train for 1 epoch, or shuffle the sequence order | Embeddings carry no sequence information | Yes |

Pick whichever five fit the team's skills and the lecturer's expectation. Each demo should end with: what was broken, what we expected, what we saw (with numbers), and what it teaches.
