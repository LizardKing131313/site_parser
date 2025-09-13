from unittest.mock import MagicMock, patch


@patch("scripts.badge.badge_amend.subprocess.run")
def test_badge_amend(mock_run: MagicMock) -> None:

    def side_effect(cmd: list[str], *_args: object, **_kwargs: object) -> MagicMock:
        if cmd[:3] == ["git", "diff", "--quiet"]:
            m = MagicMock()
            m.returncode = 1
            return m
        if cmd[:2] == ["git", "add"]:
            return MagicMock(returncode=0)
        if cmd[:2] == ["git", "commit"]:
            return MagicMock(returncode=0)
        raise AssertionError(f"Unexpected call: {cmd}")

    mock_run.side_effect = side_effect

    from scripts.badge.badge_amend import main

    assert main() == 0

    mock_run.assert_any_call(["git", "diff", "--quiet", "--", "badges/coverage.svg"])
    mock_run.assert_any_call(["git", "add", "badges/coverage.svg"], check=True)
    mock_run.assert_any_call(["git", "commit", "--amend", "--no-edit"], check=False)


@patch("scripts.badge.badge_amend.subprocess.run")
def test_badge_not_amend(mock_run: MagicMock) -> None:

    def side_effect(cmd: list[str], *_args: object, **_kwargs: object) -> MagicMock:
        if cmd[:3] == ["git", "diff", "--quiet"]:
            m = MagicMock()
            m.returncode = 0
            return m
        raise AssertionError(f"Неожиданный вызов: {cmd}")

    mock_run.side_effect = side_effect

    from scripts.badge.badge_amend import main

    assert main() == 0

    mock_run.assert_any_call(["git", "diff", "--quiet", "--", "badges/coverage.svg"])

    calls = [c.args[0] for c in mock_run.call_args_list]
    assert not any(cmd[:2] == ["git", "add"] for cmd in calls)
    assert not any(cmd[:2] == ["git", "commit"] for cmd in calls)
