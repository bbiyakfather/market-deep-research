"""verify_facts.py — G3 게이트: 본문/부록 분리 · 무태그 탐지 · 태그↔대장 의미 대조.

report.md(고객용)와 facts.jsonl(대장)을 대조해 8개 규칙을 검사한다. **위반 0이 통과**
(하나라도 violation이면 exit 1). facts-schema.json이 evidence 필수필드의 단일 진실원천이고,
스키마 검증기·confirmed 판정·manifest 해시 대조는 facts_db/manifest를 그대로 재사용한다.

    python verify_facts.py --report report.md --facts facts.jsonl [--work DIR]
                           [--strict] [--json] [--convert-on]
    python verify_facts.py --selfcheck        # 정상 픽스처 통과 + 9개 적대적 변조 실패

규칙(verification-gates §G3):
  1. 본문/부록 분리 파싱 — 부록(근거표·요약표) 태그는 "본문 사용"으로 미계산.
  2. 본문 무태그 숫자 탐지 — (Fxxx) 결박 없는 사실성 숫자 차단(연도 단독은 --strict만).
  3. 태그↔대장 — 존재 + status=confirmed + lead reread match + 값·단위·기간·주체 의미 대조.
  4. confirmed인데 본문 미사용 fact 목록(경고).
  5. evidence 필수필드 — facts_db 스키마 검증기로 전 레코드 재검증(sha256·verbatim·grade).
  6. source_capture 실재 — 경로 실재 + 파일명↔ID + _reconstructed는 증빙 불인정.
  7. manifest 대조 — manifest.verify로 해시 변경 검출(변경 시 G3 재실행).
  8. [--convert-on] 환산 검산 — 본문 영어 통화단어 0 + calculation 재계산 대조.

severity: "violation"(exit 1) | "warning"(리포트만). --strict는 저위험 무태그를 violation으로.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_paths  # noqa: E402,F401  (import 시 UTF-8 콘솔 부트스트랩 1회)

import argparse  # noqa: E402
import ast  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
from decimal import Decimal, InvalidOperation  # noqa: E402

import facts_db  # noqa: E402  (load·validate_record·_has_lead_reread_match 재사용)
import manifest  # noqa: E402  (verify 재사용)


# --- 태그·숫자 정규식 ------------------------------------------------------
# (F001) 또는 (F001, F002) 형태. 그룹 안 F-ID는 findall로 뽑는다.
PAREN_TAG_RE = re.compile(r"\(\s*(F\d{3,}(?:\s*,\s*F\d{3,})*)\s*\)")
FID_RE = re.compile(r"F\d{3,}")

# 사실성 숫자 후보: [통화기호] 숫자[,천단위][.소수] [조/억/만/천] [단위]
NUM_RE = re.compile(
    r"(?P<cur>[$₩€£¥])?\s*"
    r"(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d+)\s*"
    r"(?P<mag>조|억|만|천)?\s*"
    r"(?P<unit>원|달러|유로|엔|위안|퍼센트|%포인트|%p|%|배|명|개|건|대|위|곳|년|월|일|분기)?"
)

# 환산 ON일 때 본문에 남으면 안 되는 영어 통화·단위 단어
ENGLISH_CURRENCY_RE = re.compile(
    r"\b(?:USD|EUR|GBP|JPY|CNY|KRW|million|billion|trillion|thousand|dollars?|cents?)\b",
    re.IGNORECASE,
)

_MAG = {"조": Decimal(10) ** 12, "억": Decimal(10) ** 8, "만": Decimal(10) ** 4, "천": Decimal(10) ** 3}
_CUR_UNITS = {"원", "달러", "유로", "엔", "위안"}
_PCT_UNITS = {"%", "퍼센트", "%p", "%포인트"}
_COUNT_UNITS = {"명", "개", "건", "대", "위", "곳"}

# 부록 섹션(본문 아님) 판별 키워드 — report-format §1-②③, §2, 생성 전수표.
APPENDIX_KW = ("근거표", "요약표", "한눈에", "부록", "전수", "증빙", "캡처", "캡션",
               "source_capture", "source capture", "appendix")


# --- 헤더/표 판별 ----------------------------------------------------------
_ATX_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.*\S)\s*$")
_BOLD_RE = re.compile(r"^\s*\*\*(.+?)\*\*\s*$")
_SEP_RE = re.compile(r"^\s*\|?[\s:|\-]+\|[\s:|\-]*$")


def _header_text(line: str) -> str | None:
    m = _ATX_RE.match(line)
    if m:
        return m.group(1)
    m = _BOLD_RE.match(line)
    if m:
        return m.group(1)
    return None


def _is_appendix(header: str) -> bool:
    h = header.lower()
    return any(kw.lower() in h for kw in APPENDIX_KW)


def parse_regions(text: str) -> list[dict]:
    """report.md를 줄 단위로 본문/부록 분리 파싱(규칙 1).

    부록 헤더가 나오면 다음 헤더 전까지 부록. 각 줄에 region·kind를 붙여 반환.
    kind: header|sep|table|normal.
    """
    lines = text.splitlines()
    region = "body"
    meta: list[dict] = []
    for i, line in enumerate(lines, 1):
        ht = _header_text(line)
        if ht is not None:
            region = "appendix" if _is_appendix(ht) else "body"
            meta.append({"no": i, "text": line, "region": region, "kind": "header"})
            continue
        if _SEP_RE.match(line) and "|" in line:
            kind = "sep"
        elif line.strip().startswith("|"):
            kind = "table"
        else:
            kind = "normal"
        meta.append({"no": i, "text": line, "region": region, "kind": kind})
    return meta


def _body_units(meta: list[dict]) -> list[tuple[int, str]]:
    """본문 영역의 검사 단위(문장/표셀) 목록. 무태그·의미대조가 '같은 단위' 결박을 본다."""
    units: list[tuple[int, str]] = []
    for m in meta:
        if m["region"] != "body":
            continue
        if m["kind"] == "table":
            for cell in m["text"].split("|"):
                cell = cell.strip()
                if cell:
                    units.append((m["no"], cell))
        elif m["kind"] == "normal":
            for s in re.split(r"(?<=[.!?。])\s+", m["text"]):
                s = s.strip()
                if s:
                    units.append((m["no"], s))
    return units


# --- 숫자 파싱(Decimal) ----------------------------------------------------
def _classify(m: re.Match) -> tuple[str, str]:
    """숫자 후보 → (risk, kind). risk: high|low|skip."""
    num, mag, unit, cur = m.group("num"), m.group("mag"), m.group("unit"), m.group("cur")
    if cur or unit in _CUR_UNITS:
        return "high", "currency"
    if unit in _PCT_UNITS:
        return "high", "percent"
    if unit == "배":
        return "high", "ratio"
    if mag:
        return "high", "magnitude"
    if "." in num or "," in num:
        return "high", "precise"
    if unit in _COUNT_UNITS:
        return "high", "count"
    if unit == "년":
        return "low", "year"      # 연도 단독 = 저위험(--strict만 위반)
    if unit in ("월", "일", "분기"):
        return "low", "date"
    return "skip", "plain"        # 단위 없는 맨숫자(목록·차수 등)는 사실성 아님


def _amount(m: re.Match) -> tuple[Decimal | None, Decimal | None]:
    """(coeff, scaled) — scaled는 조/억/만/천 배율 해석값(없으면 None)."""
    try:
        coeff = Decimal(m.group("num").replace(",", ""))
    except InvalidOperation:
        return None, None
    mag = m.group("mag")
    return coeff, (coeff * _MAG[mag] if mag else None)


def _fact_amount(fact: dict) -> tuple[Decimal | None, Decimal | None]:
    """대장 fact의 (coeff, scaled). value.decimal 우선, 없으면 raw+unit에서 배율 해석."""
    v = fact.get("value") or {}
    f_scaled = None
    if v.get("decimal"):
        try:
            f_scaled = Decimal(str(v["decimal"]))
        except InvalidOperation:
            pass
    m = NUM_RE.search(f"{v.get('raw', '')} {v.get('unit') or ''}")
    coeff, mag_scaled = _amount(m) if m else (None, None)
    return coeff, (f_scaled if f_scaled is not None else mag_scaled)


def _fact_unit_class(fact: dict) -> str | None:
    """대장 fact 단위의 성격: currency|percent|None."""
    v = fact.get("value") or {}
    blob = f"{v.get('raw', '')} {v.get('unit') or ''}"
    if any(u in blob for u in _PCT_UNITS) or "pp" in blob:
        return "percent"
    if any(u in blob for u in _CUR_UNITS) or any(mg in blob for mg in _MAG) \
            or re.search(r"[$₩€£¥]|KRW|USD|EUR|JPY|CNY", blob):
        return "currency"
    return None


def _close(a: Decimal, b: Decimal, tol: str = "0.005") -> bool:
    denom = max(abs(a), abs(b), Decimal(1))
    return abs(a - b) / denom <= Decimal(tol)


def _tag_spans(unit: str) -> list[tuple[int, int]]:
    return [m.span() for m in PAREN_TAG_RE.finditer(unit)]


def _bound_number(unit: str, tag_id: str) -> re.Match | None:
    """단위 내에서 tag_id에 결박된 숫자(태그 직전 우선, 없으면 직후 최근접). 태그 안 숫자는 제외."""
    spans = _tag_spans(unit)
    pos = None
    for mt in re.finditer(re.escape(tag_id), unit):
        pos = mt.start()
        break
    if pos is None and spans:
        pos = spans[0][0]
    if pos is None:
        return None
    cands = [m for m in NUM_RE.finditer(unit)
             if not any(s <= m.start() < e for s, e in spans)]
    before = [m for m in cands if m.end() <= pos]
    if before:
        return max(before, key=lambda m: m.end())
    after = [m for m in cands if m.start() >= pos]
    return min(after, key=lambda m: m.start()) if after else None


# --- 규칙 검사 -------------------------------------------------------------
def _v(findings, rule, location, detail, severity="violation"):
    findings.append({"rule": rule, "severity": severity, "location": location, "detail": detail})


def _rule5_schema(records, findings):
    """규칙 5: facts-schema.json 전 레코드 재검증(단일 진실원천)."""
    for rec in records:
        for err in facts_db.validate_record(rec):
            _v(findings, "evidence_field", f"facts.jsonl#{rec.get('id', '?')}", err)


def _rule2_untagged(units, findings, strict):
    """규칙 2: 본문 무태그 사실성 숫자."""
    for no, unit in units:
        if PAREN_TAG_RE.search(unit):
            continue  # 같은 단위에 (Fxxx) 결박 → 통과
        spans = _tag_spans(unit)
        for m in NUM_RE.finditer(unit):
            if any(s <= m.start() < e for s, e in spans):
                continue
            risk, kind = _classify(m)
            if risk == "high":
                _v(findings, "untagged_number", no,
                   f"무태그 사실 숫자 {m.group(0).strip()!r} ({kind})")
            elif risk == "low":
                _v(findings, "untagged_number", no,
                   f"무태그 저위험 숫자 {m.group(0).strip()!r} ({kind})",
                   severity="violation" if strict else "warning")


def _rule3_tags(meta, units, facts, findings) -> set[str]:
    """규칙 3: 태그 존재+confirmed+reread + 값·단위·기간·주체 의미 대조. 본문 사용 id 집합 반환."""
    used: set[str] = set()
    body_text = "\n".join(m["text"] for m in meta if m["region"] == "body")

    # 존재/상태/reread — 본문 전 영역 태그
    first_loc: dict[str, int] = {}
    for m in meta:
        if m["region"] != "body":
            continue
        for grp in PAREN_TAG_RE.findall(m["text"]):
            for fid in FID_RE.findall(grp):
                used.add(fid)
                first_loc.setdefault(fid, m["no"])
    for fid in sorted(used):
        loc = first_loc[fid]
        fact = facts.get(fid)
        if fact is None:
            _v(findings, "tag_not_found", loc, f"{fid}: 대장에 없음")
            continue
        if fact.get("status") != "confirmed":
            _v(findings, "tag_not_confirmed", loc,
               f"{fid}: status={fact.get('status')!r} (confirmed 아님)")
            continue
        if not facts_db._has_lead_reread_match(fact):
            _v(findings, "tag_not_confirmed", loc,
               f"{fid}: lead reread match verify_event 없음")

    # 의미 대조 — 문장/셀 단위(태그와 숫자가 같은 단위)
    for no, unit in units:
        for grp in PAREN_TAG_RE.findall(unit):
            for fid in FID_RE.findall(grp):
                fact = facts.get(fid)
                if fact is None or fact.get("status") != "confirmed":
                    continue
                bm = _bound_number(unit, fid)
                if bm is None:
                    continue
                b_coeff, b_scaled = _amount(bm)
                f_coeff, f_scaled = _fact_amount(fact)
                # 값 대조
                if b_scaled is not None and f_scaled is not None:
                    if not _close(b_scaled, f_scaled):
                        _v(findings, "value_mismatch", no,
                           f"{fid}: 본문 {bm.group(0).strip()!r} vs 대장 {f_scaled}")
                elif b_coeff is not None and f_coeff is not None:
                    if not _close(b_coeff, f_coeff):
                        _v(findings, "value_mismatch", no,
                           f"{fid}: 본문 {bm.group(0).strip()!r} vs 대장 raw {f_coeff}")
                # 단위 대조(통화 vs 비율 충돌만 — 보수적)
                b_risk, b_kind = _classify(bm)
                b_ucls = {"currency": "currency", "percent": "percent"}.get(b_kind)
                f_ucls = _fact_unit_class(fact)
                if b_ucls and f_ucls and b_ucls != f_ucls:
                    _v(findings, "unit_mismatch", no,
                       f"{fid}: 본문 단위 {b_ucls} vs 대장 단위 {f_ucls}")
                # 기간 대조(대장 period가 연도이고 문장에 다른 단일 연도만 있을 때)
                period = str((fact.get("context") or {}).get("period", "")).strip()
                if re.fullmatch(r"\d{4}", period):
                    yrs = set(re.findall(r"(\d{4})\s*년", unit))
                    if len(yrs) == 1 and period not in yrs:
                        _v(findings, "period_mismatch", no,
                           f"{fid}: 본문 연도 {yrs} vs 대장 period {period}")

    # 주체(entity) 부재 — 본문 어디에도 없으면 경고
    for fid in sorted(used):
        fact = facts.get(fid)
        if fact and fact.get("status") == "confirmed":
            ent = str((fact.get("context") or {}).get("entity", "")).strip()
            if ent and ent not in body_text:
                _v(findings, "entity_absent", first_loc[fid],
                   f"{fid}: 주체 {ent!r}가 본문에 없음", severity="warning")
    return used


def _rule4_unused(facts, used, findings):
    """규칙 4: confirmed인데 본문 미사용(경고)."""
    for fid, fact in sorted(facts.items()):
        if fact.get("status") == "confirmed" and fid not in used:
            _v(findings, "unused_fact", f"facts.jsonl#{fid}",
               f"{fid}: confirmed이나 본문 미사용", severity="warning")


def _rule6_captures(records, facts, work, used, findings):
    """규칙 6: source_capture 실재 + 파일명↔ID + _reconstructed 증빙 불인정."""
    valid_by_fact: dict[str, int] = {}   # fact_id → 유효(실재·비재구성) 캡처 수
    has_cap_by_fact: dict[str, int] = {}  # fact_id → capture 필드 보유 evidence 수
    for rec in records:
        if rec.get("kind") != "evidence" or not rec.get("capture"):
            continue
        eid, fid, cap = rec.get("id"), rec.get("fact_id"), rec["capture"]
        has_cap_by_fact[fid] = has_cap_by_fact.get(fid, 0) + 1
        p = (work / cap)
        reconstructed = "_reconstructed" in Path(cap).parts
        if not p.exists():
            _v(findings, "capture_missing", f"facts.jsonl#{eid}", f"{eid}: 캡처 없음 {cap}")
            continue
        if Path(cap).stem != eid:
            _v(findings, "capture_id_mismatch", f"facts.jsonl#{eid}",
               f"{eid}: 파일명 {Path(cap).name} ≠ evidence ID")
        if not reconstructed:
            valid_by_fact[fid] = valid_by_fact.get(fid, 0) + 1
    # 핵심수치(confirmed·본문사용)가 유효 캡처 없이 재구성물에만 의존 → 위반
    for fid in used:
        fact = facts.get(fid)
        if not fact or fact.get("status") != "confirmed":
            continue
        if has_cap_by_fact.get(fid, 0) > 0 and valid_by_fact.get(fid, 0) == 0:
            _v(findings, "reconstructed_only", f"facts.jsonl#{fid}",
               f"{fid}: 핵심수치가 _reconstructed 캡처에만 의존(증빙 불인정)")


def _rule7_manifest(work, findings):
    """규칙 7: manifest 해시 대조(변경 시 G3 재실행 트리거)."""
    _, changes = manifest.verify(work)
    for c in changes:
        sev = "violation" if c["status"] in ("modified", "missing") else "warning"
        _v(findings, "manifest_changed", c["path"], f"{c['status']}: {c['path']}", severity=sev)


def _rule8_convert(meta, records, findings):
    """규칙 8[--convert-on]: 본문 영어 통화단어 0 + calculation 재계산 대조."""
    for m in meta:
        if m["region"] != "body":
            continue
        for em in ENGLISH_CURRENCY_RE.finditer(m["text"]):
            _v(findings, "english_currency", m["no"], f"본문 영어 통화 단어 {em.group(0)!r}")
    for rec in records:
        if rec.get("kind") != "evidence" or rec.get("type") != "calculation":
            continue
        loc = rec.get("locator") or {}
        formula, inputs = loc.get("formula"), loc.get("inputs")
        if not isinstance(inputs, dict):
            continue  # 숫자 매핑이 아니면 재계산 불가 — 건너뜀
        got = _safe_eval(formula, inputs)
        exp = loc.get("expected")
        if got is not None and exp is not None:
            try:
                if not _close(got, Decimal(str(exp))):
                    _v(findings, "calculation_mismatch", f"facts.jsonl#{rec.get('id')}",
                       f"{rec.get('id')}: 재계산 {got} ≠ 기대 {exp}")
            except InvalidOperation:
                pass


def _safe_eval(formula, inputs: dict) -> Decimal | None:
    """+ - * / 와 입력 이름만 허용하는 Decimal 안전 계산기."""
    if not isinstance(formula, str):
        return None
    env = {}
    for k, val in inputs.items():
        try:
            env[k] = Decimal(str(val))
        except InvalidOperation:
            return None

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            a, b = ev(node.left), ev(node.right)
            return {ast.Add: a + b, ast.Sub: a - b, ast.Mult: a * b, ast.Div: (a / b if b else None)}[type(node.op)]
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return Decimal(str(node.value))
        raise ValueError("unsupported")
    try:
        return ev(ast.parse(formula, mode="eval"))
    except Exception:
        return None


# --- 오케스트레이션 --------------------------------------------------------
def verify_report(report_path, facts_path, work=None, *, strict=False, convert_on=False) -> list[dict]:
    work = Path(work) if work else Path(facts_path).resolve().parent
    text = Path(report_path).read_text(encoding="utf-8-sig")
    meta = parse_regions(text)
    units = _body_units(meta)
    records = facts_db.load(facts_path)
    facts = {r["id"]: r for r in records if r.get("kind") == "fact"}

    findings: list[dict] = []
    _rule5_schema(records, findings)                     # 5 필수필드
    _rule2_untagged(units, findings, strict)             # 2 무태그
    used = _rule3_tags(meta, units, facts, findings)     # 3 태그·의미대조
    _rule4_unused(facts, used, findings)                 # 4 미사용
    _rule6_captures(records, facts, work, used, findings)  # 6 캡처
    _rule7_manifest(work, findings)                      # 7 manifest
    if convert_on:
        _rule8_convert(meta, records, findings)          # 8 환산
    return findings


def _report(findings, as_json) -> int:
    violations = [f for f in findings if f["severity"] == "violation"]
    warnings = [f for f in findings if f["severity"] == "warning"]
    if as_json:
        print(json.dumps({"ok": not violations, "violations": violations,
                          "warnings": warnings}, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            tag = "VIOLATION" if f["severity"] == "violation" else "warning  "
            print(f"[{tag}] {f['rule']:<18} @{f['location']}  {f['detail']}")
        if violations:
            print(f"\nG3: FAIL (violation {len(violations)}건, warning {len(warnings)}건)")
        else:
            print(f"\nG3: PASS (violation 0, warning {len(warnings)}건)")
    return 1 if violations else 0


# --- selfcheck ------------------------------------------------------------
def _build_fixture(work: Path, *, run_manifest=True):
    """정상 픽스처: confirmed fact + 태그 본문 + 캡처 더미 + 최신 manifest."""
    sha = "a" * 64
    (work / "_captures").mkdir(parents=True, exist_ok=True)
    (work / "_captures" / "E001.png").write_bytes(b"dummy-capture")
    fact = {
        "kind": "fact", "claim_key": "revenue|삼성전자|kr|2024|annual|_", "id": "F001",
        "claim": "삼성전자 2024 매출",
        "context": {"metric": "revenue", "entity": "삼성전자", "geography": "KR",
                    "period": "2024", "basis": "annual"},
        "value": {"raw": "300.9", "unit": "조원", "decimal": "300900000000000"},
        "grade": {"authority": "A", "independence": "B", "directness": "A", "recency": "A"},
        "status": "confirmed", "verified_by": "lead",
        "verify_events": [{"at": "t", "by": "lead", "action": "reread",
                           "evidence_id": "E001", "source_url": "u", "result": "match", "note": None}],
        "evidence_ids": ["E001"], "discard_reason": None,
    }
    ev = {
        "kind": "evidence", "id": "E001", "fact_id": "F001", "type": "table_cell",
        "source_url": "https://dart.fss.or.kr/x.pdf", "archived_url": None, "local": "_sources/x.pdf",
        "sha256": sha, "accessed_at": "2025-01-01T00:00:00+09:00", "http_status": 200,
        "locator": {"page": 112, "row": 3, "col": 2}, "verbatim": None, "source_role": "원출처",
        "grade": {"authority": "A", "independence": "C", "directness": "A", "recency": "A"},
        "capture": "_captures/E001.png",
    }
    facts_db.save_atomic(work / "facts.jsonl", [fact, ev])
    (work / "report.md").write_text(
        "# 삼성전자 팩트시트\n\n"
        "## 시장 개요\n\n"
        "삼성전자의 2024년 매출은 300.9조원(F001)에 달했다.\n\n"
        "## 근거표\n\n"
        "| 사실 | 수치 | 출처 | 등급 | 증빙 |\n"
        "|---|---|---|---|---|\n"
        "| 매출 | 300.9조원 (F001) | https://dart.fss.or.kr | A/B/A/A | _captures/E001.png |\n",
        encoding="utf-8")
    if run_manifest:
        manifest.update(work)


def _selfcheck() -> int:
    import tempfile

    def run(work) -> tuple[int, set[str]]:
        f = verify_report(work / "report.md", work / "facts.jsonl", work)
        code = 1 if any(x["severity"] == "violation" for x in f) else 0
        rules = {x["rule"] for x in f if x["severity"] == "violation"}
        return code, rules

    def edit_facts(work, fn):
        recs = facts_db.load(work / "facts.jsonl")
        fn(recs)
        facts_db.save_atomic(work / "facts.jsonl", recs)

    def edit_report(work, old, new):
        p = work / "report.md"
        p.write_text(p.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    # 정상 픽스처 통과
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        _build_fixture(work)
        code, rules = run(work)
        assert code == 0, ("clean이 통과해야 함", rules)
    print("[selfcheck] clean → exit 0 OK")

    # 각 변조 케이스: fresh 픽스처 + mutate + (필요시)manifest 재고정 + 정확한 rule로 실패
    cases = []

    def case(name, expect, mutate, remanifest=True):
        cases.append((name, expect, mutate, remanifest))

    # ① 본문 무태그 숫자 삽입
    case("① 무태그 숫자", "untagged_number",
         lambda w: edit_report(w, "달했다.\n", "달했다.\n\n영업이익은 50조원이다.\n"))
    # ② 존재하지 않는 F태그
    case("② 없는 F태그", "tag_not_found",
         lambda w: edit_report(w, "달했다.\n", "달했다.\n\n해외 매출도 성장했다(F999).\n"))
    # ③ pending fact 태그
    def m3(w):
        def add(recs):
            recs.append({
                "kind": "fact", "claim_key": "op|삼성전자|kr|2024|annual|_", "id": "F002",
                "claim": "신규 매출",
                "context": {"metric": "op", "entity": "삼성전자", "geography": "KR",
                            "period": "2024", "basis": "annual"},
                "value": {"raw": "10", "unit": "조원", "decimal": "10000000000000"},
                "grade": {"authority": "C", "independence": "C", "directness": "C", "recency": "B"},
                "status": "pending", "verified_by": None, "verify_events": [],
                "evidence_ids": [], "discard_reason": None})
        edit_facts(w, add)
        edit_report(w, "달했다.\n", "달했다.\n\n신규 사업 매출은 10조원(F002)이다.\n")
    case("③ pending 태그", "tag_not_confirmed", m3)
    # ④ 값 불일치(본문 350 vs 대장 300.9)
    case("④ 값 불일치", "value_mismatch",
         lambda w: edit_report(w, "300.9조원(F001)에 달했다", "350조원(F001)에 달했다"))
    # ⑤ 부록에만 태그, 본문 무태그
    case("⑤ 부록 우회", "untagged_number",
         lambda w: edit_report(w, "300.9조원(F001)에 달했다", "300.9조원이다"))
    # ⑥ text_quote sha256 제거
    def m6(w):
        def mut(recs):
            for r in recs:
                if r.get("id") == "E001":
                    r["type"] = "text_quote"
                    r["verbatim"] = "매출 300.9조원"
                    r["locator"] = {"page": 112}
                    r["sha256"] = None
        edit_facts(w, mut)
    case("⑥ text_quote sha256 제거", "evidence_field", m6)
    # ⑦ capture 파일 삭제
    case("⑦ 캡처 삭제", "capture_missing",
         lambda w: (w / "_captures" / "E001.png").unlink())
    # ⑧ _reconstructed 경로로 바꿔치기
    def m8(w):
        (w / "_reconstructed").mkdir(exist_ok=True)
        (w / "_reconstructed" / "E001.png").write_bytes(b"reconstructed")
        (w / "_captures" / "E001.png").unlink()

        def mut(recs):
            for r in recs:
                if r.get("id") == "E001":
                    r["capture"] = "_reconstructed/E001.png"
        edit_facts(w, mut)
    case("⑧ _reconstructed 바꿔치기", "reconstructed_only", m8)
    # ⑨ manifest 후 파일 변조
    case("⑨ manifest 후 변조", "manifest_changed",
         lambda w: (w / "report.md").write_text(
             (w / "report.md").read_text(encoding="utf-8") + "\n<!-- tamper -->\n",
             encoding="utf-8"),
         remanifest=False)

    for name, expect, mutate, remanifest in cases:
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            _build_fixture(work)
            mutate(work)
            if remanifest:
                manifest.update(work)  # 변조를 정상 상태로 고정 → 규칙 7이 아닌 대상 규칙만 발화
            code, rules = run(work)
            assert code == 1, (name, "exit 1이어야 함", rules)
            assert expect in rules, (name, f"기대 rule {expect!r} 없음", rules)
        print(f"[selfcheck] {name} → exit 1, rule={expect} OK")

    print("SELFCHECK OK")
    return 0


# --- CLI ------------------------------------------------------------------
def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="verify_facts", description="G3 게이트: 본문/대장 대조")
    p.add_argument("--report", help="고객용 report.md")
    p.add_argument("--facts", help="facts.jsonl 대장")
    p.add_argument("--work", default=None, help="작업폴더(캡처·manifest 기준, 기본=facts 상위)")
    p.add_argument("--strict", action="store_true", help="저위험 무태그(연도 등)도 위반 처리")
    p.add_argument("--convert-on", action="store_true", help="환산 검산 규칙 8 활성화")
    p.add_argument("--json", action="store_true", help="JSON 리포트")
    p.add_argument("--selfcheck", action="store_true", help="정상 픽스처 + 9개 적대적 변조 자기검증")
    args = p.parse_args(argv)

    if args.selfcheck:
        return _selfcheck()
    if not (args.report and args.facts):
        p.error("--report 와 --facts 는 필수입니다 (또는 --selfcheck)")
    findings = verify_report(args.report, args.facts, args.work,
                             strict=args.strict, convert_on=args.convert_on)
    return _report(findings, args.json)


if __name__ == "__main__":
    sys.exit(main())
