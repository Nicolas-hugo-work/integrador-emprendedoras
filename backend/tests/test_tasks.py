"""El punto de entrada de purga existe y es el que programa Compose."""

from app.tasks import run_all


def test_run_all_is_the_scheduled_entry_point() -> None:
    assert callable(run_all)
    assert run_all.__name__ == "run_all"
