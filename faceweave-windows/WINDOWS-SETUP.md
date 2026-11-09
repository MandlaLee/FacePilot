# FaceWeave Windows — LIVE-only face swapping

**Windows 10/11 x64 · version 0.1.0-live-alpha.**

FaceWeave has one feature: **face swapping on your webcam**. There is no target photo picker, exported image, video editor, virtual-camera registration, cloud processing or background recording.

## Install and launch

1. Download the `FaceWeave-Windows-LIVE-EXE` GitHub Actions artifact and extract the entire ZIP.
2. Put the four **original face models** in the folder named `models` beside `FaceWeave.exe`:
   - `det_10g.onnx`
   - `w600k_r50.onnx`
   - `inswapper_128_fp16.onnx`
   - `inswapper_emap.npy`
3. Transfer these model files from your Mac's `Desktop/FaceWeave Android/Models to Transfer/` folder. They are **not bundled** with the EXE because their original third-party licences may restrict redistribution.
4. Double-click `FaceWeave.exe`. Select the model folder if you stored models elsewhere.
5. Choose **SOURCE FACE** (the person whose face should appear in your camera feed).
6. Tick the consent confirmation for the source and camera participants.
7. Select **START LIVE SWAP**. The raw camera preview continues independently; the left panel displays each new processed frame as it finishes.
8. Press **STOP LIVE SWAP** or close the application to release the camera.

## Performance and privacy

- The raw webcam can operate at approximately 30 FPS while the **neural-swapped output may be far slower**. The user interface explicitly shows inference duration and actual swapped FPS.
- ONNX Runtime uses Windows CPU execution by default. This is a correctness-first build and may be too slow for smooth live video. GPU acceleration and lower-latency models require actual Windows hardware benchmarks.
- Source photos, camera frames and model files remain on the device. No online account, upload, model download or cloud connection is implemented.
- The app never saves snapshots or records video. It does not inject a virtual camera into other programs.

## Testing status

- The Python ONNX neural engine was tested on the owner's Intel Mac with the original models and a sample target frame; the output differed from the original. That **does not prove Windows webcam performance**.
- The GitHub Actions build compiles on Windows and runs both unit tests and a packaged EXE `--self-test`, but cannot test a real Windows webcam in CI.
- First-run webcam access, actual live swapping, GUI, Windows security warnings and performance must be tested on a physical Windows PC.

## Build from source

Use Python 3.11 x64 on Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -p "test_*.py" -v
python -m faceweave --self-test
python -m PyInstaller --noconfirm --clean --onefile --windowed --name FaceWeave --collect-binaries onnxruntime --collect-data onnxruntime --hidden-import onnxruntime.capi.onnxruntime_pybind11_state run_faceweave.py
```

The executable is `dist/FaceWeave.exe`; copy the model folder next to it.

**Legal caution:** use only with consent and check licensing for the third-party InsightFace/InSwapper weights before any commercial release.
