#!/usr/bin/env python3
"""Build the synthetic ASTRA login database used by the UI development team."""

from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import json
import os
import sqlite3
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "project-docs" / "가상기업" / "v1" / "company_master.json"
OUTPUT = ROOT / "demo-ui" / "auth-demo"
DELIVERY = ROOT / "팀원배포" / "ASTRA_사용자DB_UI팀_v1.zip"
ITERATIONS = 310_000
DEMO_PASSWORD = "AstraDemo!2026"
CREATED_AT = "2026-09-22T00:00:00+09:00"

ROLES = {
    "viewer": {
        "label": "공개 공고 조회자",
        "allowed_security_levels": ["L1"],
        "allowed_document_kinds": ["public_notice"],
    },
    "bid_analyst": {
        "label": "입찰 분석가",
        "allowed_security_levels": ["L1", "L2"],
        "allowed_document_kinds": ["public_notice", "company_profile", "performance", "personnel", "certification", "staffing_plan"],
    },
    "cost_analyst": {
        "label": "원가 분석가",
        "allowed_security_levels": ["L1", "L2", "L3"],
        "allowed_document_kinds": ["public_notice", "company_profile", "performance", "personnel", "certification", "staffing_plan", "cost", "partner_quote", "estimate"],
    },
    "bid_approver": {
        "label": "입찰 승인자",
        "allowed_security_levels": ["L1", "L2", "L3"],
        "allowed_document_kinds": ["*"],
    },
}

USER_TEMPLATES = [
    ("viewer", "공개정보 열람", "active", True),
    ("bid_analyst", "입찰요건 분석", "active", True),
    ("cost_analyst", "원가 검토", "active", True),
    ("bid_approver", "입찰 승인", "active", True),
    ("bid_analyst", "비활성 계정 시험", "inactive", False),
]


def encode_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return base64.b64encode(salt).decode("ascii"), base64.b64encode(digest).decode("ascii")


def verify_password(password: str, salt_b64: str, digest_b64: str) -> bool:
    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(digest_b64)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return hmac.compare_digest(actual, expected)


def load_companies() -> list[dict]:
    master = json.loads(MASTER.read_text(encoding="utf-8"))
    companies = []
    for item in master["companies"]:
        companies.append(
            {
                "company_id": item["company_id"],
                "tenant_id": item["tenant_id"],
                "company_name": item["company_name"],
                "synthetic": True,
            }
        )
    if [x["company_id"] for x in companies] != ["C01", "C02", "C03", "C04", "C05"]:
        raise ValueError("Expected the five canonical synthetic companies C01..C05")
    return companies


