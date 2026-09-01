from app.main import app


def test_mvp_routes_are_exposed() -> None:
    paths = app.openapi()["paths"]
    expected = {
        "/auth/register",
        "/auth/login",
        "/businesses",
        "/finance/categories",
        "/finance/movements",
        "/finance/summary",
        "/assistant/query",
        "/consents",
        "/privacy/export",
        "/privacy/deletion",
        "/sources",
    }
    assert expected <= set(paths)
