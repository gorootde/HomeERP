"""The Alembic migration chain must reproduce the ORM schema (project uses
Alembic for all schema changes – see CLAUDE.md)."""
import pathlib

import pytest
from alembic.command import upgrade
from alembic.config import Config
from sqlalchemy import create_engine, inspect

import backend.models  # noqa: F401
from backend.database import Base

ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture()
def alembic_cfg(tmp_path, monkeypatch):
    db_file = tmp_path / "migrated.db"
    url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg, url


def test_upgrade_head_runs_cleanly(alembic_cfg):
    cfg, url = alembic_cfg
    upgrade(cfg, "head")
    insp = inspect(create_engine(url))
    assert "alembic_version" in insp.get_table_names()


def test_migrated_schema_matches_models(alembic_cfg):
    cfg, url = alembic_cfg
    upgrade(cfg, "head")
    insp = inspect(create_engine(url))

    migrated = {t for t in insp.get_table_names() if t != "alembic_version"}
    expected = set(Base.metadata.tables)
    assert expected <= migrated, f"missing tables: {expected - migrated}"

    for table in expected:
        migrated_cols = {c["name"] for c in insp.get_columns(table)}
        model_cols = {c.name for c in Base.metadata.tables[table].columns}
        assert model_cols <= migrated_cols, (
            f"{table}: columns missing from migrations: {model_cols - migrated_cols}"
        )
