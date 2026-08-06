"""verify_facts.py — G3 검증 게이트 (plan-v2 핵심설계6 + G3 재작성). 실패 0 이어야 통과.

검사(각각 아래 함수로 분리):
  1. split_body_appendix   — 본문/생성부록 분리(부록의 F태그는 '본문 사용'으로 미계산)
  2. check_bound_numbers   — 본문을 문장·표행 세그먼트로 나눠 수치↔F태그를 1:1 최근접 결박.
                             결박된 수치는 대장 value(raw+unit)와 Decimal 스케일·단위차원까지
                             정규화해 대조([값불일치]/[단위불일치]). 결박 안 되면 같은 세그먼트
                             (표 행 등) 안의 값일치 폴백을 거쳐도 실패하면 [무태그].
  3. (2 안에 포함) 본문에 등장한 모든 (Fxxx) 태그의 대장 존재 + status∈{confirmed}
  4. check_ledger_integrity — confirmed 인데 본문 미사용 사실(유실 점검)
  5·6. check_evidence_chain — evidence 필수필드 누락 0 · text_quote verbatim 필수 ·
                             본문에 쓰인 confirmed 핵심수치(raw 가 Decimal 로 파싱되는 값) source_capture 실재
  7. check_figures         — 본문 대표 이미지(증빙캡처·차트·도식) 존재 + 참조 경로 실재([도판경로]) +
                             생성했으나 미결박 캡처 표면화
  8. check_toc             — 목차 기계검사(G9). references/research-plan.md 의 승인 목차
                             ('# 부 N. 제목'/'## 축: 이름')를 파싱해 본문 헤딩·빈 챕터·축
                             커버리지를 대조. 계획 파일이 없으면 검사 생략(warning 만).

부록 경계: '<!-- FACTSHEET:APPENDIX -->' 주석이 있으면 그 지점을 최우선으로 쓴다. 주석이 없으면
직전 최후 출현하는 '## 부록'/'## Appendix' 헤딩을 경계로 쓴다(문서 중간의 소제목 하나로 뒤 본문
전체가 부록 취급되는 것을 막기 위해 '최초 출현'이 아니라 '최후 출현'을 쓴다). 마커/헤딩이 전혀
없으면 문서 전체를 본문으로 본다. 주석 마커를 쓰는 것을 권장한다(report-format.md 참조).

  9. [v4-Q] check_forbidden_patterns — 플레이스홀더·비밀/내부경로(FAIL)·무각주 헤지(WARN) ·
     check_capture_structure — 캡처 바이트/픽셀 구조검사(WARN) · check_cited_domains — 대상 스펙
     기대출처 미달(WARN) · --min-confirmed 정량 하한(기본 OFF) · compute_metrics — 품질 메트릭
     (결박률·evidence 깊이·도메인 편중>40% 경고·1차출처율·Bx 생존율, 게이트 아님).

CLI: python verify_facts.py <report.md> <work_dir> [--conversion] [--plan <research-plan.md>]
                            [--min-confirmed N] [--target-spec audit/target-spec.json]
                            [--metrics-out audit/quality-metrics.json]
     python verify_facts.py demo
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

import manifest
from facts_db import (FactsDB, ValidationError, check_capture_path, load_schema,
                       validate_evidence, validate_fact)
from skill_paths import WorkPaths

# --- 부록 경계 ---------------------------------------------------------------
APPX_COMMENT = re.compile(r"^[ \t]*<!--\s*FACTSHEET:APPENDIX\s*-->[ \t]*$", re.M)
APPX_HEAD = re.compile(r"^#{1,6}\s*(?:부록|Appendix)\b.*$", re.M)

# --- 수치·태그 인식 -----------------------------------------------------------
# 값(범위/오차 포함): "45", "45.5", "45~50", "45-50", "45–50", "45±2". 콤마 허용.
_NUM_CORE = r"\d[\d,]*(?:\.\d+)?"
NUM = rf"{_NUM_CORE}(?:\s*(?:[~∼\-–]\s*{_NUM_CORE}|±\s*{_NUM_CORE}))?"
# 한국식 수사 프리픽스(천백만억조) — 단위 앞에 0개 이상 연속(예: "1천억원"의 '천억').
PRE = r"[천백만억조]*"
# 사실주장으로 취급하는 단위(통화·비율·전력·에너지·질량). 연도 단독/섹션번호는 제외.
# 순서 주의: 겹치는 접두 문자열은 긴 것을 먼저(TWh 를 GW 보다 먼저 등) 둬야 오매칭이 없다.
UNIT = (r"TWh|GWh|MWh|kWh|조원|억원|만원|억달러|백만달러|Nm³/h|Nm3/h|GW|MW|kW|㎿|톤|t/y|USD|KRW"
        r"|billion|million|퍼센트|원|달러|조|억|%")
# 주의: 한국어는 교착어라 단위 뒤에 조사가 붙는다("45조원으로") → 후행 \b 금지(매칭 실패).
# 선행 (?<!제) 는 '제25조'(법조문 조항) 를 '25조'(25兆원) 로 오독하는 것을 막는다 — '조' 는
# 兆(trillion)·條(조항) 동음이의어라 실전 픽스처에서 실측된 오탐(법령 인용 표). (?<!\d) 는 숫자
# 런의 중간에서 시작하는 부분매치를 막는다 — 이게 없으면 (?<!제) 에 막힌 '25' 대신 엔진이
# '5' 만 떼어 재시도해 '제25조' 가 '5조' 로 여전히 오매칭됐다(실측).
METRIC_NUM = re.compile(rf"(?<!제)(?<!\d)({NUM})\s*({PRE})\s*({UNIT})", re.I)
TAG = re.compile(r"\(F\d{3,}\)")
# '원/조/억(원)' 은 조(兆)/조(條) 처럼 다른 한글 단어의 첫 음절과 겹치는 동음이의 단위라, 숫자와
# 공백 없이 바짝 붙을 때만 화폐 표기로 인정한다("45조원"은 화폐, "2025 원문"의 '원'은 남의 단어).
# 실전 픽스처에서 "2025 원문: ..."(원문=source text) 오매칭이 실측됐다.
_TIGHT_KRW_UNITS = {"원", "조", "억", "조원", "억원", "만원"}


def _plausible(seg: str, m: re.Match) -> bool:
    unit = m.group(3)
    if unit in _TIGHT_KRW_UNITS and re.search(r"\s", seg[m.end(1):m.start(3)]):
        return False
    return True


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def split_body_appendix(md: str) -> tuple[str, str]:
    """본문/부록 경계. 주석 마커도 헤딩 폴백과 같이 **최후 출현**을 쓴다 — 최초 출현이면
    문서 맨 앞에 마커 한 줄만 넣어 본문 전체를 검사 면제로 만들 수 있다(v5). 마커는 렌더된
    PDF 에 보이지 않으므로 사람 눈으로도 안 잡히는 완전 우회로였다."""
    marks = list(APPX_COMMENT.finditer(md))
    if marks:
        idx = marks[-1].start()
    else:
        heads = list(APPX_HEAD.finditer(md))
        idx = heads[-1].start() if heads else len(md)
    return md[:idx], md[idx:]


def check_appendix_boundary(md: str) -> tuple[list[str], list[str]]:
    """경계 마커 자체의 건전성 + 부록 구간 잔여검사.

    부록은 '값대조·무태그' 면제 구간이지 '플레이스홀더·비밀' 면제 구간이 아니다.
    경계 건전성은 비율 임계(짧은 보고서에서 오탐) 대신 구조로 판정한다 — 마커는 여러 개일
    수 없고, 본문이 통째로 비어서도 안 되며, 표준 목차의 '# 부 N.' 챕터가 부록 안에
    들어가 있어서도 안 된다(마커를 앞당겨 본문을 면제시키는 우회의 실제 형태).
    """
    failures: list[str] = []
    n = len(list(APPX_COMMENT.finditer(md)))
    if n > 1:
        failures.append(f"[부록경계] APPENDIX 마커가 {n}개 — 경계는 1개여야 한다(구간 은닉 방지)")
    body, appendix = split_body_appendix(md)
    if md.strip() and not body.strip():
        failures.append("[부록경계] 경계 마커가 문서 선두 — 본문이 비어 전 구간이 검사 면제된다")
    inside = _PLAN_PART.findall(appendix)
    if inside:
        failures.append("[부록경계] 표준 목차 챕터가 부록 구간 안에 있음: "
                        + ", ".join(f"부 {n_}. {t}" for n_, t in inside[:3]))
    for m in _PLACEHOLDER_RE.finditer(appendix):
        failures.append(f"[플레이스홀더] 부록에 미완성 마커 잔존: {m.group(0)!r}")
    for rx in _SECRET_RES:
        m = rx.search(appendix)
        if m:
            failures.append(f"[비밀유출] 부록에 키/내부경로 노출: {m.group(0)[:40]!r}")
    return failures, []


# 문장 경계: 마침표류 뒤 공백에서 자르되, '...'(줄임표)의 마지막 점은 문장 끝이 아니다
# (실전 픽스처에서 인용문 안 줄임표가 숫자·태그를 갈라놓는 것을 실측 확인).
_SENT_SPLIT = re.compile(r"(?<!\.\.)(?<=[.!?。])\s+")
# 본문 URL(마크다운 링크 대상·raw URL) — 링크 슬러그에 박힌 '100mw' 류 우연한 단위-숫자
# 문자열이 사실주장으로 오매칭되는 것을 막기 위해 세그먼트 판정 전에 무력화한다.
_URL = re.compile(r"https?://\S+")


def split_segments(body: str):
    """본문을 검사 단위로 분해: 표 행(| 로 시작하는 줄)은 행 전체를 한 세그먼트로 낸다
    (report-format.md 가 강제하는 근거표 구조는 태그와 수치가 다른 셀에 있고, _bind_pairs 가
    '|' 를 건너뛰는 직접 결박은 차단하고 행 단위 값일치 폴백만 허용한다). 그 외 줄들은 빈 줄이나
    표 행을 만나기 전까지 한 문단으로 묶은 뒤 문장부호 기준으로 쪼갠다 — 리포트가 ~80컬럼
    소프트랩으로 줄바꿈되면 '수치 …\\n(F###)'처럼 태그가 다음 줄로 넘어가는 사례가 실측되어,
    줄 단위로만 쪼개면 이런 결박이 원천적으로 불가능해지기 때문이다."""
    buf: list[str] = []

    def _flush():
        if not buf:
            return []
        text = _URL.sub("", " ".join(buf))
        buf.clear()
        return [s for s in _SENT_SPLIT.split(text) if s.strip()]

    for ln in body.splitlines():
        if ln.lstrip().startswith("|"):
            yield from _flush()
            yield _URL.sub("", ln)
        elif not ln.strip():
            yield from _flush()
        else:
            buf.append(ln.strip())
    yield from _flush()


# --- 단위 스케일(free-string value.unit 대응 — enum 아님, 미상은 fail-open+warning) -----
def _p(n: int) -> Decimal:
    return Decimal(10) ** n


UNIT_SCALE: dict[str, tuple[str, Decimal]] = {
    "조원": ("KRW", _p(12)), "억원": ("KRW", _p(8)), "만원": ("KRW", _p(4)), "원": ("KRW", Decimal(1)),
    "krw_t": ("KRW", _p(12)), "krw": ("KRW", Decimal(1)), "조": ("KRW", _p(12)), "억": ("KRW", _p(8)),
    "억달러": ("USD", _p(8)), "백만달러": ("USD", _p(6)), "달러": ("USD", Decimal(1)), "usd": ("USD", Decimal(1)),
    "twh": ("WH", _p(12)), "gwh": ("WH", _p(9)), "mwh": ("WH", _p(6)), "kwh": ("WH", _p(3)),
    "gw": ("W", _p(9)), "mw": ("W", _p(6)), "kw": ("W", _p(3)), "㎿": ("W", _p(6)),
    "톤": ("TON", Decimal(1)), "t/y": ("TON", Decimal(1)), "t": ("TON", Decimal(1)),
    "nm3/h": ("NM3H", Decimal(1)), "nm³/h": ("NM3H", Decimal(1)),
    "%": ("PCT", Decimal(1)), "퍼센트": ("PCT", Decimal(1)), "percent": ("PCT", Decimal(1)),
    "billion": ("N", _p(9)), "million": ("N", _p(6)),
}
PRE_MUL = {"천": _p(3), "백": _p(2), "만": _p(4), "억": _p(8), "조": _p(12)}
# 대장 value.unit 은 자유서식이라 "MW (PEM portion, per 2021 plan)" 같은 부연설명이 붙거나
# "EUR million"/"USD_million" 처럼 통화기호+배수 단어가 조합되기도 한다. 완전일치가 실패하면
# (1) million/billion 배수어를 먼저 찾아 배수를 곱하고 — 통화 기호(EUR/AUD 등)는 본문 쪽에서도
#     접두 통화기호를 못 읽어 어차피 차원을 못 맞추므로 배수만 취하고 차원은 "N"(일반 배수)으로
#     통일해 본문의 bare "million" 표기와 차원을 맞춘다 —, (2) 그래도 없으면 물리/통화 토큰만 찾는다.
_SCALE_TOKEN = re.compile(r"million|billion", re.I)
_UNIT_TOKEN = re.compile(r"TWh|GWh|MWh|kWh|GW|MW|kW|KRW|USD|%", re.I)


def _resolve_unit(unit: str) -> tuple[str | None, Decimal]:
    u = (unit or "").strip()
    if not u:
        return None, Decimal(1)
    if u.lower() in UNIT_SCALE:
        return UNIT_SCALE[u.lower()]
    if u in UNIT_SCALE:
        return UNIT_SCALE[u]
    sm = _SCALE_TOKEN.search(u)
    if sm:
        return "N", UNIT_SCALE[sm.group(0).lower()][1]
    m = _UNIT_TOKEN.search(u)
    if m and m.group(0).lower() in UNIT_SCALE:
        return UNIT_SCALE[m.group(0).lower()]
    return None, Decimal(1)


def _mul_of_prefix(pre: str) -> Decimal:
    m = Decimal(1)
    for ch in pre:
        m *= PRE_MUL[ch]
    return m


def _vals(txt: str) -> list[Decimal] | None:
    """'45' / '45~50' / '45-50' / '45±2' 등을 Decimal 리스트로. 콤마 제거 후 파싱.
    파싱 불가(수식·자유서식 등)면 None — value.raw 가 free string 이라 fail-open 대상.
    한국어 복합수사 부분매치(예: '1억 2천만원')는 알려진 천장이며 fail-closed 로 안전한
    방향이므로 여기서 더 손대지 않는다.
    ponytail: '1억 2천만원' 류 삽입형 복합수사 완전 파싱은 안 함 — 필요해지면 숫자+수사
    토큰을 좌→우로 누적합산하는 파서로 승격."""
    txt = (txt or "").strip()
    if not txt:
        return None
    is_pm = bool(re.search(r"±", txt))
    parts = [p for p in re.split(r"\s*(?:~|∼|-|–|±)\s*", txt) if p != ""]
    try:
        v = [Decimal(p.replace(",", "")) for p in parts]
    except InvalidOperation:
        return None
    if not v:
        return None
    if is_pm and len(v) == 2:
        v = [v[0] - v[1], v[0] + v[1]]
    return v


def _qty(numtxt: str, pre: str, unit: str) -> tuple[str | None, list[Decimal] | None]:
    """본문에서 매치된 (수치, 수사프리픽스, 단위) → (단위차원, 정규화 Decimal 리스트)."""
    v = _vals(numtxt)
    dim, mul = _resolve_unit(unit)
    if pre:
        mul = mul * _mul_of_prefix(pre)
    return dim, (None if v is None else [x * mul for x in v])


def _ledger_qty(fact: dict) -> tuple[str | None, list[Decimal] | None]:
    """대장 fact.value(raw+unit) → (단위차원, 정규화 Decimal 리스트)."""
    val = fact.get("value") or {}
    v = _vals(val.get("raw") or "")
    dim, mul = _resolve_unit(val.get("unit") or "")
    return dim, (None if v is None else [x * mul for x in v])


def _bind_pairs(seg: str, nums: list[re.Match], tags: list[re.Match]) -> dict[int, int]:
    """세그먼트 안에서 수치↔태그를 결박. 둘 사이 gap 에 '|'(표 셀 경계) 또는 다른 수치·다른
    태그가 끼어 있으면 후보에서 제외 — 태그 하나가 줄 전체 수치를 면제하거나, 세 번째 항목을
    건너뛰어 엉뚱한 수치·태그가 결박되는 것을 막는다(E2E 문장 회귀의 핵심 조건). 정렬 가중치는
    거리에 역방향(태그→수치) 페널티를 곱한 값 — '수치(태그)' 가 이 문서의 지배적 표기 관행이라
    동률에 가까우면 정방향을 우선하되, 역방향이 압도적으로 더 가까우면(진짜 인접 표기) 그쪽을
    허용한다. 순수 방향우선(역방향 절대열위)이나 순수 거리만으로는 실측된 두 회귀를 동시에 잡지
    못했다: (a) 인용부호로 감싼 서술("20 MW 전해조"(F017)와 "120 MW …"(F018))에서 역방향의
    우연히 더 가까운 남의 태그를 집어가는 오결박, (b) '…5 MW급 8기(F020), 총 40 MW로 …15
    TPD(F021)…' 에서 진짜 인접(역방향, 태그 바로 뒤) 결박을 놔두고 훨씬 먼 정방향 태그를
    골라가는 오결박. MAX_GAP 은 (b) 처럼 진짜 짝이 이미 다른 수치에 선점됐을 때, 절 하나를
    통째로 건너뛰는 먼 후보를 '그나마 남은 후보'라고 받아주지 않기 위한 절대 상한이다(실측된
    합법 gap 은 표 셀 폴백을 빼면 전부 20자 이내)."""
    MAX_GAP = 20
    cand = []
    for i, m in enumerate(nums):
        for j, t in enumerate(tags):
            if t.start() >= m.end():
                lo, hi, backward = m.end(), t.start(), False   # 정방향: 수치 뒤 태그
            elif t.end() <= m.start():
                lo, hi, backward = t.end(), m.start(), True    # 역방향: 태그 뒤 수치
            else:
                continue
            if hi - lo > MAX_GAP:
                continue
            gap = seg[lo:hi]
            if "|" in gap:
                continue
            if any(o is not m and lo <= o.start() < hi for o in nums):
                continue
            if any(o is not t and lo <= o.start() < hi for o in tags):
                continue
            weight = (hi - lo) * (2 if backward else 1)
            cand.append((weight, i, j))
    bind: dict[int, int] = {}
    used_tags: set[int] = set()
    for _, i, j in sorted(cand):
        if i in bind or j in used_tags:
            continue
        bind[i] = j
        used_tags.add(j)
    return bind


def check_bound_numbers(body: str, facts: dict) -> tuple[list[str], list[str]]:
    """무태그 숫자 차단 + (Fxxx) 존재/confirmed + 값·단위 의미대조."""
    failures: list[str] = []
    warnings: list[str] = []

    # 본문에 등장하는 모든 (Fxxx) 태그: 대장 존재 + confirmed 상태(값 유무와 무관하게 전건).
    for tag in sorted(set(m.group(0) for m in TAG.finditer(body))):
        fid = tag.strip("()")
        f = facts.get(fid)
        if not f:
            failures.append(f"[오태그] 본문 {fid} 대장에 없음")
        elif f.get("status") != "confirmed":
            failures.append(f"[미확정] 본문 {fid} status={f.get('status')}")

    # 세그먼트별 수치 결박 + 값 대조.
    for seg in split_segments(body):
        nums = [m for m in METRIC_NUM.finditer(seg) if _plausible(seg, m)]
        if not nums:
            continue
        tags = list(TAG.finditer(seg))
        bind = _bind_pairs(seg, nums, tags)
        for idx, m in enumerate(nums):
            bd, bvals = _qty(m.group(1), m.group(2), m.group(3))
            j = bind.get(idx)
            if j is None:
                # 직접 결박 실패(태그 없음 또는 표 셀 경계) → 같은 세그먼트 내 값일치 폴백.
                ok = False
                for t in tags:
                    f = facts.get(t.group(0).strip("()"))
                    if not f:
                        continue
                    ld, lv = _ledger_qty(f)
                    if lv is not None and bvals is not None and lv == bvals and \
                            (ld is None or bd is None or ld == bd):
                        ok = True
                        break
                if not ok:
                    failures.append(
                        f"[무태그] 수치 사실주장에 F태그 없음: '{m.group(0)}' (문맥: {seg.strip()[:60]!r})")
                continue
            fid = tags[j].group(0).strip("()")
            f = facts.get(fid)
            if not f:
                continue  # 오태그는 위 전역 검사에서 이미 실패 처리됨(중복 방지)
            ld, lv = _ledger_qty(f)
            if lv is None:
                warnings.append(
                    f"[값미대조] {fid}: 대장 value.raw={f.get('value', {}).get('raw')!r} "
                    f"파싱불가(수식/자유서식) — 본문 '{m.group(0)}' 비교 생략")
                continue
            if ld is None or bd is None:
                warnings.append(
                    f"[단위미상] {fid}: unit={f.get('value', {}).get('unit')!r} 인식불가 — 값만 대조")
            elif ld != bd:
                failures.append(
                    f"[단위불일치] 본문 {fid}: 표기 '{m.group(0)}' 차원={bd} ≠ 대장 차원={ld} "
                    f"(대장 {f['value']})")
                continue
            if lv != bvals:
                failures.append(
                    f"[값불일치] 본문 {fid}: 표기 '{m.group(0)}' ≠ 대장 '{f['value']['raw']}'")

    return failures, warnings


# G4: risk 태깅 누락 경고 — 지표가 이 5개 범주(시장규모·성장률·딜규모·순위·점유율)에 해당하는데
# risk=high 가 아니면 경고만(강제 아님, 다음 배치). 별도 설정 파일 없이 코드 리터럴로 유지.
_HIGH_RISK_METRICS = ("market_size", "growth_rate", "deal_size", "rank", "share")


def check_ledger_integrity(facts: dict, used: set[str], facts_raw: list[dict],
                           evidence_raw: list[dict], wp: WorkPaths) -> tuple[list[str], list[str]]:
    """confirmed 인데 본문 미사용(경고) + 대장 원시행 재검증(실패) + F-ID·E-ID·claim_key
    유일성(실패) + 고위험 지표 risk 미태깅(경고).
    verify() 가 `{f['id']: f for f in db.facts()}` 로 dict 화만 하면 같은 ID 중복행이 마지막
    값으로 조용히 덮인다 — 대장 파일에 직접 append 된 미검증 행(예: status=confirmed·
    evidence_ids=[] 인 조작 행)이나 중복 F-ID(하나가 값대조를 무력화)를 통과시킨다. 그래서
    이 함수는 raw 리스트를 따로 받아 전 행을 validate_fact/validate_evidence 로 재검증한다."""
    failures: list[str] = []
    warnings: list[str] = []
    schema = load_schema()

    seen_fid: dict[str, dict] = {}
    seen_claim_key: dict[str, str] = {}
    for f in facts_raw:
        fid = f.get("id")
        if f.get("kind") == "evidence":       # 실전 픽스처에서 실측: evidence 행이 facts.jsonl 에 섞여 있음
            failures.append(f"[대장오염] {fid}: evidence 행이 facts.jsonl 에 있음(파이프라인 오류)")
            continue
        if fid in seen_fid:
            failures.append(f"[중복ID] fact.id {fid} 가 facts.jsonl 에 중복 행 — 대장 직접조작 의심")
        else:
            seen_fid[fid] = f
        ck = f.get("claim_key")
        if ck:
            if ck in seen_claim_key and seen_claim_key[ck] != fid:
                failures.append(f"[중복claim_key] {ck!r} → {seen_claim_key[ck]}·{fid} 중복")
            else:
                seen_claim_key[ck] = fid
        try:
            validate_fact(f, schema)
        except ValidationError as e:
            failures.append(f"[대장무결성] {fid}: {e}")

    seen_eid: dict[str, dict] = {}
    for e in evidence_raw:
        eid = e.get("id")
        if e.get("kind") == "fact":
            failures.append(f"[대장오염] {eid}: fact 행이 evidence.jsonl 에 있음(파이프라인 오류)")
            continue
        if eid in seen_eid:
            failures.append(f"[중복ID] evidence.id {eid} 가 evidence.jsonl 에 중복 행")
        else:
            seen_eid[eid] = e
        try:
            validate_evidence(e, schema, wp)
        except ValidationError as ex:
            failures.append(f"[대장무결성] {eid}: {ex}")

    for fid, f in facts.items():
        if f.get("status") == "confirmed" and fid not in used:
            warnings.append(f"[미사용] confirmed {fid} 본문에서 안 쓰임")
        metric = ((f.get("context") or {}).get("metric") or "").lower()
        if any(k in metric for k in _HIGH_RISK_METRICS) and f.get("risk") != "high":
            warnings.append(f"[risk태깅] {fid} metric={metric!r} 고위험 지표인데 risk={f.get('risk')!r}")
        # [Bx] claim-graph 긍정 요건 【v8 — failure 승격】
        # 승격을 막던 이유는 "구 대장 confirmed 전건이 요건 미달이라 기존 조사가 통째로
        # 막힌다"였는데, 그 대장이 실데이터가 아니라 테스트 샘플임이 확인돼 사유가 사라졌다.
        # 범위는 **본문에 실제로 인쇄되는** confirmed high-risk 로 한정한다 — 게이트가 지키는
        # 것은 고객이 읽는 수치이고, 대장에만 있고 안 쓰인 fact 까지 막으면 과잉 차단이다.
        if f.get("risk") == "high" and f.get("status") == "confirmed":
            missing, soft = [], []
            groups = f.get("independent_groups") or []
            if len(groups) < 2:
                # 독립 관찰 2개가 원리적으로 불가능한 경우가 있다(그 회사 공시가 곧 유일한
                # 1차출처인 수치 등). 그때는 '1차출처를 직접 인용했는가'로 대체 충족시킨다 —
                # 요건을 못 지키면 risk 를 낮춰 회피하는 게임을 유도하는 것보다 낫다.
                if _cites_primary(f, evidence_raw):
                    soft.append("독립 관찰그룹 1개(1차출처 직접 인용으로 대체 충족)")
                else:
                    missing.append("독립 관찰그룹 부족(2개 미만이면 1차출처 직접 인용 필요)")
            if not f.get("counter_search"):
                missing.append("반박검색 기록 없음")
            if not f.get("primary_source_ref"):
                missing.append("기본소스 참조 없음")
            if not (f.get("observed_at") or f.get("valid_at")):
                missing.append("시간증거 없음")
            if missing:
                if fid in used:
                    failures.append(f"[반박게이트] {fid}(본문 인용): " + "·".join(missing))
                else:
                    warnings.append(f"[반박게이트] {fid}(본문 미사용): " + "·".join(missing))
            for s in soft:
                warnings.append(f"[반박게이트] {fid}: {s}")

    return failures, warnings


def _cites_primary(f: dict, evidence_raw: list[dict]) -> bool:
    """fact 의 primary_source_ref 가 실제로 '원출처' 역할의 증거를 가리키는가.
    독립 관찰그룹 2개를 못 채울 때의 대체 충족 조건 — 근거는 대장에 남아 감사 가능하다."""
    ref = f.get("primary_source_ref")
    if not ref:
        return False
    ev = next((e for e in evidence_raw if e.get("id") == ref), None)
    return bool(ev and ev.get("source_role") == "원출처"
                and ev.get("fact_id") == f.get("id"))


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.I)


def check_evidence_chain(facts: dict, evidence: dict, wp: WorkPaths, used: set[str]) -> list[str]:
    """evidence 필수필드 + text_quote verbatim + sha256 형식/실해시 대조 + confirmed 핵심수치
    source_capture 실재(신뢰경계 포함)."""
    failures = []
    for f in facts.values():
        if f.get("status") != "confirmed":
            continue
        for eid in f.get("evidence_ids", []):
            e = evidence.get(eid)
            if not e:
                failures.append(f"[증거유실] {f['id']} → {eid} 없음"); continue
            for k in ("source_url", "type", "sha256", "accessed_at"):
                if not e.get(k):
                    failures.append(f"[증거필드] {eid} '{k}' 누락")
            if e.get("type") == "text_quote" and not e.get("verbatim"):
                failures.append(f"[verbatim] {eid} text_quote 인데 verbatim 없음")
            sha = e.get("sha256")
            if sha and not _SHA256_RE.match(sha):
                failures.append(f"[해시형식] {eid} sha256 형식 오류(64자리 16진수 아님): {sha!r}")
            local = e.get("local")
            if local:
                p = wp.root / local
                if not p.exists():
                    failures.append(f"[스냅샷유실] {eid} local 경로 없음: {local}")
                elif sha and _SHA256_RE.match(sha):
                    actual = manifest.sha256_file(p)      # 새 해시 유틸 신설 금지 — manifest 재사용
                    if actual.lower() != sha.lower():
                        failures.append(f"[해시불일치] {eid} local 파일 실해시가 sha256 필드와 다름")
            else:
                # [v6/EV-1] local 이 없으면 sha256 은 대조할 대상이 없어 '아무 64자 hex' 나 통과한다
                # — 원문을 열지 않고 만든 evidence 가 A등급 1차출처로 인쇄되던 경로. 스키마
                # required 는 건드리지 않고(additive 원칙) 검증 쪽에서 닫는다.
                failures.append(f"[해시미결박] {eid} local 스냅샷 없음 — sha256 을 대조할 원문이 없다"
                                f"(fetch.py 가 저장한 _sources 경로를 local 에 실을 것)")
            # [v6/EV-5] 팀리드 재검증이 '무엇을' 재열람했는지 결박 + 시간 순서(증거 확보 이후)
            evs = [v for v in f.get("verify_events", []) if v.get("by") == "lead"]
            if evs and not any(v.get("evidence_id") for v in evs):
                failures.append(f"[재검증미결박] {f['id']} lead 재검증 이벤트에 evidence_id 없음 "
                                f"— 무엇을 재열람했는지 지목되지 않는다")
            for v in evs:
                tgt, at = v.get("evidence_id"), v.get("at")
                if tgt and at and (evidence.get(tgt) or {}).get("accessed_at"):
                    if at < evidence[tgt]["accessed_at"]:
                        failures.append(f"[재검증시각] {f['id']} 재검증이 증거 확보보다 먼저 기록됨"
                                        f"({at} < {evidence[tgt]['accessed_at']})")
        # G2 증빙: 본문에 쓰인 confirmed '핵심수치'(raw 가 Decimal 로 파싱되는 값)는 source_capture 필수.
        # risk=high 태깅 여부와 무관하게 강제 — [Bx] 반박게이트 미실행 시 캡처 0 통과되던 구멍 차단.
        is_core_num = _vals((f.get("value") or {}).get("raw", "")) is not None
        if f["id"] in used and (is_core_num or f.get("risk") == "high"):
            caps = [(evidence.get(e) or {}).get("capture") for e in f.get("evidence_ids", [])]
            caps = [c for c in caps if c]
            if not caps:
                failures.append(f"[증빙] 핵심수치 {f['id']} source_capture 없음")
            else:
                ok_cap = False
                for c in caps:
                    violation = check_capture_path(c, wp)
                    if violation:
                        failures.append(f"[증빙경계] {f['id']} capture 신뢰경계 위반({c}): {violation}")
                        continue
                    if (wp.root / c).exists():
                        ok_cap = True
                if not ok_cap:
                    failures.append(f"[증빙유실] {f['id']} 캡처 파일 없음: {caps[0]}")
    return failures


def check_capture_binding(evidence: dict, wp: WorkPaths) -> tuple[list[str], list[str]]:
    """[v6/EV-2·EV-3] 캡처가 '어느 fact 의 화면인가'를 결박.

    종전 검사는 파일 존재(exists)뿐이라 정당한 캡처 1장을 E002~E080.png 로 복제하면
    evidence 80건이 전부 통과했다 — 실제 수치가 찍힌 캡처는 0장인 채로.
    ① capture_sha256 이 있으면 실파일 해시와 일치해야 하고(사후 교체 검출),
    ② 같은 내용의 캡처가 **서로 다른 fact** 의 증빙으로 쓰이면 돌려막기다.
    """
    failures: list[str] = []
    warnings: list[str] = []
    by_content: dict[str, list[tuple[str, str]]] = {}       # 내용해시 → [(evidence id, fact id)]
    for e in evidence.values():
        cap = e.get("capture")
        if not cap:
            continue
        p = wp.root / cap
        if not p.exists():
            continue                                         # 실재 검사는 check_evidence_chain 담당
        actual = manifest.sha256_file(p)
        declared = e.get("capture_sha256")
        if declared and declared.lower() != actual.lower():
            failures.append(f"[캡처해시] {e['id']} capture 실해시가 capture_sha256 과 다름 "
                            f"— 등재 후 이미지가 교체됐다")
        elif not declared:
            warnings.append(f"[캡처미봉인] {e['id']} capture_sha256 없음 — 사후 교체를 검출할 수 없다")
        by_content.setdefault(actual, []).append((e["id"], e.get("fact_id", "?")))
    for _h, owners in by_content.items():
        facts_sharing = {fid for _eid, fid in owners}
        if len(facts_sharing) > 1:
            failures.append("[캡처재사용] 같은 캡처가 서로 다른 fact 의 증빙으로 쓰임: "
                            + ", ".join(f"{eid}({fid})" for eid, fid in sorted(owners)))
    return failures, warnings


_IMG_MD = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_IMG_HTML = re.compile(r'<img\b[^>]*\bsrc=["\']([^"\']+)["\']', re.I)


def check_figures(body: str, evidence: dict, wp: WorkPaths) -> tuple[list[str], list[str]]:
    """대표 이미지(증빙캡처·차트·도식) 존재 + 참조 경로 실재 + 생성했으나 미결박 캡처 표면화."""
    failures: list[str] = []
    warnings: list[str] = []
    if not re.search(r"!\[[^\]]*\]\([^)]+\)|<img\b|<figure\b", body, re.I):
        failures.append("[도판] 본문 대표 이미지 0장(증빙캡처·차트·도식 누락)")
    else:
        paths = _IMG_MD.findall(body) + _IMG_HTML.findall(body)
        if paths:
            def _exists(p: str) -> bool:
                p = p.split("#")[0]
                if p.startswith(("http://", "https://", "data:")):
                    return True  # 외부/데이터 URI 는 경로 실재 검사 대상 아님
                return (wp.root / p).exists() or Path(p).exists()
            if not any(_exists(p) for p in paths):
                failures.append(f"[도판경로] 참조 이미지 경로 실재 없음: {paths[0]}")

    for e in evidence.values():
        cap = e.get("capture")
        if cap and (wp.root / cap).exists() and Path(cap).name not in body:
            warnings.append(f"[미결박캡처] {cap} 생성됐으나 본문 미참조")
    return failures, warnings


# --- 목차(G9) ----------------------------------------------------------------
# research-plan.md "승인 목차 예시" 서식 — 부 번호·제목은 '# 부 N. 제목', 3부 하위 축 챕터는
# '## 축: 이름' 으로 고정 표기(문서 자체가 정본, 서식 임의 변경 금지 — 바뀌면 파서도 같이 깨져야
# 정합이 유지되므로 plan_format_contract 케이스로 실제 파일을 직접 먹여 계약을 고정한다).
_PLAN_PART = re.compile(r"^# 부 (\d+)\.\s*(.+)$", re.M)
_PLAN_AXIS = re.compile(r"^## 축:\s*(.+)$", re.M)
_COND_MARK = "(해당 시)"


def parse_plan_toc(text: str) -> tuple[list[tuple[int, str]], list[str]]:
    """승인 목차 텍스트에서 (부번호, 제목) 목록과 '3부' 바로 아래(다음 '# 부' 전까지)의
    '## 축:' 이름 목록을 뽑는다."""
    parts = [(int(n), title.strip()) for n, title in _PLAN_PART.findall(text)]
    part_matches = list(_PLAN_PART.finditer(text))
    axes: list[str] = []
    for i, m in enumerate(part_matches):
        if m.group(1) == "3":
            end = part_matches[i + 1].start() if i + 1 < len(part_matches) else len(text)
            axes = [a.strip() for a in _PLAN_AXIS.findall(text[m.end():end])]
            break
    return parts, axes


_MD_HEADING = re.compile(r"^(#{1,6})\s*(.+?)\s*$", re.M)


def check_toc(md: str, wp: WorkPaths, plan: Path | str | None = None) -> tuple[list[str], list[str]]:
    """승인 목차(research-plan.md 서식) 대비 본문의 목차 이탈·빈 껍데기·축 커버리지 검사.
    plan 을 명시하지 않으면 wp.audit/research-plan.md 를 자동 탐지하되, 그마저 없으면 검사를
    생략한다(warning 만) — 계획 파일이 없는 기존 조사를 전건 FAIL 시키지 않기 위함(비교대상
    없이는 이탈도 없다). plan 이 명시됐거나 자동탐지된 파일이 실재할 때만 failure 로 승격."""
    failures: list[str] = []
    warnings: list[str] = []
    plan_path = Path(plan) if plan else (wp.audit / "research-plan.md")
    if not plan_path.exists():
        warnings.append(f"[목차미검증] 승인 계획 없음({plan_path}) — 목차 기계검사 생략")
        return failures, warnings

    parts, axes = parse_plan_toc(plan_path.read_text(encoding="utf-8"))
    if not parts:
        warnings.append(f"[목차미검증] {plan_path} 에서 승인 목차('# 부 N.')를 못 찾음")
        return failures, warnings

    headings = [(m.start(), m.end(), len(m.group(1)), m.group(2).strip())
                for m in _MD_HEADING.finditer(md)]
    body_len = len(md)

    def _find(title: str) -> int | None:
        for idx, (_s, _e, _lvl, text) in enumerate(headings):
            if title and (title in text or text in title):
                return idx
        return None

    def _section(idx: int) -> str:
        _s, end, level, _text = headings[idx]
        nxt = next((h[0] for h in headings[idx + 1:] if h[2] <= level), body_len)
        return md[end:nxt].strip()

    for num, raw_title in parts:
        conditional = _COND_MARK in raw_title
        title = raw_title.replace(_COND_MARK, "").strip()
        idx = _find(title)
        if idx is None:
            if conditional:
                continue                # 조건부 부는 헤딩 자체가 없어도 충족
            failures.append(f"[목차이탈] 승인 목차 '부 {num}. {title}' 이 본문에 없음")
            continue
        if not _section(idx):
            failures.append(f"[빈챕터] '부 {num}. {title}' 헤딩만 있고 본문이 비어있음"
                            + ("(조건부면 '해당 없음' 한 줄 필요)" if conditional else ""))

    for axis in axes:
        idx = _find(axis)
        if idx is None:
            failures.append(f"[축누락] 승인 축 '{axis}' 챕터가 본문에 없음")
        elif not _section(idx):
            failures.append(f"[빈챕터] 축 '{axis}' 헤딩만 있고 본문이 비어있음")

    return failures, warnings


# --- [v4-Q] 금지 패턴·캡처 구조검사·품질 메트릭 -------------------------------
# 금지 패턴 상수는 문자열 연접으로 조립한다 — 이 스크립트·스킬 문서·테스트 픽스처가 패턴 문자열
# 자체를 담고 있어도 자기 자신을 오탐하지 않게(gajae verify-g002 self-safe pattern 관행).
_PLACEHOLDER_RE = re.compile("|".join([
    "TO" + "DO", "TB" + "D", r"\[캡" + r"처\]", "lor" + "em ipsum", "XX" + "XX",
]))
# 무각주 헤지: 세그먼트에 (Fxxx) 태그가 하나도 없는데 추정성 서술이 등장 — 근거 미결박 추정 신호.
_HEDGE_RE = re.compile(r"(?:으로|로)\s*추정된다|것으로\s*보인다|추산된다")
# 비밀·내부경로: 고객 PDF 공개 경계 보호(키 형식·스크래치/사용자 절대경로).
_SECRET_RES = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}"),
    re.compile(r"[A-Za-z]:\\Users\\[^\s)\"']+"),
    re.compile(r"AppData\\Local\\Temp"),
]


def check_forbidden_patterns(body: str) -> tuple[list[str], list[str]]:
    """[v4-Q] 본문 금지 패턴 — 플레이스홀더(FAIL)·비밀/내부경로(FAIL)·무각주 헤지(WARN)."""
    failures: list[str] = []
    warnings: list[str] = []
    for m in _PLACEHOLDER_RE.finditer(body):
        failures.append(f"[플레이스홀더] 미완성 마커 잔존: {m.group(0)!r}")
    for rx in _SECRET_RES:
        m = rx.search(body)
        if m:
            failures.append(f"[비밀유출] 키/내부경로 패턴 노출: {m.group(0)[:40]!r}")
    for seg in split_segments(body):
        if _HEDGE_RE.search(seg) and not TAG.search(seg):
            warnings.append(f"[무근거헤지] F태그 없는 추정 서술: {seg.strip()[:60]!r}")
    return failures, warnings


def check_capture_structure(evidence: dict, wp: WorkPaths) -> list[str]:
    """[v4-Q] 캡처 파일 구조검사(WARN 전용) — '파일이 존재한다'와 '원문 화면이 담겼다'를 분리.
    바이트 하한 + 백지·단색 판정(기준은 capture_pdf.is_blank_pixmap 이 정본 — 생성 시점에
    이미 .FAILED 로 걸러지므로 여기 걸리면 외부 도구로 만든 캡처다). fitz 미가용/판독 불가는
    판독불가 WARN(실패 위장 금지 — honest unknown)."""
    warnings: list[str] = []
    for e in evidence.values():
        cap = e.get("capture")
        if not cap:
            continue
        p = wp.root / cap
        if not p.exists():
            continue                       # 실재 검사는 check_evidence_chain 소관(FAIL)
        size = p.stat().st_size
        if size < 2048:
            warnings.append(f"[캡처구조] {e.get('id')} 캡처 {size}B — 바이트 하한(2KB) 미달")
            continue
        try:
            import fitz                    # preflight HARD 의존성 — 신규 의존 아님
            import capture_pdf             # 백지 판정 기준은 한 곳(생성기)이 정본
            with fitz.open(p) as doc:
                pix = doc[0].get_pixmap()
            blank, stat = capture_pdf.is_blank_pixmap(pix)
            if blank:
                warnings.append(f"[캡처구조] {e.get('id')} 백지·단색 의심"
                                f"(유니크 {stat['unique']}, 잉크율 {stat['ink_ratio']})")
        except Exception as ex:            # noqa: BLE001 — 판독 실패는 WARN 으로 표면화
            warnings.append(f"[캡처구조] {e.get('id')} 캡처 판독 불가({type(ex).__name__}) — 육안 확인 필요")
    return warnings


def check_cited_domains(evidence_raw: list[dict], target_spec: Path | str | None) -> list[str]:
    """[v4-S] 대상 스펙(audit/target-spec.json)의 기대 1차출처 도메인(cited_domains)이 대장에
    전무하면 '기대출처 미달' WARN. 스펙 파일이 없으면 검사 생략."""
    if not target_spec:
        return []
    sp = Path(target_spec)
    if not sp.exists():
        return []
    try:
        spec = json.loads(sp.read_text(encoding="utf-8"))
    except (OSError, ValueError) as ex:
        return [f"[대상스펙] target-spec 판독 불가({type(ex).__name__}): {sp}"]
    seen = {urlparse(e.get("source_url", "")).netloc.lower() for e in evidence_raw}
    warnings = []
    for t in spec.get("targets", []):
        for dom in t.get("cited_domains", []):
            d = dom.lower()
            if not any(d in s for s in seen if s):
                warnings.append(f"[기대출처] {t.get('name', '?')}: {dom} 이 대장에 미인용")
    return warnings


def check_out_of_scope(body: str, target_spec: Path | str | None) -> list[str]:
    """[v4-Q] 대상 스펙의 out_of_scope 용어가 본문 세그먼트에 F태그 동반 사실주장으로 등장하면
    WARN — 확정 범위 밖 주제가 보고서에 스며든 신호(리뷰 C4: 13필드 다운스트림 결박)."""
    if not target_spec:
        return []
    sp = Path(target_spec)
    if not sp.exists():
        return []
    try:
        spec = json.loads(sp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []                              # 판독 불가는 check_cited_domains 가 보고
    terms = [t for t in spec.get("out_of_scope", []) if t]
    warnings = []
    for term in terms:
        for seg in split_segments(body):
            if term in seg and TAG.search(seg):
                warnings.append(f"[축외침범] out-of-scope 용어 {term!r} 가 사실주장 세그먼트에 등장: "
                                f"{seg.strip()[:60]!r}")
                break                          # 용어당 1회 보고
    return warnings


def compute_metrics(facts_raw: list[dict], evidence_raw: list[dict], used: set[str]) -> tuple[dict, list[str]]:
    """[v4-Q] 품질 메트릭(게이트 아님·리포트 전용) — audit/quality-metrics.json 은 CLI 가 기록."""
    warnings: list[str] = []
    confirmed = [f for f in facts_raw if f.get("status") == "confirmed"]
    high = [f for f in facts_raw if f.get("risk") == "high"]
    ev_by_fact: dict[str, int] = {}
    for e in evidence_raw:
        ev_by_fact[e.get("fact_id", "")] = ev_by_fact.get(e.get("fact_id", ""), 0) + 1

    domains: dict[str, int] = {}
    for e in evidence_raw:
        d = urlparse(e.get("source_url", "")).netloc.lower()
        if d:
            domains[d] = domains.get(d, 0) + 1
    top_domain, top_share = None, 0.0
    if domains:
        top_domain = max(domains, key=domains.get)
        top_share = domains[top_domain] / sum(domains.values())
        if top_share > 0.40:
            warnings.append(f"[출처편중] 단일 도메인 {top_domain} 인용 점유 {top_share:.0%} (>40%)")

    entity_ev: dict[str, int] = {}
    for f in facts_raw:
        ent = (f.get("context") or {}).get("entity") or "na"
        entity_ev[ent] = entity_ev.get(ent, 0) + ev_by_fact.get(f.get("id", ""), 0)

    metrics = {
        "facts_total": len(facts_raw),
        "facts_confirmed": len(confirmed),
        "confirmed_used_in_body_rate": round(
            sum(1 for f in confirmed if f["id"] in used) / len(confirmed), 3) if confirmed else None,
        "evidence_per_confirmed_fact": round(
            sum(ev_by_fact.get(f["id"], 0) for f in confirmed) / len(confirmed), 2) if confirmed else None,
        "primary_source_rate": round(
            sum(1 for f in confirmed if f.get("primary_source_ref")) / len(confirmed), 3) if confirmed else None,
        "bx_survival_rate": round(
            sum(1 for f in high if f.get("status") == "confirmed") / len(high), 3) if high else None,
        "top_domain": top_domain,
        "top_domain_share": round(top_share, 3) if top_domain else None,
        "domain_citations": dict(sorted(domains.items(), key=lambda kv: -kv[1])[:20]),
        "entity_evidence_share": entity_ev,
    }
    return metrics, warnings


def verify(report_md: Path | str, work: WorkPaths | Path | str, conversion: bool = False,
          plan: Path | str | None = None, min_confirmed: int | None = None,
          target_spec: Path | str | None = None) -> dict:
    md = Path(report_md).read_text(encoding="utf-8")
    body, _appendix = split_body_appendix(md)
    db = FactsDB(work)
    facts_raw = db.facts()
    evidence_raw = db.evidence()
    facts = {f["id"]: f for f in facts_raw}
    evidence = {e["id"]: e for e in evidence_raw}
    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    used = {m.group(0).strip("()") for m in TAG.finditer(body)}

    failures: list[str] = []
    warnings: list[str] = []

    bn_fail, bn_warn = check_bound_numbers(body, facts)
    failures += bn_fail
    warnings += bn_warn

    li_fail, li_warn = check_ledger_integrity(facts, used, facts_raw, evidence_raw, wp)
    failures += li_fail
    warnings += li_warn
    failures += check_evidence_chain(facts, evidence, wp, used)
    cb_fail, cb_warn = check_capture_binding(evidence, wp)
    failures += cb_fail
    warnings += cb_warn

    fig_fail, fig_warn = check_figures(body, evidence, wp)
    failures += fig_fail
    warnings += fig_warn

    toc_fail, toc_warn = check_toc(md, wp, plan)
    failures += toc_fail
    warnings += toc_warn

    if conversion:
        for f in facts.values():
            v = f.get("value", {})
            if v.get("unit", "").startswith(("USD", "$")) and not v.get("decimal"):
                warnings.append(f"[환산] {f['id']} decimal 검산값 없음")

    # [v4-Q] 금지 패턴·캡처 구조·기대출처·정량 하한·품질 메트릭
    fp_fail, fp_warn = check_forbidden_patterns(body)
    failures += fp_fail
    warnings += fp_warn
    ab_fail, ab_warn = check_appendix_boundary(md)
    failures += ab_fail
    warnings += ab_warn
    warnings += check_capture_structure(evidence, wp)
    warnings += check_cited_domains(evidence_raw, target_spec)
    warnings += check_out_of_scope(body, target_spec)
    n_confirmed = sum(1 for f in facts.values() if f.get("status") == "confirmed")
    if min_confirmed is not None and n_confirmed < min_confirmed:
        failures.append(f"[하한] requires at least {min_confirmed} confirmed facts; "
                        f"current: {n_confirmed}")
    metrics, m_warn = compute_metrics(facts_raw, evidence_raw, used)
    warnings += m_warn

    return {"ok": len(failures) == 0, "failures": failures, "warnings": warnings,
            "metrics": metrics,
            "stats": {"facts": len(facts), "evidence": len(evidence),
                      "body_tags": len(used)}}


def _print(rep: dict) -> None:
    print(f"[G3 verify] facts={rep['stats']['facts']} evidence={rep['stats']['evidence']} "
          f"본문태그={rep['stats']['body_tags']}")
    for f in rep["failures"]:
        print("  ✗ " + f)
    for w in rep["warnings"]:
        print("  ⚠ " + w)
    print("  결과:", "PASS" if rep["ok"] else f"FAIL ({len(rep['failures'])}건)")


def _fitz_doc_with_text(text: str):
    """데모용 실제 PNG 소스 — 4바이트 스텁은 백지검사·해시결박을 받을 수 없다(v6)."""
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=420, height=200)
    page.draw_rect(fitz.Rect(10, 10, 410, 190), color=(0.1, 0.2, 0.6), width=2)
    page.insert_text((28, 70), text, fontsize=13)
    page.insert_text((28, 110), "source: https://dart.fss.or.kr", fontsize=9)
    return doc


def demo() -> None:
    import hashlib
    import tempfile
    from skill_paths import resolve_work_dir
    from facts_db import FactsDB as DB
    _h = lambda tag: hashlib.sha256(tag.encode()).hexdigest()  # 유효한 sha256 fixture 생성
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("검증 데모", base=td)
        db = DB(wd)
        # 정상 confirmed fact F001 = 300.9
        db.add_fact({"claim": "매출 300.9조",
                     "context": {"metric": "revenue", "entity": "삼성", "geography": "KR", "period": "2024"},
                     "value": {"raw": "300.9", "unit": "KRW_T"},
                     "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"},
                     "risk": "normal", "status": "pending"})
        # 증거는 실파일 결박(v6) — 스냅샷 실해시 + 캡처 실해시 + 재검증 대상 지목
        wp = WorkPaths(wd)
        wp.sources.mkdir(parents=True, exist_ok=True)
        snap = wp.root / "_sources" / "F001.txt"
        snap.write_text("삼성전자 2024년 매출 300.9조원", encoding="utf-8")
        wp.captures.mkdir(parents=True, exist_ok=True)
        cap_file = wp.root / "_captures" / "f001.png"
        _doc = _fitz_doc_with_text("매출 300.9조원")
        _doc[0].get_pixmap(dpi=110).save(str(cap_file))
        _doc.close()
        ev1 = db.add_evidence({"fact_id": "F001", "type": "table_cell",
                               "source_url": "https://dart.fss.or.kr",
                               "local": "_sources/F001.txt",
                               "sha256": hashlib.sha256(snap.read_bytes()).hexdigest(),
                               "capture": "_captures/f001.png",
                               "capture_sha256": hashlib.sha256(cap_file.read_bytes()).hexdigest()})
        db.add_verify_event("F001", "lead", "reread", evidence_id=ev1["id"])
        db.set_status("F001", "confirmed")
        # 정상 = 핵심수치에 캡처 결박 + 본문에 대표 이미지 존재
        good = ("삼성전자 2024년 매출은 300.9조원(F001) 입니다.\n\n"
                "![매출 증빙](_captures/f001.png)\n")
        (wp.root / "good.md").write_text(good, encoding="utf-8")
        assert verify(wp.root / "good.md", wd)["ok"], verify(wp.root / "good.md", wd)

        bad_untag = "시장 규모는 45조원으로 성장했다.\n"          # 무태그
        (wp.root / "u.md").write_text(bad_untag, encoding="utf-8")
        assert not verify(wp.root / "u.md", wd)["ok"], "무태그 미검출"

        bad_val = "매출은 999조원(F001) 이다.\n"                  # 값불일치
        (wp.root / "v.md").write_text(bad_val, encoding="utf-8")
        r = verify(wp.root / "v.md", wd)
        assert not r["ok"] and any("값불일치" in x for x in r["failures"]), r

        # 부록의 태그는 본문 사용으로 미계산
        appx = good + "\n## 부록\n- F001 전수표 999조원(F001)\n"
        (wp.root / "a.md").write_text(appx, encoding="utf-8")
        assert verify(wp.root / "a.md", wd)["ok"], "부록이 본문검사 오염"

        # 핵심수치인데 캡처 없음 → 증빙게이트 FAIL (risk=normal 이어도 강제)
        db.add_fact({"claim": "신규 용량 4GW",
                     "context": {"metric": "capacity", "entity": "글로벌", "geography": "GL", "period": "2025"},
                     "value": {"raw": "4", "unit": "GW"},
                     "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"},
                     "risk": "normal", "status": "pending"})
        db.add_evidence({"fact_id": "F002", "type": "text_quote", "verbatim": "surpass 4 GW",
                         "source_url": "https://iea.org", "sha256": _h("F002-E002")})   # capture 없음
        db.add_verify_event("F002", "lead", "reread")
        db.set_status("F002", "confirmed")
        nocap = "신규 용량은 4GW(F002) 이다.\n\n![](_captures/f001.jpg)\n"
        (wp.root / "nc.md").write_text(nocap, encoding="utf-8")
        r2 = verify(wp.root / "nc.md", wd)
        assert not r2["ok"] and any("증빙" in x for x in r2["failures"]), r2

        # 대표 이미지 0장 → 도판게이트 FAIL
        noimg = "삼성전자 2024년 매출은 300.9조원(F001) 입니다.\n"
        (wp.root / "ni.md").write_text(noimg, encoding="utf-8")
        r3 = verify(wp.root / "ni.md", wd)
        assert not r3["ok"] and any("도판" in x for x in r3["failures"]), r3
    print(f"[{_now()}] verify_facts demo OK")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    elif len(args) >= 2:
        def _opt(name: str) -> str | None:
            return args[args.index(name) + 1] if name in args[:-1] else None
        plan = _opt("--plan")
        mc = _opt("--min-confirmed")
        rep = verify(args[0], args[1], conversion="--conversion" in args, plan=plan,
                     min_confirmed=int(mc) if mc else None, target_spec=_opt("--target-spec"))
        metrics_out = _opt("--metrics-out")
        if metrics_out:  # [v4-Q] verify() 는 순수 유지 — 파일 기록은 CLI 경로에서만
            Path(metrics_out).parent.mkdir(parents=True, exist_ok=True)
            Path(metrics_out).write_text(
                json.dumps(rep["metrics"], ensure_ascii=False, indent=2), encoding="utf-8")
        _print(rep)
        sys.exit(0 if rep["ok"] else 1)
    else:
        print(__doc__); sys.exit(2)
