from app.core.session import SessionStatus, SignalResult, TestSession


def test_session_lifecycle_and_score() -> None:
    session = TestSession("portrait.png")
    session.start()
    session.add_signal(SignalResult("duplicate_frames", 0.8, "Repeated frames detected"))
    session.add_signal(SignalResult("low_motion", 0.6, "Motion below expected range"))
    session.complete()

    assert session.status is SessionStatus.COMPLETED
    assert session.risk_score() == 0.7
    assert session.classification() == "review recommended"
    assert session.to_dict()["status"] == "completed"


def test_signal_score_is_clamped() -> None:
    assert SignalResult("high", 9, "").score == 1.0
    assert SignalResult("low", -4, "").score == 0.0
