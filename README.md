# FacePilot

**An authorized liveness-testing laboratory for organizations evaluating their own verification systems.**

FacePilot is a local-first desktop research tool for simulating controlled visual conditions and challenge-response movements against systems you own or are explicitly authorized to test.

## Current milestone: Phase 4

FacePilot now includes:

- Dark desktop test console
- Portrait loading, movement, zoom, flip, and reset controls
- Persistent `AUTHORIZED TEST SIMULATION` watermark
- First-launch authorization notice
- Guided test-session lifecycle
- Challenge queue with head-turn, blink, and expression prompts
- Pass/fail annotations with response timing
- Aggregate anomaly score and classification
- JSON, CSV, and styled HTML report exports
- Local duplicate-frame, motion, brightness, and sharpness analysis modules
- Automated tests and cross-platform GitHub Actions
- Windows, macOS, and Linux packaging workflows
- No system-wide virtual-camera registration or third-party camera injection

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

## Eight-phase roadmap

1. Desktop shell and manual preview controls — complete
2. Session, challenge, analysis, and report foundations — complete
3. Authorization, CI, and packaging infrastructure — complete
4. Integrated session and challenge dashboard — complete
5. Live analysis and evidence capture — next
6. Session history, retention, and in-app report management
7. Recording, reliability, settings, and interface polish
8. Release candidate validation and first complete release

## License

A license will be selected before the first public release.
