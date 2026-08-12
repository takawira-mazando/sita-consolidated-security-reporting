"""Anonymised provincial peer benchmarking.

SITA's 113 provincial departments sit inside 9 provincial administrations.
A provincial executive may compare its province against peers without
breaching tenant isolation: peers are returned as blinded "Peer Province A/B/…"
aggregates (fused risk only — never raw vulnerability counts, findings or
logs), while the caller's own province is returned unblinded with a
department-level drill-down. A national SITA executive (nationwide role, no
province scope) sees every province fully unblinded.

Identity vs analytics separation: the endpoint only ever reads aggregated
fused scores out of the warehouse; the SQL is still scoped by tenant_filter,
so a provincial caller's query cannot touch rows outside its province.
"""
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import JWTClaims, is_nationwide, require_roles, tenant_filter
from app.db import get_session
from app.models.risk_score import RiskScore
from app.tenant import DEPARTMENTS, PROVINCES, province_for_department

router = APIRouter(tags=["benchmark"])

_PEER_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

_PRIMARY_DRIVER = {
    "appscan": "AppScan: unresolved vulnerabilities",
    "imperva": "Imperva WAF: SQL injection / attack traffic",
    "api": "API exposure: shadow endpoints",
    "compliance": "Compliance penalty: unaddressed controls",
}


def _bucket(score: float) -> str:
    if score >= 70:
        return "critical"
    if score >= 45:
        return "monitored"
    return "safe"


def _build_benchmark(
    records: list[dict],
    caller_provinces: set[str],
    nationwide: bool,
) -> dict:
    """Build the anonymised leaderboard from raw in-scope fused-score rows.

    records: [{department_id, app_name, fused_score, signal_appscan,
               signal_imperva, signal_api_exposure, signal_compliance_penalty}]
    Only provincial-department rows participate; national departments are out
    of scope for the provincial peer benchmark.
    """
    dept_score: dict[str, list[float]] = defaultdict(list)
    dept_apps: dict[str, set[str]] = defaultdict(set)
    dept_signals: dict[str, dict[str, float]] = defaultdict(
        lambda: {"appscan": 0.0, "imperva": 0.0, "api": 0.0, "compliance": 0.0}
    )
    dept_signal_n: dict[str, int] = defaultdict(int)

    for r in records:
        dept = r.get("department_id")
        if not dept:
            continue
        if province_for_department(dept) is None:
            continue
        dept_score[dept].append(float(r["fused_score"]))
        if r.get("app_name"):
            dept_apps[dept].add(r["app_name"])
        for key, rk in (
            ("appscan", "signal_appscan"),
            ("imperva", "signal_imperva"),
            ("api", "signal_api_exposure"),
            ("compliance", "signal_compliance_penalty"),
        ):
            v = r.get(rk)
            if v is not None:
                dept_signals[dept][key] += float(v)
        dept_signal_n[dept] += 1

    # province score = mean of its department averages (each department equal
    # weight so a big portfolio does not swamp a province's peers).
    province_dept: dict[str, list[tuple[str, float]]] = defaultdict(list)
    dept_detail: dict[str, dict] = {}
    for dept, scores in dept_score.items():
        avg = sum(scores) / len(scores)
        province_dept[province_for_department(dept)].append((dept, avg))
        dominant = max(dept_signals[dept], key=lambda k: dept_signals[dept][k] / max(1, dept_signal_n[dept]))
        dept_detail[dept] = {
            "department_id": dept,
            "name": DEPARTMENTS.get(dept, dept),
            "fused_score": round(avg, 1),
            "bucket": _bucket(avg),
            "app_count": len(dept_apps[dept]),
            "primary_driver": _PRIMARY_DRIVER[dominant],
        }

    province_score = {
        p: sum(a for _, a in entries) / len(entries)
        for p, entries in province_dept.items()
    }
    ranked = sorted(province_score.items(), key=lambda kv: (-kv[1], kv[0]))
    national_average = round(sum(v for _, v in ranked) / len(ranked), 1) if ranked else None

    def mine(p: str) -> bool:
        return (not nationwide) and p in caller_provinces

    leaderboard = []
    peer_index = 0
    for rank, (p, score) in enumerate(ranked, start=1):
        is_you = mine(p)
        if nationwide or is_you:
            label = PROVINCES[p]
        else:
            label = f"Peer Province {_PEER_LETTERS[peer_index]}"
            peer_index += 1
        leaderboard.append({
            "rank": rank,
            "label": label,
            "province_id": p if (nationwide or is_you) else None,
            "fused_score": round(score, 1),
            "bucket": _bucket(score),
            "is_you": is_you,
        })

    own = None
    if not nationwide:
        own_province = next((p for p in caller_provinces if p in province_score), None)
        if own_province is not None:
            depts = [
                dept_detail[d]
                for _, entries in province_dept.items()
                if _ == own_province
                for d, _ in entries
            ]
            depts.sort(key=lambda x: -x["fused_score"])
            own = {
                "province_id": own_province,
                "name": PROVINCES[own_province],
                "fused_score": round(province_score[own_province], 1),
                "bucket": _bucket(province_score[own_province]),
                "departments": depts,
            }

    return {
        "viewer": "national" if nationwide else "province",
        "scope": {"provinces": sorted(PROVINCES) if nationwide else sorted(caller_provinces)},
        "national_average": national_average,
        "own": own,
        "leaderboard": leaderboard,
        "note": (
            "Peer provinces are anonymised: only the aggregated fused risk "
            "score is exposed; raw vulnerability counts, findings and logs are "
            "never included."
        ),
    }


@router.get("/benchmark/province")
async def province_benchmark(
    session: AsyncSession = Depends(get_session),
    claims: JWTClaims = Depends(require_roles("dashboard")),
):
    scope = tenant_filter(claims, RiskScore)
    q = select(
        RiskScore.department_id,
        RiskScore.app_name,
        RiskScore.fused_score,
        RiskScore.signal_appscan,
        RiskScore.signal_imperva,
        RiskScore.signal_api_exposure,
        RiskScore.signal_compliance_penalty,
    )
    if scope is not None:
        q = q.where(scope)
    rows = (await session.execute(q)).all()
    records = [
        {
            "department_id": r.department_id,
            "app_name": r.app_name,
            "fused_score": float(r.fused_score),
            "signal_appscan": r.signal_appscan,
            "signal_imperva": r.signal_imperva,
            "signal_api_exposure": r.signal_api_exposure,
            "signal_compliance_penalty": r.signal_compliance_penalty,
        }
        for r in rows
    ]
    nationwide = is_nationwide(claims) and not getattr(claims, "province_ids", None)
    return _build_benchmark(records, set(getattr(claims, "province_ids", None) or []), nationwide)
