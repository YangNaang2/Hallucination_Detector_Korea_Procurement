#!/usr/bin/env python3
"""Build the UI-team handoff package for the five synthetic ASTRA companies."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "project-docs" / "가상기업" / "v1"
OUTPUT_ZIP = REPO_ROOT / "팀원배포" / "가상기업5개_UI자료_v1.zip"
OUTPUT_README = REPO_ROOT / "팀원배포" / "가상기업5개_UI자료_v1_README.md"
PACKAGE_ROOT_NAME = "ASTRA_가상기업5개_UI자료_v1"
FIXED_ZIP_TIME = (2026, 9, 16, 0, 0, 0)

COMPANY_ACCENTS = {
    "C01": "#2F6FAD",
    "C02": "#0B8F87",
    "C03": "#815AC0",
    "C04": "#E28A2B",
    "C05": "#D24C60",
}

ROLE_RULES = [
    {
        "role": "viewer",
        "label": "공개 공고 조회자",
        "allowed_security_levels": ["L1"],
        "company_scope": "none",
    },
    {
        "role": "bid_analyst",
        "label": "입찰 분석가",
        "allowed_security_levels": ["L1", "L2"],
        "company_scope": "own_tenant_only",
    },
    {
        "role": "cost_analyst",
        "label": "원가 분석가",
        "allowed_security_levels": ["L1", "L2", "L3"],
        "company_scope": "own_tenant_only",
    },
    {
        "role": "bid_approver",
        "label": "입찰 승인자",
        "allowed_security_levels": ["L1", "L2", "L3"],
        "company_scope": "own_tenant_only",
    },
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def company_source_base(company_id: str) -> Path:
    if company_id == "C01":
        return SOURCE_ROOT / "generated" / "C01" / "r1"
    return SOURCE_ROOT / "generated" / "C02-C05" / "r1" / company_id


def company_manifest_path(company_id: str) -> Path:
    if company_id == "C01":
        return SOURCE_ROOT / "generated" / "C01" / "r1" / "manifest.json"
    return SOURCE_ROOT / "generated" / "C02-C05" / "r1" / company_id / "manifest.json"


def build_readme(company_names: list[str], document_count: int) -> str:
    names = ", ".join(company_names)
    return f"""# ASTRA 가상기업 5개 UI 자료 v1

이 패키지는 ASTRA 데모 UI 개발팀에 전달하기 위해 기존 합성 회사 원장과 생성 문서를 묶은 자료다.

## 포함 범위

- 회사 5곳: {names}
- 기준일: 2026-04-01
- UI용 L2·L3 문서: {document_count}개
- 모든 회사와 문서는 합성 자료다. 실제 기업, 실제 실적, 실제 인증, 실제 견적이 아니다.

## 폴더

```text
public/
  companies_catalog.json       회사 선택 화면용 공개 요약
internal/
  company_master.json          회사 사실의 정본
  company_master.schema.json   원장 스키마
  companies_ui.json            내부 UI용 회사·문서 요약
  role_access.json             역할별 접근등급 예시
  access_rule_checks.json      기존 권한 검증 자료
  manifests/                   회사별 UI 패키지 문서 목록
  documents/C01...C05/L2,L3/   회사별 문서 JSON·Markdown
PACKAGE_MANIFEST.json          패키지 파일 해시와 용도
```

## UI 적용 원칙

1. `public/companies_catalog.json`만 회사 선택 카드 등 공개 정적 화면에 사용할 수 있다.
2. `internal/` 전체를 브라우저 정적 폴더에 복사하지 않는다.
3. L2·L3 문서는 서버가 인증된 사용자 회사, tenant, 역할을 확인한 뒤 필요한 문서만 반환해야 한다.
4. 브라우저의 역할 선택 드롭다운은 권한 시연 설정일 뿐 실제 접근 통제가 아니다.
5. L2는 기업 내부 실적·인력·인증 자료, L3는 원가·견적·투찰 검토 자료다.
6. `human_approval=pending`, `review_status=unreviewed`, `rag_ingest=false` 상태를 UI에서 완료로 바꾸지 않는다.
7. `missing`, 만료 인증, 참여 보류 사유를 정상·확보 완료 상태처럼 표시하지 않는다.
8. 질문·기대답·판정표는 이 패키지에 포함하지 않았다. RAG 검색 자료에 평가 정답을 넣지 않는다.

## 권장 화면

- 회사 선택: 회사명, 지역, 규모, 전문분야, 한 줄 특징
- L2 탭: 기업·등록, 실적, 인력, 인증, 배치 계획
- L3 탭: 원가 정책, 원가 산출, 공개가격 참고, 투찰 검토
- 상태 표시: 합성 자료, 기준일, 보안등급, 사람 승인 pending, 색인 상태

