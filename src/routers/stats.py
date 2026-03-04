from fastapi import APIRouter, Query
from app.database import get_connection
from app.schemas import LayerViolationStat, AuthorStat, TrendPoint

router = APIRouter()


@router.get("/layer-violations", response_model=list[LayerViolationStat])
def layer_violation_stats(repo: str | None = None):
    """레이어별 위반 비중 — 어느 경계가 가장 많이 뚫리나"""
    with get_connection() as conn:
        if repo:
            rows = conn.execute(
                """
                SELECT lv.from_layer, lv.to_layer, COUNT(*) as count
                FROM layer_violations lv
                JOIN arch_checks ac ON ac.id = lv.check_id
                WHERE ac.repo = ?
                GROUP BY lv.from_layer, lv.to_layer
                ORDER BY count DESC
                """,
                (repo,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT from_layer, to_layer, COUNT(*) as count
                FROM layer_violations
                GROUP BY from_layer, to_layer
                ORDER BY count DESC
                """
            ).fetchall()

    total = sum(r["count"] for r in rows)
    return [
        LayerViolationStat(
            from_layer=r["from_layer"],
            to_layer=r["to_layer"],
            count=r["count"],
            ratio=round(r["count"] / total * 100, 1) if total else 0.0,
        )
        for r in rows
    ]


@router.get("/authors", response_model=list[AuthorStat])
def author_stats(repo: str | None = None):
    """기여자별 개선 현황 — 누가 얼마나 고쳤나"""
    with get_connection() as conn:
        if repo:
            rows = conn.execute(
                """
                SELECT author,
                       COUNT(*) as pr_count,
                       COALESCE(SUM(delta), 0) as total_improved,
                       MIN(delta) as best_delta
                FROM arch_checks
                WHERE repo = ? AND delta IS NOT NULL
                GROUP BY author
                ORDER BY total_improved ASC
                """,
                (repo,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT author,
                       COUNT(*) as pr_count,
                       COALESCE(SUM(delta), 0) as total_improved,
                       MIN(delta) as best_delta
                FROM arch_checks
                WHERE delta IS NOT NULL
                GROUP BY author
                ORDER BY total_improved ASC
                """
            ).fetchall()

    return [AuthorStat(**dict(r)) for r in rows]


@router.get("/trend", response_model=list[TrendPoint])
def trend(repo: str | None = None, limit: int = 30):
    """위반 수 시계열 — 전체 추이"""
    with get_connection() as conn:
        if repo:
            rows = conn.execute(
                """
                SELECT checked_at, violation_count, author, pr_number, delta
                FROM arch_checks
                WHERE repo = ?
                ORDER BY checked_at ASC
                LIMIT ?
                """,
                (repo, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT checked_at, violation_count, author, pr_number, delta
                FROM arch_checks
                ORDER BY checked_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    return [TrendPoint(**dict(r)) for r in rows]


@router.get("/summary")
def summary(repo: str | None = None):
    """전체 요약 수치"""
    with get_connection() as conn:
        q = "WHERE repo = ?" if repo else ""
        params = (repo,) if repo else ()

        row = conn.execute(
            f"""
            SELECT
                COUNT(*) as total_checks,
                MAX(violation_count) as peak_violations,
                MIN(violation_count) as best_violations,
                (SELECT violation_count FROM arch_checks {q} ORDER BY checked_at DESC LIMIT 1) as latest_violations,
                COUNT(DISTINCT author) as contributor_count
            FROM arch_checks {q}
            """,
            params * 2,
        ).fetchone()

    return dict(row)
