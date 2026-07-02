from backend.app.main import health


def test_health() -> None:
    response = health()

    assert response["status"] == "ok"
    assert response["service"] == "TPMS-FORGE"
