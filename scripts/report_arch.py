#!/usr/bin/env python3
"""
import-linter 결과를 파싱해서 Arch Dashboard API로 전송하는 CI 스크립트

사용법:
  python scripts/report_arch.py \
    --dashboard-url http://your-server:8080 \
    --repo owner/repo \
    --author $GITHUB_ACTOR \
    --branch $GITHUB_REF_NAME \
    --commit $GITHUB_SHA \
    --pr-number $PR_NUMBER
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

LAYER_ORDER = ["presentation", "domains", "infrastructure", "data_access"]


def detect_layer(module: str) -> str:
    for layer in LAYER_ORDER:
        if layer in module:
            return layer
    return module.split(".")[0] if "." in module else "unknown"


def run_import_linter() -> dict:
    """
    import-linter 실행 후 결과 파싱
    Returns: { total_files, total_dependencies, violation_count, violations[] }
    """
    result = subprocess.run(
        ["lint-imports", "--output-format", "json"],
        capture_output=True,
        text=True,
    )

    raw = result.stdout.strip()

    # JSON 모드 지원 여부에 따라 분기
    try:
        data = json.loads(raw)
        return _parse_json_output(data), raw
    except (json.JSONDecodeError, ValueError):
        return _parse_text_output(result.stdout + result.stderr), raw


def _parse_json_output(data: dict) -> dict:
    violations = []
    violation_count = 0

    for contract in data.get("contracts", []):
        for violation in contract.get("violations", []):
            importer = violation.get("importer", "")
            imported = violation.get("imported", "")
            violations.append({
                "from_module": importer,
                "to_module":   imported,
                "from_layer":  detect_layer(importer),
                "to_layer":    detect_layer(imported),
            })
            violation_count += 1

    return {
        "total_files":        data.get("analyzed_files", 0),
        "total_dependencies": data.get("analyzed_dependencies", 0),
        "violation_count":    violation_count,
        "violations":         violations,
    }


def _parse_text_output(text: str) -> dict:
    """
    텍스트 출력 파싱 (JSON 미지원 버전 fallback)
    예: "myproject.low.x imports myproject.high.y"
    """
    violations = []

    # 파일/의존성 수 파싱
    files_match = re.search(r"Analyzed (\d+) files, (\d+) dependencies", text)
    total_files = int(files_match.group(1)) if files_match else 0
    total_deps  = int(files_match.group(2)) if files_match else 0

    # 위반 라인 파싱: "module.a imports module.b"
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"^(\S+)\s+imports\s+(\S+)$", line)
        if m:
            importer, imported = m.group(1), m.group(2)
            violations.append({
                "from_module": importer,
                "to_module":   imported,
                "from_layer":  detect_layer(importer),
                "to_layer":    detect_layer(imported),
            })

    return {
        "total_files":        total_files,
        "total_dependencies": total_deps,
        "violation_count":    len(violations),
        "violations":         violations,
    }


def post_to_dashboard(url: str, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/checks/",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dashboard-url", required=True)
    parser.add_argument("--repo",          required=True)
    parser.add_argument("--author",        required=True)
    parser.add_argument("--branch",        default="unknown")
    parser.add_argument("--commit",        default="unknown")
    parser.add_argument("--pr-number",     type=int, default=None)
    args = parser.parse_args()

    print("🔍 import-linter 실행 중...")
    parsed, raw = run_import_linter()

    print(f"   파일: {parsed['total_files']}  |  의존성: {parsed['total_dependencies']}  |  위반: {parsed['violation_count']}")

    payload = {
        "repo":       args.repo,
        "author":     args.author,
        "branch":     args.branch,
        "commit_sha": args.commit,
        "pr_number":  args.pr_number,
        "raw_result": raw,
        **parsed,
    }

    print(f"📤 대시보드로 전송: {args.dashboard_url}")
    try:
        resp = post_to_dashboard(args.dashboard_url, payload)
        delta = resp.get("delta")
        if delta is None:
            print("   ✅ 등록 완료 (첫 체크)")
        elif delta < 0:
            print(f"   ✅ 등록 완료 — 이전 대비 {delta}건 개선!")
        elif delta > 0:
            print(f"   ⚠️  등록 완료 — 이전 대비 +{delta}건 증가")
        else:
            print("   ✅ 등록 완료 — 변화 없음")
    except Exception as e:
        print(f"   ❌ 전송 실패: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
