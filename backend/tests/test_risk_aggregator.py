from __future__ import annotations

import pytest

from app.processing import risk_aggregator


class _Scalars:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return _Scalars(self.rows)

    def all(self):
        return self.rows


@pytest.mark.asyncio
async def test_compute_all_risk_scores_keeps_tenant_tier_groups_separate(monkeypatch):
    class Session:
        def __init__(self):
            self.results = iter(
                [
                    _Result(["global-app"]),
                    _Result([("workspace-a", "branch"), ("workspace-b", "department")]),
                    _Result(["tenant-app"]),
                    _Result(["tenant-app"]),
                ]
            )

        async def execute(self, _statement):
            return next(self.results)

    ceiling_scopes = []
    score_scopes = []

    async def ceiling(_session, tenant_workspace_id=None, tenant_scope_level_key=None):
        ceiling_scopes.append((tenant_workspace_id, tenant_scope_level_key))
        return 100.0

    async def score(
        _session,
        app_name,
        appscan_ceiling=None,
        tenant_workspace_id=None,
        tenant_scope_level_key=None,
    ):
        score_scopes.append((app_name, tenant_workspace_id, tenant_scope_level_key))
        return {
            "app_name": app_name,
            "tenant_workspace_id": tenant_workspace_id,
            "tenant_scope_level_key": tenant_scope_level_key,
        }

    monkeypatch.setattr(risk_aggregator, "estate_appscan_ceiling", ceiling)
    monkeypatch.setattr(risk_aggregator, "compute_risk_for_app", score)

    scores = await risk_aggregator.compute_all_risk_scores(Session())

    assert ceiling_scopes == [
        (None, None),
        ("workspace-a", "branch"),
        ("workspace-b", "department"),
    ]
    assert score_scopes == [
        ("global-app", None, None),
        ("tenant-app", "workspace-a", "branch"),
        ("tenant-app", "workspace-b", "department"),
    ]
    assert len(scores) == 3


@pytest.mark.asyncio
async def test_tenant_risk_query_filters_findings_and_compliance_by_tier():
    class QueryResult:
        def all(self):
            return [("high", "appscan", {})]

        def scalar_one_or_none(self):
            return 82.0

    class Session:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return QueryResult()

    session = Session()
    score = await risk_aggregator.compute_risk_for_app(
        session,
        "tenant-app",
        appscan_ceiling=100.0,
        tenant_workspace_id="workspace-a",
        tenant_scope_level_key="branch",
    )
    compiled = [
        str(statement.compile(compile_kwargs={"literal_binds": True}))
        for statement in session.statements
    ]

    assert score["tenant_workspace_id"] == "workspace-a"
    assert score["tenant_scope_level_key"] == "branch"
    assert all("workspace-a" in statement for statement in compiled)
    assert all("branch" in statement for statement in compiled)