def build_users(companies: list[dict]) -> list[dict]:
    users = []
    for company in companies:
        prefix = company["company_id"].lower()
        for index, (role, function, status, membership_active) in enumerate(USER_TEMPLATES, start=1):
            suffix = role if status == "active" else "inactive"
            salt, digest = encode_password(DEMO_PASSWORD)
            users.append(
                {
                    "user_id": f"USR-{company['company_id']}-{index:02d}",
                    "username": f"{prefix}_{suffix}",
                    "display_name": f"{company['company_name']} {function} 사용자",
                    "company_id": company["company_id"],
                    "tenant_id": company["tenant_id"],
                    "role": role,
                    "allowed_security_levels": ROLES[role]["allowed_security_levels"],
                    "account_status": status,
                    "membership_active": membership_active,
                    "password_algorithm": "pbkdf2_sha256",
                    "password_iterations": ITERATIONS,
                    "password_salt": salt,
                    "password_hash": digest,
                    "synthetic": True,
                    "created_at": CREATED_AT,
                }
            )
    return users


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_sqlite(path: Path, companies: list[dict], users: list[dict]) -> None:
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE companies (
          company_id TEXT PRIMARY KEY,
          tenant_id TEXT NOT NULL UNIQUE,
          company_name TEXT NOT NULL,
          synthetic INTEGER NOT NULL CHECK (synthetic = 1)
        );
        CREATE TABLE roles (
          role_id TEXT PRIMARY KEY,
          label TEXT NOT NULL,
          allowed_security_levels_json TEXT NOT NULL,
          allowed_document_kinds_json TEXT NOT NULL,
          own_tenant_only INTEGER NOT NULL CHECK (own_tenant_only = 1)
        );
        CREATE TABLE users (
          user_id TEXT PRIMARY KEY,
          username TEXT NOT NULL UNIQUE,
          display_name TEXT NOT NULL,
          company_id TEXT NOT NULL REFERENCES companies(company_id),
          tenant_id TEXT NOT NULL REFERENCES companies(tenant_id),
          role_id TEXT NOT NULL REFERENCES roles(role_id),
          account_status TEXT NOT NULL CHECK (account_status IN ('active', 'inactive')),
          membership_active INTEGER NOT NULL CHECK (membership_active IN (0, 1)),
          password_algorithm TEXT NOT NULL CHECK (password_algorithm = 'pbkdf2_sha256'),
          password_iterations INTEGER NOT NULL,
          password_salt TEXT NOT NULL,
          password_hash TEXT NOT NULL,
          synthetic INTEGER NOT NULL CHECK (synthetic = 1),
          created_at TEXT NOT NULL
        );
        CREATE INDEX users_tenant_role_idx ON users(tenant_id, role_id);
        """
    )
    connection.executemany(
        "INSERT INTO companies VALUES (:company_id, :tenant_id, :company_name, :synthetic)", companies
    )
    connection.executemany(
        "INSERT INTO roles VALUES (?, ?, ?, ?, 1)",
        [
            (
                role_id,
                rule["label"],
                json.dumps(rule["allowed_security_levels"], ensure_ascii=False),
                json.dumps(rule["allowed_document_kinds"], ensure_ascii=False),
            )
            for role_id, rule in ROLES.items()
        ],
    )
    connection.executemany(
        """INSERT INTO users VALUES (
        :user_id, :username, :display_name, :company_id, :tenant_id, :role,
        :account_status, :membership_active, :password_algorithm, :password_iterations,
        :password_salt, :password_hash, :synthetic, :created_at)""",
        users,
    )
    connection.commit()
    connection.close()


def write_credentials(path: Path, users: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["company_id", "tenant_id", "username", "role", "account_status", "demo_password"])
        for user in users:
            writer.writerow(
                [user["company_id"], user["tenant_id"], user["username"], user["role"], user["account_status"], DEMO_PASSWORD]
            )


def build() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    companies = load_companies()
    users = build_users(companies)
    public_users = {
        "schema_version": "1.0.0",
        "warning": "Synthetic local-development accounts only. The server must enforce tenant and role authorization.",
        "password_storage": {"algorithm": "PBKDF2-HMAC-SHA256", "iterations": ITERATIONS, "plaintext_stored": False},
        "companies": companies,
        "roles": [{"role": key, **value, "own_tenant_only": True} for key, value in ROLES.items()],
        "users": users,
    }
    write_json(OUTPUT / "users.demo.json", public_users)
    write_sqlite(OUTPUT / "users.demo.sqlite3", companies, users)
    write_credentials(OUTPUT / "DEMO_LOGIN_ACCOUNTS.csv", users)
    readme = f"""ASTRA 합성 사용자 DB v1

- 총 25계정: 회사 5곳 x (viewer, bid_analyst, cost_analyst, bid_approver, inactive)
- 로그인 ID: DEMO_LOGIN_ACCOUNTS.csv 참고
- 공통 개발용 암호: {DEMO_PASSWORD}
- users.demo.sqlite3에는 평문 암호가 아니라 PBKDF2-SHA256 해시만 저장됨
- 모든 계정과 회사는 합성 자료이며 로컬 UI 시연 전용

권한 규칙
- viewer: L1 공개 공고만
- bid_analyst: 자기 회사 L1/L2
- cost_analyst: 자기 회사 L1/L2와 L3 원가·견적
- bid_approver: 자기 회사 L1/L2/L3 전체
- inactive: 올바른 암호여도 로그인/문서 접근 거절

로그인 처리 기준
1. username으로 사용자를 찾고 PBKDF2-SHA256으로 암호를 검증한다.
2. account_status=active와 membership_active=true를 모두 확인한다.
3. 서버 세션에는 user_id만 저장하고, 매 요청마다 DB의 tenant_id와 role을 다시 적용한다.
4. 같은 역할이어도 다른 tenant의 L2/L3 문서는 거절한다.

주의
- 브라우저가 보내는 role, tenant_id, security_level은 권한 판단에 사용하지 않는다.
- 이 DB와 공통 암호는 로컬 UI 시연 전용이며 실제 서비스 인증 DB로 사용하지 않는다.
"""
    (OUTPUT / "README_FIRST.txt").write_text(
        readme,
        encoding="utf-8",
        newline="\n",
    )

    DELIVERY.parent.mkdir(parents=True, exist_ok=True)
    if DELIVERY.exists():
        DELIVERY.unlink()
    with zipfile.ZipFile(DELIVERY, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for item in sorted(OUTPUT.iterdir()):
            if item.is_file():
                archive.write(item, Path("ASTRA_사용자DB_UI팀_v1") / item.name)

    if len(users) != 25 or len({u["username"] for u in users}) != 25:
        raise AssertionError("Expected 25 unique demo users")
    if any(not verify_password(DEMO_PASSWORD, u["password_salt"], u["password_hash"]) for u in users):
        raise AssertionError("Password hash verification failed")
    print(f"created {len(users)} users at {OUTPUT}")
    print(f"delivery {DELIVERY}")


if __name__ == "__main__":
    try:
        build()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
