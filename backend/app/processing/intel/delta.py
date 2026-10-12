"""Risk-delta decomposition. No model.

Backs stage (a) of AVP-8: why did the score move?

``warehouse.risk_scores`` already stores the four fused signals separately on
every row (``models/risk_score.py:25-28``). The contribution of each to a change
in the headline score is arithmetic over data the platform has been writing
every five minutes for as long as the risk aggregator has run. Nothing here
interprets anything. The reason it is worth building is that no dashboard in the
product decomposes a risk movement, and it is the first question an executive
asks when the trend line moves.

Stage (b) of AVP-8 — the *external* reason a finding moved the appscan signal —
is not here. It depends on campaign enrichment (AVP-3) and on a ``cve_id`` column
the warehouse does not yet have. Recorded in ``capability.REGISTRY`` as
``THREAT_ENRICHMENT`` so the gap is visible rather than assumed away.

Column names are taken from the model rather than restated, and read from
``risk_scores`` rather than recomputed. Recomputing a bucket here would risk the
three-way divergence between ``risk_engine.risk_bucket`` (safe <= 30) and the
``< 45`` copies in ``exports_ag`` and ``benchmark`` — P0-5 in the master plan.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.risk_score import RiskScore

#: The four fused signals, read from the model. Order is display order.
SIGNALS = (
    ("appscan", RiskScore.signal_appscan),
    ("imperva", RiskScore.signal_imperva),
    ("api_exposure", RiskScore.signal_api_exposure),
    ("compliance_penalty", RiskScore.signal_compliance_penalty),
)


@dataclass(frozen=True)
class Contribution:
    signal: str
    delta: float
    share_pct: float

    def as_dict(self) -> dict:
        return {"signal": self.signal, "delta": self.delta, "share_pct": self.share_pct}


def decompose(delta_total: float, deltas: dict[str, float]) -> list[Contribution]:
    """Split a score movement across the four signals.

    ``share_pct`` is a share of the summed **absolute** movement, so the four
    shares always total 100 and a signal that moved down is reported as a
    negative delta with a positive share. Using the net change as the
    denominator instead would let shares exceed 100 or turn negative whenever
    two signals offset, which reads as a measurement error rather than a real
    finding.

    ``delta_total`` is accepted and returned by the caller for display, but the
    denominator is deliberately not the net change. A signal may legitimately
    exceed the net movement when others pull the other way — that is the whole
    point of the decomposition.
    """
    clean = {
        name: float(deltas.get(name) or 0.0) for name, _col in SIGNALS
    }
    magnitude = sum(abs(v) for v in clean.values())
    out = []
    for name in clean:
        d = round(clean[name], 1)
        share = round(abs(d) / magnitude * 100, 1) if magnitude else 0.0
        out.append(Contribution(signal=name, delta=d, share_pct=share))
    out.sort(key=lambda c: abs(c.delta), reverse=True)
    return out


def _series(rows) -> tuple:
    """First and last row of a date-ordered series."""
    if len(rows) < 2:
        return None, None
    return rows[0], rows[-1]


async def app_delta(
    session: AsyncSession, claims, app_name: str, window_days: int = 14
) -> dict:
    """Decompose one application's fused-score movement over ``window_days``."""
    from app.api.auth import tenant_filter

    scope = tenant_filter(claims, RiskScore)
    stmt = (
        select(RiskScore)
        .where(RiskScore.app_name == app_name, RiskScore.score_date.isnot(None))
        .order_by(RiskScore.score_date)
    )
    if scope is not None:
        stmt = stmt.where(scope)
    rows = (await session.execute(stmt)).all()

    # Restrict to the window in Python: the row count per app is small and this
    # keeps the query index-friendly on score_date without a second round trip.
    cutoff = date.today() - timedelta(days=window_days)
    rows = [r for r in rows if r.score_date and r.score_date >= cutoff]

    first, last = _series(rows)
    if first is None or last is None:
        return {
            "avp": "AVP-8",
            "stage": "a",
            "requires_model": False,
            "app_name": app_name,
            "sufficient_history": False,
            "samples": len(rows),
            "note": (
                "At least two scored days are required in the window to decompose "
                "a movement. The risk aggregator runs every "
                f"{5} minutes but only materialises one row per app per day."
            ),
        }

    delta_total = round(float(last.fused_score) - float(first.fused_score), 1)
    deltas = {
        name: float(getattr(last, col.key) or 0) - float(getattr(first, col.key) or 0)
        for name, col in SIGNALS
    }
    contributions = decompose(delta_total, deltas)

    return {
        "avp": "AVP-8",
        "stage": "a",
        "requires_model": False,
        "scope_class": "tenant_scoped",
        "app_name": app_name,
        "sufficient_history": True,
        "samples": len(rows),
        "window_days": window_days,
        "from": {"score_date": first.score_date.isoformat(), "fused_score": float(first.fused_score),
                 "bucket": first.bucket},
        "to": {"score_date": last.score_date.isoformat(), "fused_score": float(last.fused_score),
               "bucket": last.bucket},
        "delta_fused_score": delta_total,
        "contributions": [c.as_dict() for c in contributions],
        "dominant_signal": contributions[0].signal if contributions else None,
        "external_cause": {
            "available": False,
            "reason": (
                "Stage (b) requires campaign enrichment (AVP-3) and a findings.cve_id "
                "column. Neither is present; the connector receives cve and the "
                "warehouse discards it."
            ),
        },
    }


async def largest_movers(session: AsyncSession, claims, window_days: int = 14, limit: int = 25) -> dict:
    """The applications whose fused score moved most in the window (AVP-8a).

    Ordering only. The per-application decomposition is
    :func:`app_delta`; doing it for every app in the estate in one request would
    be a scan nobody asked for.
    """
    from app.api.auth import tenant_filter

    scope = tenant_filter(claims, RiskScore)
    cutoff = date.today() - timedelta(days=window_days)
    stmt = select(RiskScore).where(RiskScore.score_date >= cutoff)
    if scope is not None:
        stmt = stmt.where(scope)
    rows = (await session.execute(stmt)).all()

    by_app: dict[str, list] = {}
    for r in rows:
        by_app.setdefault(r.app_name, []).append(r)

    movers = []
    for app_name, series in by_app.items():
        series.sort(key=lambda r: r.score_date)
        first, last = _series(series)
        if first is None or last is None:
            continue
        movers.append({
            "app_name": app_name,
            "delta_fused_score": round(float(last.fused_score) - float(first.fused_score), 1),
            "from_bucket": first.bucket,
            "to_bucket": last.bucket,
            "samples": len(series),
        })
    movers.sort(key=lambda m: abs(m["delta_fused_score"]), reverse=True)

    return {
        "avp": "AVP-8",
        "stage": "a",
        "requires_model": False,
        "scope_class": "tenant_scoped",
        "window_days": window_days,
        "apps_with_history": len(movers),
        "movers": movers[:limit],
    }