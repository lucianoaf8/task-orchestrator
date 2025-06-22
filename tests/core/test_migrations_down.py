from types import SimpleNamespace
import importlib

Migration0001InitialSchema = importlib.import_module(
    'orchestrator.core.migrations.0001_initial_schema'
).Migration0001InitialSchema
Migration0002AddConstraints = importlib.import_module(
    'orchestrator.core.migrations.0002_add_constraints'
).Migration0002AddConstraints
Migration0003AddIndexes = importlib.import_module(
    'orchestrator.core.migrations.0003_add_indexes'
).Migration0003AddIndexes


def _check(mig_cls):
    captured = {}
    conn = SimpleNamespace(executescript=lambda sql: captured.setdefault('sql', sql))
    mig = mig_cls(conn)
    mig.down()
    assert 'DROP' in captured['sql'] or 'PRAGMA' in captured['sql']


def test_migrations_down():
    _check(Migration0001InitialSchema)
    _check(Migration0002AddConstraints)
    _check(Migration0003AddIndexes)
