from app.api.routers.benchmark import build_tier_benchmark


def test_tier_benchmark_groups_only_configured_scope_levels():
    result = build_tier_benchmark(
        [
            {"scope_level_key": "division", "fused_score": 80},
            {"scope_level_key": "division", "fused_score": 60},
            {"scope_level_key": "team", "fused_score": 40},
            {"scope_level_key": None, "fused_score": 99},
        ]
    )

    assert result == {
        "items": [
            {
                "scope_level_key": "division",
                "average_risk": 70.0,
                "maximum_risk": 80.0,
                "records": 2,
            },
            {
                "scope_level_key": "team",
                "average_risk": 40.0,
                "maximum_risk": 40.0,
                "records": 1,
            },
        ]
    }


def test_tier_benchmark_is_empty_without_scoped_records():
    assert build_tier_benchmark([{"scope_level_key": None, "fused_score": 99}]) == {
        "items": []
    }
