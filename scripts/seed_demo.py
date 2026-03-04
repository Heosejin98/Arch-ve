"""
데모 데이터 생성기 — 서버가 실행 중일 때 사용
Usage: python scripts/seed_demo.py [--base-url http://localhost:8080]
"""

import argparse
import random
import string
import requests
from datetime import datetime, timedelta

AUTHORS = [
    "kim.minjun", "lee.soyeon", "park.jihoon", "choi.yuna",
    "jung.hyunwoo", "kang.minji", "cho.taehyun", "yoon.seoyeon",
]

LAYER_VIOLATIONS = [
    ("presentation", "data_access", "web.controller.UserController", "repository.UserRepository"),
    ("presentation", "data_access", "web.api.OrderApi", "repository.OrderRepository"),
    ("presentation", "infrastructure", "web.controller.AuthController", "infra.email.EmailSender"),
    ("domains", "data_access", "domain.service.PaymentService", "repository.PaymentRepository"),
    ("domains", "data_access", "domain.service.UserService", "repository.UserRepository"),
    ("domains", "infrastructure", "domain.service.NotificationService", "infra.sms.SmsSender"),
    ("infrastructure", "presentation", "infra.scheduler.BatchJob", "web.controller.ReportController"),
    ("data_access", "presentation", "repository.CacheRepo", "web.dto.CacheResponse"),
]


def random_sha():
    return "".join(random.choices(string.hexdigits[:16], k=40))


def generate_checks(n: int = 25):
    """점진적으로 개선되는 위반 추이를 가진 체크 데이터 생성"""
    checks = []
    base_time = datetime.now() - timedelta(days=n)
    violation_count = random.randint(18, 25)  # 초기 위반 수

    for i in range(n):
        author = random.choice(AUTHORS)
        pr_number = 100 + i
        # 점진적 개선: 70% 확률로 감소, 20% 유지, 10% 증가
        r = random.random()
        if r < 0.70 and violation_count > 2:
            change = -random.randint(1, 3)
        elif r < 0.90:
            change = 0
        else:
            change = random.randint(1, 2)

        violation_count = max(0, violation_count + change)

        # 위반 상세 — violation_count만큼 무작위 추출
        violations = []
        if violation_count > 0:
            sampled = random.choices(LAYER_VIOLATIONS, k=violation_count)
            violations = [
                {
                    "from_layer": v[0],
                    "to_layer": v[1],
                    "from_module": v[2],
                    "to_module": v[3],
                }
                for v in sampled
            ]

        checks.append(
            {
                "repo": "my-org/backend-api",
                "author": author,
                "branch": "main",
                "commit_sha": random_sha(),
                "pr_number": pr_number,
                "violation_count": violation_count,
                "violations": violations,
                "total_files": random.randint(80, 150),
                "total_dependencies": random.randint(200, 400),
            }
        )

    return checks


def main():
    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument("--base-url", default="http://localhost:8080")
    args = parser.parse_args()

    url = f"{args.base_url}/api/checks/"
    checks = generate_checks(25)

    print(f"Seeding {len(checks)} checks to {url} ...")
    for i, payload in enumerate(checks, 1):
        resp = requests.post(url, json=payload)
        if resp.status_code == 201:
            data = resp.json()
            print(f"  [{i:02d}] id={data['id']}  violations={data['violation_count']}  delta={data.get('delta', '—')}")
        else:
            print(f"  [{i:02d}] FAILED {resp.status_code}: {resp.text[:120]}")

    print("Done!")


if __name__ == "__main__":
    main()
