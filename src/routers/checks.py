from fastapi import APIRouter
from app.schemas import ArchCheckRequest, ArchCheckResponse
from app.database import get_connection
import json

router = APIRouter()


def _resolve_layer(module: str, layers: list[str]) -> str:
    """모듈 경로에서 레이어명 추출"""
    for layer in layers:
        if layer in module:
            return layer
    return module.split(".")[0] if "." in module else module


def _get_prev_violation_count(conn, repo: str, branch: str = "main") -> int | None:
    row = conn.execute(
        """
        SELECT violation_count FROM arch_checks
        WHERE repo = ? AND branch = ?
        ORDER BY checked_at DESC LIMIT 1
        """,
        (repo, branch),
    ).fetchone()
    return row["violation_count"] if row else None


@router.post("/", response_model=ArchCheckResponse, status_code=201)
def create_check(payload: ArchCheckRequest):
    with get_connection() as conn:
        # 직전 main 기준값 조회
        prev = _get_prev_violation_count(conn, payload.repo)
        delta = (payload.violation_count - prev) if prev is not None else None

        cur = conn.execute(
            """
            INSERT INTO arch_checks
              (repo, pr_number, branch, commit_sha, author,
               total_files, total_dependencies,
               violation_count, prev_violation_count, delta, raw_result)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                payload.repo,
                payload.pr_number,
                payload.branch,
                payload.commit_sha,
                payload.author,
                payload.total_files,
                payload.total_dependencies,
                payload.violation_count,
                prev,
                delta,
                payload.raw_result,
            ),
        )
        check_id = cur.lastrowid

        # 위반 상세 저장
        if payload.violations:
            conn.executemany(
                """
                INSERT INTO layer_violations
                  (check_id, from_layer, to_layer, from_module, to_module)
                VALUES (?,?,?,?,?)
                """,
                [
                    (check_id, v.from_layer, v.to_layer, v.from_module, v.to_module)
                    for v in payload.violations
                ],
            )

        row = conn.execute(
            "SELECT * FROM arch_checks WHERE id = ?", (check_id,)
        ).fetchone()

    return ArchCheckResponse(**dict(row))


@router.get("/", response_model=list[ArchCheckResponse])
def list_checks(repo: str | None = None, limit: int = 50):
    with get_connection() as conn:
        if repo:
            rows = conn.execute(
                "SELECT * FROM arch_checks WHERE repo = ? ORDER BY checked_at DESC LIMIT ?",
                (repo, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM arch_checks ORDER BY checked_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [ArchCheckResponse(**dict(r)) for r in rows]


@router.get("/{check_id}")
def get_check(check_id: int):
    with get_connection() as conn:
        check = conn.execute(
            "SELECT * FROM arch_checks WHERE id = ?", (check_id,)
        ).fetchone()
        if not check:
            from fastapi import HTTPException
            raise HTTPException(404, "Not found")
        violations = conn.execute(
            "SELECT * FROM layer_violations WHERE check_id = ?", (check_id,)
        ).fetchall()
    return {
        "check": dict(check),
        "violations": [dict(v) for v in violations],
    }
