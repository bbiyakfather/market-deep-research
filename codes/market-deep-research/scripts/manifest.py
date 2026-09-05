"""manifest.py — 증거체인 SHA-256 매니페스트 기록·검증(plan-v2 핵심설계6 / G3·G5).

목적: source/capture/report/PDF/대장 파일의 해시를 고정해, G3 통과 이후 파일이 바뀌면
검출한다(변경 시 G3 재실행 트리거). 최종 PDF 무결성 재검사(G5)도 이 모듈로.

봉인 순서(G3 → [4b] → G5):
  build()  = G3 기준선. verify_facts.py CLI PASS 가 호출하고 G3 영수증에 manifest 해시를 결박한다.
  extend() = [4b] 재봉인. 기존 항목이 한 바이트도 안 바뀌었음을 먼저 확인한 뒤 렌더 산출물만
             **추가**한다(덮어쓰기 금지 — 덮어쓰면 G3 이후 변조가 새 기준선으로 세탁된다).
  verify() = 저장 항목을 경로로 직접 재해시(TRACKED 글롭 밖의 산출물도 추적) + 미봉인 신규 탐지.

CLI:
  python manifest.py build  <work_dir>   # 현재 상태 해시 기록 → manifest.json (G3 외 수동 호출은 비권장)
  python manifest.py verify <work_dir>   # [4b]·G4 영수증 확인 + [4b]↔manifest 결박 대조 후 저장본 대조,
                                         # 결과를 G5 로 자기기록(변경 시 exit 1)
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import gates
from skill_paths import WorkPaths

# 해시 대상: (라벨, 상대경로 glob). 조사 산출물의 증거체인.
# audit/** 는 절대 추가하지 말 것 — G5c·G4 가 G3 이후에도 정상적으로 audit/ 에 쓰므로
# 추가하면 정상 경로가 매번 changed 로 잡혀 G3 무한 복귀가 된다(실측 확인됨).
TRACKED = [
    ("source", "_sources/**/*"),
    ("capture", "_captures/**/*"),
    ("assets", "assets/**/*"),        # report.pdf 에 --embed-resources 로 내장되는 생성 차트
    ("images", "_images/**/*"),       # 수확 도판 + IMAGES.md + harvest index.json — 본문 도판도 PDF 에 내장된다
    ("facts", "facts.jsonl"),
    ("evidence", "evidence.jsonl"),
    ("report_md", "report.md"),
    ("report_pdf", "report.pdf"),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _tracked_paths(root: Path) -> dict[str, tuple[str, Path]]:
    paths = {}
    for label, pattern in TRACKED:
        for p in sorted(root.glob(pattern)):
            if p.is_file():
                paths[p.relative_to(root).as_posix()] = (label, p)
    return paths


def _scan(root: Path) -> dict[str, dict]:
    return {rel: {"label": label, "sha256": sha256_file(p), "size": p.stat().st_size}
            for rel, (label, p) in _tracked_paths(root).items()}


def build(work: WorkPaths | Path | str, *, for_g3: bool = False) -> dict:
    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    entries = _scan(wp.root)
    if for_g3:
        # 재검증 때 옛 렌더 결과까지 입력으로 봉인하면 새 PDF가 매번 '변조'가 된다.
        # 과거 파일/영수증은 보존하고 이번 기준선에서 렌더 산출물만 제외한다.
        outputs = {"report.pdf"}
        if wp.manifest.is_file():
            previous = _load(wp)
            outputs.update(rel for rel, meta in previous.get("entries", {}).items()
                           if meta.get("label") == "render")
            for extension in previous.get("extended", []):
                outputs.update(extension.get("added", []))
        entries = {rel: meta for rel, meta in entries.items() if rel not in outputs}
    manifest = {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "root": wp.root.name,
        "revision_id": gates.confirmed_digest(gates._read_jsonl(wp.facts)),
        "entries": entries,
    }
    wp.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _load(wp: WorkPaths) -> dict:
    return json.loads(wp.manifest.read_text(encoding="utf-8"))


def _write(wp: WorkPaths, manifest: dict) -> None:
    wp.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _diff(wp: WorkPaths, stored: dict) -> dict:
    """저장 항목은 경로로 직접 재해시한다 — TRACKED 글롭에 안 잡히는 산출물(report.hwpx·custom.pdf)도
    일단 봉인됐으면 변조·삭제를 잡는다. 신규는 글롭 스캔으로만 본다."""
    changed, missing = [], []
    for rel, meta in stored.items():
        p = wp.root / rel
        if not p.is_file():
            missing.append(rel)
        elif sha256_file(p) != meta["sha256"]:
            changed.append(rel)
    # 신규 탐지는 경로만 필요하다. 대용량 원본·캡처를 여기서 다시 해시하지 않는다.
    new = [r for r in _tracked_paths(wp.root) if r not in stored]
    return {"changed": changed, "missing": missing, "new": new}


def extend(work: WorkPaths | Path | str, paths: list[Path | str], label: str = "render",
           expected_sha256: str | None = None) -> dict:
    """[4b] 재봉인: 기존 항목 불변 확인 후 ``paths`` 만 추가한다.

    ``expected_sha256`` 는 G3 영수증이 결박한 manifest.json 해시 — 다르면 G3 이후 누군가 기준선을
    다시 만든 것이므로 거부한다. 기존 항목이 하나라도 changed/missing 이면 거부한다(= G3 복귀).
    추가 경로는 작업폴더 내부의 실재 파일이어야 한다.
    """
    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    if not wp.manifest.exists():
        raise ValueError("manifest.json 없음 — G3 기준선(build) 먼저")
    if expected_sha256 and sha256_file(wp.manifest).lower() != expected_sha256.lower():
        raise ValueError("manifest.json 이 G3 영수증의 기준선과 다름 — G3 이후 재빌드됨, G3 복귀")
    base_sha256 = sha256_file(wp.manifest)
    manifest = _load(wp)
    revision_issues = gates._check_revision(manifest, wp, "manifest")
    if revision_issues:
        raise ValueError("; ".join(revision_issues))
    d = _diff(wp, manifest["entries"])
    if d["changed"] or d["missing"]:
        raise ValueError(f"기존 봉인 항목 변조/소실 — 재봉인 거부(G3 복귀): {d}")
    root = wp.root.resolve()
    added = []
    for raw in paths:
        p = Path(raw).resolve()
        if not p.is_file():
            raise ValueError(f"추가 대상 없음: {raw}")
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            raise ValueError(f"추가 대상이 작업폴더 밖: {raw}")
        manifest["entries"][rel] = {"label": label, "sha256": sha256_file(p), "size": p.stat().st_size}
        added.append(rel)
    manifest.setdefault("extended", []).append({"at": datetime.now().isoformat(timespec="seconds"),
                                                "base_sha256": base_sha256,
                                                "added": added})
    _write(wp, manifest)
    return manifest


def verify(work: WorkPaths | Path | str) -> dict:
    """저장 항목의 해시만 대조하는 기존 API. 최종 출고는 finalize_report/CLI verify로 판정한다."""
    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    if not wp.manifest.exists():
        return {"ok": False, "reason": "manifest.json 없음", "changed": [], "missing": [], "new": []}
    d = _diff(wp, _load(wp)["entries"])
    ok = not (d["changed"] or d["missing"] or d["new"])   # 신규(미봉인) 파일도 실패 — render 산출물은 재봉인 필수
    return {"ok": ok, **d}


def _check_final_report(work: WorkPaths | Path | str) -> dict:
    """현재 원고·PDF의 실검증과 기존 체인·봉인 대조를 모두 수행한다. 쓰기 부작용 없음."""
    import verify_facts

    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    try:
        facts = verify_facts.verify(wp.report_md, wp, check_only=True)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        facts = {"ok": False, "failures": [f"[원고검사] {exc}"], "warnings": []}
    pdf = _check_pdf(wp)
    try:
        # 자기 G5의 과거 실패/드리프트는 재실행을 막지 않는다.
        checked = gates.check_prerequisites(wp, "G5")
        if not checked["ok"]:
            raise gates.GateError("; ".join(checked["issues"]))
        chain = [gates.require_receipt(wp, gate) for gate in ("G3", "[4b]", "G4")]
        reseal = chain[1]
        bound = reseal.get("manifest_sha256")
        if not bound:
            raise gates.GateError("[4b] 영수증에 manifest_sha256 결박 없음 — render_pdf.py 재실행")
        if not wp.manifest.is_file() or sha256_file(wp.manifest).lower() != str(bound).lower():
            raise gates.GateError("manifest.json 이 [4b] 영수증 결박과 다름 — [4b] 이후 재봉인/변조")
        revision_issues = gates._check_revision(_load(wp), wp, "manifest")
        if revision_issues:
            raise gates.GateError("; ".join(revision_issues))
        result = verify(wp)
    except (gates.GateError, OSError, ValueError, KeyError, TypeError) as exc:
        result = {"ok": False, "reason": str(exc), "changed": [], "missing": [], "new": []}
    reasons = ([result["reason"]] if result.get("reason") else [])
    reasons += facts.get("failures", []) + pdf.get("failures", [])
    return {**result, "ok": result["ok"] and facts["ok"] and pdf["ok"],
            "facts": facts, "pdf": pdf, "reason": "; ".join(reasons)}


def _pdf_expectations(wp: WorkPaths) -> tuple[Counter, Counter, int]:
    """렌더와 같은 GFM 파서로 표시 태그·링크·캡처 수를 구한다(참조형 링크 포함)."""
    from verify_facts import TAG, _scoped_ref

    parsed = subprocess.run(["pandoc", str(wp.report_md), "-f", "gfm", "-t", "json"],
                            capture_output=True, text=True, encoding="utf-8", timeout=30)
    if parsed.returncode:
        raise ValueError(f"PDF 대조 원고 파싱 실패: {parsed.stderr.strip()}")
    chunks, targets, captures = [], [], []

    class RawHTML(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "a" and attrs.get("href"):
                targets.append(attrs["href"])
            if tag == "img" and _scoped_ref(attrs.get("src", ""), "_captures"):
                captures.append(attrs["src"])

        def handle_data(self, data):
            chunks.append(data)

    raw_html = RawHTML()

    def walk(node):
        if isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict):
            kind, content = node.get("t"), node.get("c")
            if kind == "Image":
                if _scoped_ref(content[2][0], "_captures"):
                    captures.append(content[2][0])
                return  # 내장 이미지의 대체 텍스트는 PDF 본문에 표시되지 않는다.
            if kind == "Link":
                targets.append(content[2][0])
                walk(content[1])
                return
            if kind == "Str":
                chunks.append(content)
            elif kind in {"Code", "CodeBlock", "Math"}:
                chunks.append(content[1])
            elif kind in {"RawInline", "RawBlock"} and content[0] == "html":
                raw_html.feed(content[1])
            else:
                walk(content)

    walk(json.loads(parsed.stdout)["blocks"])
    tags = Counter(m.group(0).strip("()[]") for m in TAG.finditer("".join(chunks)))
    links = Counter(_link_target(target, wp) for target in targets)
    return tags, links, len(captures)


def _link_target(target: str, wp: WorkPaths) -> str:
    if target.startswith("#"):
        return "#internal"
    if not urlsplit(target).scheme:
        target = (wp.root / unquote(target)).resolve().as_uri()
    return unquote(target)


def _check_pdf(wp: WorkPaths) -> dict:
    """정규 PDF와 봉인된 사용자 지정 PDF를 검사한다. 원고 파싱은 한 번만 수행한다."""
    try:
        paths = {wp.report_pdf} if wp.report_pdf.is_file() else set()
        if wp.manifest.is_file():
            paths.update(wp.root / rel for rel, meta in _load(wp)["entries"].items()
                         if meta.get("label") == "render" and Path(rel).suffix.lower() == ".pdf")
        expected = _pdf_expectations(wp)
        results = {str(path.relative_to(wp.root)): _check_pdf_file(wp, path, expected)
                   for path in sorted(paths or {wp.report_pdf})}
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        return {"ok": False, "failures": [f"[PDF 검사] {exc}"], "artifacts": {}}
    return {"ok": all(result["ok"] for result in results.values()),
            "failures": [f"{path}: {failure}" for path, result in results.items()
                         for failure in result["failures"]], "artifacts": results}


def _check_pdf_file(wp: WorkPaths, pdf_path: Path, expected: tuple) -> dict:
    """PDF를 실제로 열어 원고의 F태그·링크와 캡처 배치 수가 남아 있는지 대조한다."""
    import fitz
    from verify_facts import TAG

    failures, stats = [], {}
    try:
        with fitz.open(pdf_path) as doc:
            if not doc.is_pdf or doc.needs_pass or not doc.page_count:
                raise ValueError("읽을 수 있는 PDF 페이지 없음")
            text, links, images = [], Counter(), 0
            for page in doc:
                text.append(page.get_text())
                images += len(page.get_image_info())  # 공유 XObject도 실제 배치 횟수로 센다.
                for link in page.get_links():
                    if link.get("uri"):
                        links[_link_target(link["uri"], wp)] += 1
                    elif link.get("kind") == fitz.LINK_GOTO and link.get("page", -1) >= 0:
                        links["#internal"] += 1
                    elif link.get("file"):
                        links[_link_target(link["file"], wp)] += 1
            expected_tags, expected_links, captures = expected
            tags = Counter(m.group(0).strip("()[]") for m in TAG.finditer(
                re.sub(r"\s+", "", "".join(text))))
            if missing := expected_tags - tags:
                failures.append(f"[PDF F태그] 누락: {dict(missing)}")
            if missing := expected_links - links:
                failures.append(f"[PDF 링크] 누락: {dict(missing)}")
            if images < captures:
                failures.append(f"[PDF 캡처] 원고 {captures}건 > PDF 이미지 배치 {images}건")
            stats = {"pages": doc.page_count, "tags": sum(tags.values()),
                     "links": sum(links.values()), "images": images, "expected_captures": captures}
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        failures.append(f"[PDF 검사] {exc}")
    return {"ok": not failures, "failures": failures, "stats": stats}


def _final_refs(wp: WorkPaths) -> list[dict]:
    """봉인 외 검사 입력만 별도로 결박한다. 감사 출력·일반 로그는 입력이 아니다."""
    return [{"path": rel, "sha256": sha256_file(wp.root / rel)
             if (wp.root / rel).is_file() else "missing"}
            for rel in ("manifest.json", "audit/claim-review.jsonl", "audit/research-plan.md")]


def _final_snapshot(wp: WorkPaths) -> dict[str, str]:
    """봉인 항목 전체와 정규 검사 입력을 해시한다. 없는 입력도 이후 생성을 탐지한다."""
    paths = {"manifest.json", "report.md", "report.pdf", "audit/claim-review.jsonl",
             "audit/research-plan.md", *_tracked_paths(wp.root)}
    if wp.manifest.is_file():
        paths.update(_load(wp)["entries"])
    return {rel: sha256_file(wp.root / rel) if (wp.root / rel).is_file() else "missing"
            for rel in sorted(paths)}


def finalize_report(work: WorkPaths | Path | str) -> dict:
    """출고 판정은 현재 입력의 실검증으로 계산하고 성공·실패 모두 G5에 보존한다."""
    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    refs = _final_refs(wp)
    snapshot = {}
    snapshot_error = ""
    try:
        snapshot = _final_snapshot(wp)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        snapshot_error = f"검증 입력 스냅샷 실패: {exc}"
    result = _check_final_report(wp)
    try:
        if snapshot != _final_snapshot(wp):
            snapshot_error = "검증 중 입력 변경 — 스냅샷 해시 집합 불일치"
    except (OSError, ValueError, KeyError, TypeError) as exc:
        snapshot_error = f"검증 중 입력 변경 — 재해시 실패: {exc}"
    if snapshot_error:
        result.update(ok=False, reason="; ".join(filter(None, [result["reason"], snapshot_error])))
    if result["ok"]:
        try:
            receipt = gates._record_script_result(
                wp, "G5", 0, json.dumps(result, ensure_ascii=False, sort_keys=True), extra={
                    "manifest_sha256": snapshot["manifest.json"], "refs": refs},
                _final_verification=dict(result), _snapshot_hashes=snapshot)
        except (gates.GateError, OSError, ValueError) as exc:
            result.update(ok=False, reason=str(exc))
    if not result["ok"]:
        receipt = gates._record_script_result(wp, "G5", 1,
            json.dumps(result, ensure_ascii=False, sort_keys=True), wp.facts,
            extra={"refs": refs}, _final_verification=dict(result), _snapshot_hashes=snapshot)
    result.update(revision_id=receipt["revision_id"], receipt_id=receipt["receipt_id"],
                  publication_state="최종" if result["ok"] else "재검토 필요")
    return result


def publication_state(work: WorkPaths | Path | str, receipt: dict | None = None) -> dict:
    """가벼운 상태 조회: 판정시점 결과와 현재 결박을 표시한다. 출고 재승인이 아니다."""
    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    basis = "원장 기반 판정시점 결과와 현재 스냅샷 해시 대조; 재확인은 manifest.py verify"
    receipt = receipt or gates._latest(gates._read_records(wp), "G5")
    if not receipt:
        return {"publication_state": "초안", "basis": basis,
                "checked_at": None, "bindings_match": None, "issues": []}
    result = receipt.get("final_verification") or {}
    issues = gates._receipt_issues(receipt, wp)
    verified = (receipt.get("exit") == 0 and result.get("ok") is True
                and result.get("facts", {}).get("ok") is True
                and result.get("pdf", {}).get("ok") is True)
    if not verified:
        issues.append("현재 입력을 실검증한 G5 PASS 판정 없음 — finalize 재실행 필요")
    elif receipt.get("result_summary_sha256") != gates.sha256_text(
            json.dumps(result, ensure_ascii=False, sort_keys=True)):
        issues.append("G5 실검증 결과 요약 해시 불일치")
    try:
        snapshot = receipt.get("snapshot_hashes")
        if not snapshot or snapshot != _final_snapshot(wp):
            issues.append("G5 판정 스냅샷 해시 집합 불일치/누락")
        if receipt.get("snapshot_sha256") != gates.sha256_text(
                json.dumps(snapshot, ensure_ascii=False, sort_keys=True)):
            issues.append("G5 스냅샷 요약 해시 불일치/누락")
        if receipt.get("refs") != _final_refs(wp):
            issues.append("G5 판정 입력 결박 불일치/누락")
        if receipt.get("manifest_sha256") != sha256_file(wp.manifest):
            issues.append("G5 manifest 결박 불일치/누락")
        diff = verify(wp)
        if not diff["ok"]:
            issues.append(f"G5 판정 이후 봉인 파일 변경: {diff}")
        if receipt.get("code_sha256") != gates._code_digest():
            issues.append("G5 판정 이후 검증 코드 변경")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        issues.append(str(exc))
    return {"publication_state": "최종(판정시점)" if not issues else "재검토 필요",
            "basis": basis,
            "checked_at": receipt.get("ts"), "receipt_id": gates._receipt_id(receipt),
            "bindings_match": not issues, "issues": issues}


def demo() -> None:
    import tempfile
    from skill_paths import resolve_work_dir
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("매니페스트 데모", base=td)
        wp = WorkPaths(wd)
        (wp.sources / "a.txt").write_text("hello", encoding="utf-8")
        wp.facts.write_text('{"id":"F001"}\n', encoding="utf-8")
        m = build(wp)
        assert m["entries"], "스캔 결과 비어있음"
        assert verify(wp)["ok"], "빌드 직후 verify 는 ok 여야 함"

        (wp.sources / "a.txt").write_text("tampered", encoding="utf-8")   # 변조
        v = verify(wp)
        assert not v["ok"] and v["changed"], f"변조 미검출: {v}"
        (wp.sources / "a.txt").write_text("hello", encoding="utf-8")      # 원복(다음 단언 격리)

        # G3 build 이후 render_pdf 가 report.pdf 를 새로 만드는 상황 재현 — 재봉인 전엔 미봉인 신규
        # 파일로 잡혀 실패해야 한다(V06 회귀 가드).
        wp.report_pdf.write_bytes(b"%PDF-1.4 fake")
        v2 = verify(wp)
        assert not v2["ok"] and "report.pdf" in v2["new"], f"미봉인 신규 파일이 통과됨: {v2}"

        baseline_sha = sha256_file(wp.manifest)
        extend(wp, [wp.report_pdf], expected_sha256=baseline_sha)          # [4b] 재봉인 = 추가만
        assert verify(wp)["ok"], "재봉인 후에도 실패"
        assert _load(wp)["entries"]["_sources/a.txt"]["sha256"] == m["entries"]["_sources/a.txt"]["sha256"], \
            "extend 가 기존 항목을 건드림"

        # C1 회귀: G3 이후 대장을 변조하고 재봉인하면 거부돼야 한다(세탁 차단)
        wp.facts.write_text('{"id":"F001","tampered":1}\n', encoding="utf-8")
        (wp.root / "custom.pdf").write_bytes(b"%PDF custom")
        try:
            extend(wp, [wp.root / "custom.pdf"]); raise AssertionError("변조 후 재봉인이 통과됨")
        except ValueError as e:
            assert "변조" in str(e), e
        wp.facts.write_text('{"id":"F001"}\n', encoding="utf-8")           # 원복

        # 기준선이 재빌드됐으면(G3 영수증 해시와 불일치) 거부
        try:
            extend(wp, [wp.root / "custom.pdf"], expected_sha256="0" * 64); raise AssertionError("기준선 불일치 통과")
        except ValueError as e:
            assert "기준선" in str(e), e

        # C2 회귀: TRACKED 글롭 밖 산출물(custom.pdf)도 extend 로 봉인되면 변조를 잡는다
        extend(wp, [wp.root / "custom.pdf"])
        assert verify(wp)["ok"]
        (wp.root / "custom.pdf").write_bytes(b"%PDF custom tampered")
        v3 = verify(wp)
        assert not v3["ok"] and "custom.pdf" in v3["changed"], f"글롭 밖 산출물 변조 미검출: {v3}"
        (wp.root / "custom.pdf").unlink()
        assert "custom.pdf" in verify(wp)["missing"]

        # 작업폴더 밖 경로는 거부
        outside = Path(td) / "outside.pdf"; outside.write_bytes(b"x")
        try:
            extend(wp, [outside]); raise AssertionError("폴더 밖 산출물 봉인 통과")
        except ValueError:
            pass
    print(f"[{datetime.now().isoformat(timespec='seconds')}] manifest demo OK")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    elif args[0] == "build" and len(args) == 2:
        m = build(args[1]); print(f"기록: {len(m['entries'])} 항목 → manifest.json")
    elif args[0] == "verify" and len(args) == 2:
        wp = WorkPaths(args[1])
        try:
            v = finalize_report(wp)
        except (gates.GateError, OSError, ValueError) as exc:
            print(f"[G5] 기록 실패: {exc}", file=sys.stderr)
            sys.exit(1)
        if v.get("reason"):
            print(f"[G5] 전제조건 미충족: {v['reason']}", file=sys.stderr)
        print(json.dumps(v, ensure_ascii=False, indent=2))
        sys.exit(0 if v["ok"] else 1)
    else:
        print(__doc__); sys.exit(2)
