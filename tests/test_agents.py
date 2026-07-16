"""Agent roster seed tests."""
from __future__ import annotations

import json

import pytest
from click.testing import CliRunner


@pytest.fixture()
def isolated_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = data_dir / "soloos.sqlite"
    monkeypatch.setenv("SOLOOS_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SOLOOS_DB_PATH", str(db_path))

    import soloos.config as cfg_mod

    cfg_mod.reset_config()
    from soloos.db import migrate

    migrate()
    yield data_dir
    cfg_mod.reset_config()


def test_seed_default_agents_creates_active_core_roster(isolated_env):
    from soloos.agents import AgentsService
    from soloos.db import connect

    seeded = AgentsService().seed_defaults()

    assert seeded == 7
    conn = connect()
    try:
        rows = conn.execute("SELECT * FROM agents ORDER BY id").fetchall()
    finally:
        conn.close()

    assert [row["id"] for row in rows] == [
        "agent:ceo_office",
        "agent:cfo",
        "agent:cto",
        "agent:design",
        "agent:general_counsel",
        "agent:growth",
        "agent:ops",
    ]
    assert {row["status"] for row in rows} == {"active"}
    cto = next(row for row in rows if row["id"] == "agent:cto")
    assert cto["name"] == "Engineering / CTO"
    assert "context7" in json.loads(cto["skills_json"])
    legal = next(row for row in rows if row["id"] == "agent:general_counsel")
    assert json.loads(legal["authority_json"])["can_provide_final_legal_advice"] is False


def test_seed_default_agents_is_idempotent(isolated_env):
    from soloos.agents import AgentsService

    svc = AgentsService()

    assert svc.seed_defaults() == 7
    assert svc.seed_defaults() == 0
    assert len(svc.list_agents()) == 7


def test_agents_cli_seed_and_list(isolated_env):
    from soloos.cli import main

    runner = CliRunner()
    seed_result = runner.invoke(main, ["agents", "seed"])
    list_result = runner.invoke(main, ["agents", "list"])

    assert seed_result.exit_code == 0, seed_result.output
    assert "seeded 7" in seed_result.output
    assert list_result.exit_code == 0, list_result.output
    assert "agent:cto" in list_result.output
    assert "Engineering / CTO" in list_result.output
    assert "agent:growth" in list_result.output
    assert "active" in list_result.output
