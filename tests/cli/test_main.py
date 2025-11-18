import os
from pathlib import Path
from types import SimpleNamespace


from bullet_trade.cli.main import apply_cli_overrides
from bullet_trade.core.globals import Logger


def test_apply_cli_overrides_updates_log_dir(tmp_path, monkeypatch):
    monkeypatch.delenv('LOG_DIR', raising=False)
    bootstrap_dir = tmp_path / "bootstrap"
    monkeypatch.setenv('LOG_DIR', str(bootstrap_dir))
    logger = Logger()

    log_dir = tmp_path / "cli_logs"
    args = SimpleNamespace(log_dir=str(log_dir), runtime_dir=None)

    overrides = apply_cli_overrides(args, logger=logger)

    assert overrides == {}
    assert os.environ['LOG_DIR'] == str(log_dir.resolve())
    handler = logger._file_handler
    assert handler is not None
    assert Path(handler.baseFilename).parent == log_dir.resolve()


def test_apply_cli_overrides_sets_runtime_override(tmp_path, monkeypatch):
    monkeypatch.delenv('RUNTIME_DIR', raising=False)
    runtime_dir = tmp_path / "runtime"
    args = SimpleNamespace(runtime_dir=str(runtime_dir), log_dir=None)

    overrides = apply_cli_overrides(args)

    expected = str(runtime_dir.resolve())
    assert overrides['runtime_dir'] == expected
    assert os.environ['RUNTIME_DIR'] == expected
