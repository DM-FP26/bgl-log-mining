"""Check that PyTorch can really use the GPU. Ends with `GPU CHECK: PASS` or `GPU CHECK: FAIL`."""
import sys

FIX = ("Install the CUDA 12.8+ build in a fresh venv: pip install torch --index-url https://download.pytorch.org/whl/cu128 "
       "and update the NVIDIA driver (see docs/GPU-HANDOFF-FRIEND.md step 2).")


def main() -> int:
    try:
        import torch
    except ImportError:
        print("GPU CHECK: FAIL (torch is not installed). " + FIX)
        return 1
    print("torch version:", torch.__version__)
    print("CUDA version (torch built with):", torch.version.cuda)
    avail = torch.cuda.is_available()
    print("cuda available:", avail)
    if not avail:
        print("GPU CHECK: FAIL (CUDA is not available to PyTorch; this is a CPU-only build or the driver is missing). " + FIX)
        return 1
    print("device name:", torch.cuda.get_device_name(0))
    archs = torch.cuda.get_arch_list()
    print("arch list:", archs)
    print("sm_120 listed:", "sm_120" in archs)
    try:
        x = torch.randn(256, 256, device="cuda")
        print("CUDA tensor op OK, checksum:", float((x @ x).sum().cpu()) != 0.0)
        rnn = torch.nn.LSTM(16, 32, num_layers=2, batch_first=True).cuda()
        out, _ = rnn(torch.randn(8, 10, 16, device="cuda"))
        out.sum().backward()
        torch.cuda.synchronize()
        print("tiny LSTM forward/backward on GPU OK")
    except Exception as exc:  # noqa: BLE001
        print(f"GPU CHECK: FAIL ({type(exc).__name__}: {exc}). " + FIX)
        return 1
    if "sm_120" not in archs:
        print("NOTE: sm_120 (RTX 50-series) is not in the arch list; this works only if your GPU is an older architecture.")
    print("GPU CHECK: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
