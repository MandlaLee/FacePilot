# FaceWeave Windows LIVE (v0.1.0-alpha)

Native Windows 10/11 x64 webcam-based face swapping application. **Only live camera mode is supported.** No Photo Mode, gallery target editor, recording, cloud or virtual camera installation.

Engine: original SCRFD 10G face detector + ArcFace identity (one-time setup) + 512x512 EMap + InSwapper FP16 through ONNX Runtime. UI: native Qt via PySide6. Webcam: OpenCV DirectShow/Media Foundation, latest-frame-only neural worker, independent raw camera preview, honest swap latency/FPS.

## Files
- `faceweave/engine.py`: portable offline neural engine, reusable sessions.
- `faceweave/app.py`: live-only Windows desktop interface and camera pipeline.
- `requirements.txt`: Python 3.11 runtime libraries.
- `run_faceweave.py`: PyInstaller Windows entry point.
- `.github/workflows/build-windows.yml`: development copy of the Windows Actions workflow; published to a dedicated isolated build branch.
- `WINDOWS-SETUP.md`: consumer installation instructions.
- `tests/`: geometry/unit tests and optional local original-model smoke test.

### Model source
Copy model files into `models/` from the existing Mac FaceWeave Android model pack. No pretrained weight is shipped with the EXE.

### Verification
The CPU neural pipeline was run end-to-end using the original models on the Intel Mac; the actual Windows EXE is built and self-tested on a Windows CI runner separately. Real Windows webcam performance remains to be verified.

### Build
Run `python -m unittest discover -s tests`, `python -m faceweave --self-test`, then the GitHub Windows packaging job. This repository keeps the Windows project entirely separate from the original macOS and Android source trees.
