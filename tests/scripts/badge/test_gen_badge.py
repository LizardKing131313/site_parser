from __future__ import annotations

import runpy
import sys
import types
from pathlib import Path

from _pytest.capture import CaptureFixture


def _fake_anybadge_module() -> types.ModuleType:
    """
    Лёгкая подмена anybadge, чтобы не тянуть зависимость.
    API: anybadge.Badge(label, value, thresholds).write_badge(path, overwrite=True)
    """

    class FakeBadge:
        def __init__(self, label: str, value: float | str, thresholds: object = None) -> None:
            self.label = label
            self.value = value
            self.thresholds = thresholds or {}

        # noinspection PyUnusedLocal
        def write_badge(self, path: Path, overwrite: bool | None = False) -> None:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"{self.label}:{self.value}", encoding="utf-8")

    module = types.ModuleType("anybadge")
    module.Badge = FakeBadge  # type: ignore[attr-defined]
    return module


def _run_script_in(tmp_path: Path, coverage_xml: str | None) -> None:
    """
    Запускаем scripts/gen_badge.py как скрипт в изолированной директории.
    Опционально создаём coverage.xml с переданным содержимым.
    """
    cwd = Path.cwd()
    try:
        # chdir в песочницу
        __import__("os").chdir(tmp_path)

        # подготовим optional coverage.xml
        if coverage_xml is not None:
            (tmp_path / "coverage.xml").write_text(coverage_xml, encoding="utf-8")

        # подменяем anybadge в sys.modules ДО запуска скрипта
        sys.modules["anybadge"] = _fake_anybadge_module()

        # tests/scripts/test_gen_badge.py  -> parents[3] == {root}
        repo_root = Path(__file__).resolve().parents[3]
        script_path = repo_root / "scripts" / "badge" / "gen_badge.py"
        assert script_path.exists(), f"gen_badge.py not found at {script_path}"

        # выполняем как __main__, чтобы прошёл весь топ-левел код
        runpy.run_path(str(script_path), run_name="__main__")

    finally:
        __import__("os").chdir(cwd)
        # убираем фейковый модуль, чтобы не протекал в другие тесты
        sys.modules.pop("anybadge", None)


def test_gen_badge_success(tmp_path: Path, capsys: CaptureFixture) -> None:
    # валидный xml → берём line-rate * 100 и округляем до 1 знака
    xml = """<?xml version="1.0" ?>
    <coverage branch-rate="0.1" line-rate="0.876" version="6.0.0">
    </coverage>"""
    _run_script_in(tmp_path, xml)

    # проверяем, что бэйдж создан
    badge = tmp_path / "badges" / "coverage.svg"
    assert badge.exists()
    # наш фейковый writer пишет "coverage:<value>"
    assert badge.read_text(encoding="utf-8") == "Coverage:87.6"

    # проверяем stdout
    out = capsys.readouterr().out
    assert "Generated badge at badges/coverage.svg (coverage: 87.6%)" in out


def test_gen_badge_missing_or_broken_xml(tmp_path: Path, capsys: CaptureFixture) -> None:
    # coverage.xml отсутствует → должна сработать ветка except и coverage=0.0
    _run_script_in(tmp_path, coverage_xml=None)

    badge = tmp_path / "badges" / "coverage.svg"
    assert badge.exists()
    assert badge.read_text(encoding="utf-8") == "Coverage:0.0"

    out = capsys.readouterr().out
    assert "Failed to parse coverage.xml" in out
    assert "Generated badge at badges/coverage.svg (coverage: 0.0%)" in out
