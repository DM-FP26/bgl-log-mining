# GPU Training Guide (for the teammate with the RTX 5060 laptop)

> **Ringkasan (ID):** Clone repo → install PyTorch versi CUDA → jalankan satu script → `git push` ke branch `gpu-run`. Colok charger, matikan sleep, jangan tutup laptop sampai selesai. Kalau error, kirim screenshot ke Nafi.

Claude Code fills the `<...>` placeholders in S04. Do not send this file with placeholders left in it.

**Repo:** `https://github.com/<owner>/bgl-log-mining` (public to read; you still need write access to push, so accept the organization invite first)
**Your branch:** `gpu-run` (never push to `main`)
**You only need:** Windows, Git, Python 3.12, the NVIDIA driver, about 3 GB of free disk space.

---

## 0. Before you start (one time)

1. Plug in the charger. Set the Legion to **Performance / Turbo** mode (Lenovo Vantage or Fn+Q).
2. Turn off sleep while plugged in. In PowerShell:
   ```powershell
   powercfg /change standby-timeout-ac 0
   powercfg /change monitor-timeout-ac 30
   ```
3. Update the NVIDIA driver (GeForce Experience or nvidia.com). Reboot if asked.
4. Make sure you are a member of the GitHub organization `DM-FP26` with write access (check with Nafi). Without it `git push` is rejected.
5. Install Python 3.12 from python.org if `py -3.12 --version` fails (tick "Add to PATH").

## 1. Get the code

```powershell
git clone https://github.com/<owner>/bgl-log-mining.git
cd bgl-log-mining
git checkout -b gpu-run
```
If Git asks you to log in, use your GitHub account in the browser window that opens.

## 2. Create the environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements-train.txt
```
If activation is blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and retry.

## 3. Check the GPU is really used

```powershell
python scripts/check_gpu.py
```
You must see **`GPU CHECK: PASS`**. If you see FAIL, do not continue: update the driver, reinstall torch with the line from step 2 in a fresh venv, and if it still fails, send Nafi a screenshot.

## 4. Train both models

```powershell
.\scripts\train_all.ps1
```
- It trains an LSTM, then a GRU. The window prints the device name (it must say your NVIDIA GPU) and one line per epoch.
- Keep the laptop plugged in and awake. Do not close the lid.
- If it stops (crash, power cut): run the same command again with `-Resume`:
  ```powershell
  .\scripts\train_all.ps1 -Resume
  ```
  It continues from the last saved epoch.

## 5. Send the results back

```powershell
git add handoff/results
git status
git commit -m "GPU training results: lstm + gru (RTX 5060)"
git push -u origin gpu-run
```
`git status` should only list files under `handoff/results/`. If you see anything else, do not commit; ask Nafi.

Then tell Nafi: "pushed". Done. You can close everything.

## If something goes wrong

| Symptom | Fix |
|---|---|
| `GPU CHECK: FAIL` / "sm_120 is not compatible" | You installed a CPU or old CUDA build of torch. Redo step 2 in a fresh venv with the `cu128` line. Update the NVIDIA driver. |
| `CUDA out of memory` | Run `.\scripts\train_all.ps1 -BatchSize 256` |
| Training is very slow | Charger plugged in? Performance mode on? Other GPU apps (games, browsers with video) closed? |
| `git push` rejected | Make sure you are on branch `gpu-run` (`git branch --show-current`). Never use `--force`. |
| Anything else | Screenshot the whole terminal and send it to Nafi. |