## 정본과 변경

회사 공통 사실을 수정할 때는 `internal/company_master.json`의 원본인
`project-docs/가상기업/v1/company_master.json`을 먼저 수정하고 검증기를 통과시킨 뒤 이 패키지를 다시 생성한다.
UI에서 공고에 맞추려고 회사의 실적·인증·인력을 임의로 바꾸지 않는다.
"""


def make_catalog_company(company: dict) -> dict:
    return {
        "company_id": company["company_id"],
        "tenant_id": company["tenant_id"],
        "company_name": company["company_name"],
        "synthetic": True,
        "snapshot_as_of": company["snapshot_as_of"],
        "enterprise_size": company["enterprise_size"],
        "region": company["headquarters"]["region"],
        "specialties": company["specialties"],
        "design_summary": company["design_summary"],
        "ui_accent": COMPANY_ACCENTS[company["company_id"]],
    }


def make_internal_company(company: dict, documents: list[dict]) -> dict:
    def registration_view(item: dict) -> dict:
        return {
            key: item.get(key)
            for key in (
                "registration_id",
                "code",
                "name",
                "status",
                "registered_on",
                "valid_until",
                "evidence_id",
            )
        }

    def certification_view(item: dict) -> dict:
        return {
            key: item.get(key)
            for key in (
                "certification_id",
                "code",
                "label",
                "holder_type",
                "holder_id",
                "valid_from",
                "valid_until",
                "evidence_state",
                "evidence_id",
            )
        }

    return {
        **make_catalog_company(company),
        "version": company["version"],
        "founded_on": company["founded_on"],
        "headcount": company.get("headcount"),
        "registrations": [registration_view(x) for x in company.get("registrations", [])],
        "certifications": [certification_view(x) for x in company.get("certifications", [])],
        "project_count": len(company.get("projects", [])),
        "personnel_count": len(company.get("personnel", [])),
        "service_count": len(company.get("services", [])),
        "known_absences": company.get("known_absences", []),
        "document_security": company.get("document_security", {}),
        "documents": documents,
    }


def zip_deterministically(source_dir: Path, output_zip: Path) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue
            relative = Path(PACKAGE_ROOT_NAME) / path.relative_to(source_dir)
            info = zipfile.ZipInfo(relative.as_posix(), FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def build_package(package_dir: Path) -> dict:
    master = load_json(SOURCE_ROOT / "company_master.json")
    companies = master["companies"]
    expected_ids = ["C01", "C02", "C03", "C04", "C05"]
    actual_ids = [company["company_id"] for company in companies]
    if actual_ids != expected_ids:
        raise ValueError(f"Expected companies {expected_ids}, got {actual_ids}")

    public_catalog = {
        "schema_version": "1.0.0",
        "dataset_id": master["dataset_id"],
        "snapshot_as_of": master["snapshot_as_of"],
        "synthetic": True,
        "intended_use": "public company selector summary only",
        "companies": [make_catalog_company(company) for company in companies],
    }
    write_json(package_dir / "public" / "companies_catalog.json", public_catalog)

    (package_dir / "internal").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_ROOT / "company_master.json", package_dir / "internal" / "company_master.json")
    shutil.copy2(
        SOURCE_ROOT / "company_master.schema.json",
        package_dir / "internal" / "company_master.schema.json",
    )
    shutil.copy2(
        SOURCE_ROOT / "access_rule_checks.json",
        package_dir / "internal" / "access_rule_checks.json",
    )
    write_json(
        package_dir / "internal" / "role_access.json",
        {
            "schema_version": "1.0.0",
            "warning": "UI role selection is not authentication. Enforce these rules on the server.",
            "roles": ROLE_RULES,
        },
    )

    internal_companies = []
    package_document_count = 0
    level_counts = {"L2": 0, "L3": 0}

    for company in companies:
        company_id = company["company_id"]
        source_base = company_source_base(company_id)
        source_manifest = load_json(company_manifest_path(company_id))
        package_documents = []

        for level in ("L2", "L3"):
            source_level = source_base / level
            if not source_level.exists():
                continue
            for source_json in sorted(source_level.glob("*.json")):
                document = load_json(source_json)
                if document.get("company_id") != company_id:
                    raise ValueError(f"Company mismatch in {source_json}")
                if document.get("security_level") != level:
                    raise ValueError(f"Security level mismatch in {source_json}")
                if document.get("synthetic") is not True:
                    raise ValueError(f"Non-synthetic document in {source_json}")

                document.pop("chunks", None)
                destination_dir = package_dir / "internal" / "documents" / company_id / level
                destination_json = destination_dir / source_json.name
                write_json(destination_json, document)

                source_markdown = source_json.with_suffix(".md")
                if source_markdown.exists():
                    write_text(destination_dir / source_markdown.name, source_markdown.read_text(encoding="utf-8"))

                document_entry = {
                    "document_id": document["document_id"],
                    "title": document["title"],
                    "kind": document["kind"],
                    "security_level": level,
                    "allowed_roles": document["allowed_roles"],
                    "document_version": document["document_version"],
                    "review_status": document["review_status"],
                    "rag_ingest": document["rag_ingest"],
                    "json_path": (
                        Path("internal") / "documents" / company_id / level / source_json.name
                    ).as_posix(),
                    "markdown_path": (
                        Path("internal") / "documents" / company_id / level / source_markdown.name
                    ).as_posix()
                    if source_markdown.exists()
                    else None,
                }
                package_documents.append(document_entry)
                package_document_count += 1
                level_counts[level] += 1

        source_manifest_by_id = {
            item["document_id"]: item for item in source_manifest.get("documents", [])
        }
        for item in package_documents:
            source_item = source_manifest_by_id.get(item["document_id"])
            if not source_item:
                raise ValueError(f"Document missing from source manifest: {item['document_id']}")
            item["automated_validation"] = source_item.get("automated_validation")
            item["human_approval"] = source_item.get("human_approval")
            item["index_status"] = source_item.get("index_status")

        package_company_manifest = {
            "company_id": company_id,
            "tenant_id": company["tenant_id"],
            "synthetic": True,
            "snapshot_as_of": company["snapshot_as_of"],
            "documents": package_documents,
        }
        write_json(
            package_dir / "internal" / "manifests" / f"{company_id}.json",
            package_company_manifest,
        )
        internal_companies.append(make_internal_company(company, package_documents))

    companies_ui = {
        "schema_version": "1.0.0",
        "dataset_id": master["dataset_id"],
        "snapshot_as_of": master["snapshot_as_of"],
        "synthetic": True,
        "warning": "Internal UI data. Do not serve as public static assets.",
        "companies": internal_companies,
    }
    write_json(package_dir / "internal" / "companies_ui.json", companies_ui)

    readme = build_readme([company["company_name"] for company in companies], package_document_count)
    write_text(package_dir / "README_FIRST.md", readme)

    manifest_files = []
    for path in sorted(package_dir.rglob("*")):
        if not path.is_file() or path.name == "PACKAGE_MANIFEST.json":
            continue
        content = path.read_bytes()
        manifest_files.append(
            {
                "path": path.relative_to(package_dir).as_posix(),
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )

    package_manifest = {
        "package_version": "1.0.0",
        "source_dataset_id": master["dataset_id"],
        "snapshot_as_of": master["snapshot_as_of"],
        "synthetic": True,
        "company_count": len(companies),
        "company_ids": expected_ids,
        "document_count": package_document_count,
        "security_level_counts": level_counts,
        "excluded": [
            "evaluation questions and expected answers",
            "chunk JSONL files",
            "source procurement documents",
            "secrets and model files",
        ],
        "files": manifest_files,
    }
    write_json(package_dir / "PACKAGE_MANIFEST.json", package_manifest)
    return package_manifest


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="astra-company-ui-") as temp_dir:
        package_dir = Path(temp_dir) / PACKAGE_ROOT_NAME
        package_dir.mkdir(parents=True)
        manifest = build_package(package_dir)
        zip_deterministically(package_dir, OUTPUT_ZIP)

    readme = f"""# 가상기업 5개 UI 전달 패키지

- ZIP: `{OUTPUT_ZIP.name}`
- 회사: C01~C05, 총 {manifest['company_count']}곳
- 문서: L2 {manifest['security_level_counts']['L2']}개, L3 {manifest['security_level_counts']['L3']}개
- 기준일: {manifest['snapshot_as_of']}
- 모든 자료는 평가용 합성 자료다.

UI 팀원은 ZIP을 압축 해제한 뒤 `README_FIRST.md`부터 읽는다.
`public/companies_catalog.json`은 회사 선택 화면용이고, `internal/`은 서버에서 권한을 확인한 뒤 사용한다.
"""
    write_text(OUTPUT_README, readme)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"zip={OUTPUT_ZIP}")
    print(f"readme={OUTPUT_README}")


if __name__ == "__main__":
    main()
