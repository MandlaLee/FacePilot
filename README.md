# FacePilot

**An authorized liveness-testing laboratory for organizations evaluating their own verification systems.**

FacePilot is a local-first desktop research tool for simulating controlled visual conditions and challenge-response movements against systems you own or are explicitly authorized to test.

## Current milestone: Phase 1

- Load a portrait image
- Fit it into a test preview
- Move the frame up, down, left, and right
- Zoom in and out
- Flip horizontally
- Reset the scene
- Persistent `AUTHORIZED TEST SIMULATION` watermark
- No virtual-camera registration or third-party camera injection

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows
pip install -r requirements.txt
python -m app.main
```

## Scope and authorization

FacePilot is intended only for controlled, consent-based evaluation. It must not be used to bypass identity verification, age checks, KYC, access controls, or third-party security systems.

The project deliberately excludes third-party camera injection, emulator camera replacement, stealth features, ADB automation, browser camera spoofing, and integrations that automate real-world KYC flows.

## Roadmap

1. Phase 1 — desktop shell and manual preview controls
2. Phase 2 — local facial landmarks and head-pose measurements
3. Phase 3 — challenge scripting and session recording
4. Phase 4 — replay/anomaly analysis
5. Phase 5 — reports, packaging, tests, and documentation

## License

A license will be selected before the first public release.
