from app.core.session import SessionStatus, SignalResult, TestSession


def test_session_lifecycle_and_score() -> None:
    session = TestSession("portrait.png")
    session.start()
    session.add_signal(SignalResult("challenge:blink", 0.8, "Challenge failed"))
    session.add_signal(SignalResult("frame:duplicate", 0.6, "Repeated frame heuristic"))
    session.add_signal(SignalResult("frame:quality", 1.0, "Poor image quality"))
    session.complete()

    assert session.status is SessionStatus.COMPLETED
    assert session.risk_score() == 0.7
    assert session.classification() == "review recommended"
    assert session.risk_breakdown() == {
        "challenge_outcomes": 0.8,
        "frame_analysis": 0.6,
        "overall": 0.7,
    }
    assert session.to_dict()["status"] == "completed"
    assert session.to_dict()["risk_breakdown"] == {
        "challenge_outcomes": 0.8,
        "frame_analysis": 0.6,
        "overall": 0.7,
    }


def test_challenge_motion_is_part_of_automated_risk() -> None:
    session = TestSession("portrait.png")
    session.start()
    session.add_signal(SignalResult("challenge:look_left", 0.0, "Challenge passed"))
    session.add_signal(SignalResult("frame:duplicate", 0.0, "No duplicate detected"))
    session.add_signal(SignalResult("frame:challenge_motion", 1.0, "No motion observed"))
    session.complete()

    assert session.risk_score() == 1 / 3
    assert session.risk_breakdown()["frame_analysis"] == 0.5


def test_quality_signal_does_not_change_anomaly_score() -> None:
    session = TestSession("portrait.png")
    session.start()
    session.add_signal(SignalResult("challenge:smile", 0.0, "Challenge passed"))
    session.add_signal(SignalResult("frame:duplicate", 0.0, "No duplicate detected"))
    session.add_signal(SignalResult("frame:quality", 1.0, "Quality concern"))
    session.complete()

    assert session.risk_score() == 0.0
    assert session.risk_breakdown()["overall"] == 0.0


def test_signal_score_is_clamped() -> None:
    assert SignalResult("high", 9, "").score == 1.0
    assert SignalResult("low", -4, "").score == 0.0
