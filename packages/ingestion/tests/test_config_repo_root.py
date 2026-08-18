from __future__ import annotations

from pathlib import Path

from contextiq_ingestion.config import repo_root


def test_repo_root_env_override(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("CONTEXTIQ_REPO_ROOT", str(tmp_path))
    assert repo_root() == tmp_path.resolve()
