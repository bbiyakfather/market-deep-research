# 구현 계획서 — 카운슬 권고 1단계(G3 구멍 3건) + 2단계(게이트 무결성 3건)

- 대상: `codes/market-deep-research/` @ `fix/council-step1-2`(= main 4196c98, 스킬 코드 무변경 상태)
- 작성: 설계자(claude fable, 읽기 전용). 구현자: 다른 모델(grok). **이 문서만 보고 구현할 수 있게 줄 번호·변경 전/후 코드·테스트·기대판정을 전부 적었다.**
- 근거: `SYNTHESIS.md §4` 1·2단계 ← `review-claude.md` H1·H2·M1·M2·M3·H4, `review-grok.md` HIGH-G·HIGH-H·MEDIUM-2
- 줄 번호는 모두 **현재 파일 기준**. 앞 항목을 구현하면 뒤 항목의 줄 번호가 밀리므로 **함수명·앵커 문자열로 찾고, 줄 번호는 참고로만** 쓴다.

## 0. 기준선(이 세션 실측, 2026-08-21) — 구현 전 반드시 같은 값이 나와야 한다

| 명령 | 결과 |
|---|---|
| `python tests/test_adversarial.py` | **60/60** 검출 성공 |
| `python scripts/{verify_facts,gates,facts_db,manifest,make_chart,harvest_images,skill_paths}.py demo` | 7종 모두 OK |
| `python tests/test_e2e.py` | `E2E OK — facts=2 evidence=2 … G3 PASS, 무결성 OK` |
| 실전 대장 `research_글로벌PEM수전해_2026_20260807` 에 `verify_facts.verify()` 함수 호출(영수증 미기록) | **이미 FAIL**(failures 501: 스냅샷유실 289·해시불일치 191·도판출처 10·도판무결박 10·미확정 1). confirmed 620 / high 378 / 본문 사용 high 199 / `independent_groups≥2` **0건** / `counter_search` **0건** / lead 이벤트 `reread_sha256` **0건**. 원장 `gates.jsonl`: G0,G0,G1,[2],G3,G3,[4b],G4 |
| 다른 실전 폴더 2곳(KERI 69건·영수증OCR 15건) | 원장 없음, 위 필드 전부 0건 |

실행 환경 주의: Windows 에서 한글 경로·출력을 쓰는 스크립트는 `PYTHONUTF8=1 python …` 으로 돌린다(이 세션에서 미설정 시 cp949 디코드 오류 실측).

## 1. 범위 통제(반드시 지킬 것)

- **건드리는 파일**: `scripts/verify_facts.py` · `scripts/manifest.py` · `scripts/gates.py` · `scripts/facts_db.py` · `scripts/make_chart.py`(데모 1줄) · `tests/test_adversarial.py` · `tests/test_e2e.py` · `references/verification-gates.md`(4줄).
- **절대 금지**: `scripts/install.py` 실행(mirror-sync) · `README.md` 수정 · `SKILL.md` 본문 수정(§9 "문서 후속" 으로만 남긴다) · 실전 research 폴더 어떤 파일도 수정.
- **이번 배치 제외(이유 포함)**: G1 영수증 삭제(§7.5), 핫링크 도판 FAIL·라이선스 전달(C4 나머지 → 3단계 이후), `independent_groups` 를 `evidence.observer_group` 에서 유도(HIGH-G 보강 → WARN 만, §5.4), 기간·주체 대조(MEDIUM-H), `parse_markers.py`(4단계).
- 새 파일 생성 없음. 새 의존성 없음. 새 해시 유틸 없음(`manifest.sha256_file`·`gates.sha256_text` 재사용).

## 2. 설계 결정 5개 (구현자가 다시 판단하지 않도록 여기서 확정)

| # | 결정 | 이유 |
|---|---|---|
| D1 | 부록 검사는 **`check_bound_numbers(appendix, facts, lenient_untagged=True)` 한 번 더 호출**. `[오태그]·[미확정]·[값불일치]·[단위불일치]` 는 FAIL, `[무태그]` 만 `[부록무태그]` WARN. 실패 메시지에 `부록 ` 접두를 붙인다. `used`(본문 사용 집합)는 **본문 태그만** 유지(부록 태그는 여전히 '미사용') | H1 최소수정 그대로. 부록 전수표·환산근거의 값 불일치를 막되, 생성 전수표 때문에 만든 무태그 면제의 본래 목적은 유지 |
| D2 | 접두 통화는 **별도 정규식 `CUR_NUM`** 으로 잡고 `METRIC_NUM` 매치와 **겹치는 구간은 `CUR_NUM` 우선**(중복 [무태그] 방지). 차원은 통화 코드(USD/EUR/GBP/JPY/KRW/CNY). 대장 쪽 `_resolve_unit` 도 통화토큰+배수어를 읽어 `("USD", 1e6)` 처럼 돌려주되, **`"N"`(bare million/billion) 은 통화 차원과 호환**으로 취급 | 기존 대장 `USD_million` ↔ 본문 `120 million(Fxxx)` 정상 케이스를 깨지 않으면서 `$999M(F002)` 오값·`$4.5B` 무태그를 잡는다. 통화 종류 불일치($ vs €)는 이번엔 잡지 않음(알려진 천장, `ponytail:` 주석) |
| D3 | 한글 계수 단위(`건·명·개사·기·위·배·대`)는 **숫자에 바짝 붙을 때만**(`_TIGHT_KRW_UNITS` 확장) 인정. `대·기` 는 **약한 단위**: 수사 접두(만/천/억) 또는 콤마 또는 값≥100 일 때만. bare `개` 는 **넣지 않는다** | 오탐 실측 회피: `| 3 \| 건수 \|`(표 셀) · `20~30대 소비자`·`50대 여성`(연령대) · `3대 핵심 과제`(수사) · `3기 신도시`(고유명) · `4개 축`·`6개월`(보고서 구조어). §4(b) 프로브 39케이스 0 오탐 |
| D4 | `[2]` 영수증 결박은 **whole-file sha 가 아니라 "confirmed 투영 다이제스트"**(`facts_db.confirmed_digest`) 로 한다. 영수증에는 `facts_db_sha256`(전체 파일, 추적용)과 `confirmed_digest_sha256`(결박용) 둘 다 기록. `require_receipt("[2]")` 가 투영 다이제스트를 재계산해 대조 | `[2]` 이후 `[Bx]`(claim-graph 필드 기입)·`G2`(`add_evidence` → `evidence_ids` 갱신)가 **정상 흐름에서 facts.jsonl 을 바꾼다**. 전체 파일 sha 로 묶으면 매 조사마다 G3 직전 `[2]` 재기록이 강제돼 도장 찍기가 된다. 투영(= confirmed id·raw·unit·lead 재열람 이벤트)은 "재검증 선언 당시의 confirmed 집합과 값" 만 고정한다 |
| D5 | `reread_sha256` = **재열람 산출물의 SHA-256 64hex**: `fetch.py get` 이 돌려주는 `sha256`(원문 바이트) 또는 로컬 PDF 파일 해시(`manifest.sha256_file`) 또는 WebFetch 만 가능했을 때 옮겨 적은 **verbatim 문자열의 `gates.sha256_text`**. `by=="lead" and action=="reread"` 이벤트에 필수(add 시점 + validate 시점 이중 검사). G3 는 이 해시가 그 fact 의 evidence `sha256`/`local` 파일 해시/`verbatim` 해시 중 하나와도 안 맞으면 **WARN `[재열람미결박]`** | M2·MEDIUM-2. WebFetch 경로가 남아 있어 FAIL 로는 못 올리지만 "재열람 산출물 없는 lead 이벤트" 는 구조적으로 막힌다 |

---

## 3. 1단계 — G3 구멍 3건

### (c) `manifest.py` — `_images/**` 추적 (가장 작으니 먼저)

**파일·위치**: `scripts/manifest.py:25-33` `TRACKED`.

```python
# 변경 전
    ("assets", "assets/**/*"),        # report.pdf 에 --embed-resources 로 내장되는 생성 차트
# 변경 후 (한 줄 추가)
    ("assets", "assets/**/*"),        # report.pdf 에 --embed-resources 로 내장되는 생성 차트
    ("images", "_images/**/*"),       # 수확 도판 + IMAGES.md + harvest index.json — 본문 도판도 PDF 에 내장된다
```

**IMAGES.md 처리 방침(확정)**: `_images/IMAGES.md` 와 `_images/**/index.json` 도 **함께 봉인**한다(제외하지 않음). 근거: `write_image_index()`(`harvest_images.py:661-681`) 는 파일 목록과 `index.json` 만으로 결정적으로 생성되므로 같은 입력이면 같은 바이트 → G3 이후 `index` 재실행은 내용이 달라질 때만 `changed` 가 된다. 라이선스·출처 기록 자체가 봉인 대상이어야 C4(라이선스 드리프트)에도 맞다. 운영 규칙: `harvest_images.py index` 는 `[3] 보고서 작성` 단계(G3 전)에 돌린다 — 이미 SKILL.md 의 순서와 같고, 어기면 G3 복귀(assets 차트와 동일 규칙). `WorkPaths` 에 `images` 프로퍼티는 **추가하지 않는다**(`_scan` 이 `root.glob` 이라 불필요).

**새 테스트** `manifest_image_swap` (`manifest_asset_swap` 바로 아래):
```python
@case
def manifest_image_swap():
    """_images/ 도판은 report.pdf 에 내장되는데 TRACKED 밖이면 G3 뒤 교체를 G5 가 못 잡는다(M3 실측).
    긍정형 짝: 변조 안 하면 ok. IMAGES.md 도 봉인 대상."""
    assert any(pattern.startswith("_images/") for _, pattern in manifest.TRACKED)
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("도판변조", base=td)
        wp = WorkPaths(wd)
        (wp.root / "_images").mkdir()
        (wp.root / "_images" / "fig.png").write_bytes(b"\x89PNG-orig")
        manifest.build(wp)
        assert manifest.verify(wp)["ok"]
        (wp.root / "_images" / "fig.png").write_bytes(b"\x89PNG-swapped")
        v = manifest.verify(wp)
        assert not v["ok"] and "_images/fig.png" in v["changed"], v
        manifest.build(wp)
        (wp.root / "_images" / "IMAGES.md").write_text("| f |\n", encoding="utf-8")   # 봉인 후 인덱스 추가
        v2 = manifest.verify(wp)
        assert not v2["ok"] and "_images/IMAGES.md" in v2["new"], v2
```
기대: 변조 → `changed`, 미봉인 IMAGES.md → `new`. 기존 `empty_source_label_fails`·`every_missing_figure_path_is_reported` 는 `_images/` 를 쓰지만 manifest 를 안 만들므로 영향 없음.

---

### (a) `verify_facts.py` — 부록 검사

**파일·위치**
- `check_bound_numbers` 시그니처 `scripts/verify_facts.py:260`
- `[무태그]` append `:296-298`
- `verify()` 의 본문 검사 호출 `:684-686`
- demo `:761-764`
- 모듈 docstring `:4` ("부록의 F태그는 '본문 사용'으로 미계산") 와 `:19-22` 옆에 한 줄 추가

**변경 전**
```python
def check_bound_numbers(body: str, facts: dict) -> tuple[list[str], list[str]]:
    ...
                if not ok:
                    failures.append(
                        f"[무태그] 수치 사실주장에 F태그 없음: '{m.group(0)}' (문맥: {seg.strip()[:60]!r})")
                continue
```
**변경 후**
```python
def check_bound_numbers(body: str, facts: dict, *, lenient_untagged: bool = False,
                        where: str = "") -> tuple[list[str], list[str]]:
    """무태그 숫자 차단 + (Fxxx) 존재/confirmed + 값·단위 의미대조.
    lenient_untagged=True(부록): [무태그] 만 warning([부록무태그]) 으로 내리고 나머지는 동일 — 생성
    전수표 때문에 둔 무태그 면제의 본래 목적만 남기고, 오태그·미확정·값불일치는 부록에서도 막는다(H1).
    where 는 실패 메시지 접두('부록 ')."""
    ...
                if not ok:
                    msg = f"수치 사실주장에 F태그 없음: '{m.group(0)}' (문맥: {seg.strip()[:60]!r})"
                    if lenient_untagged:
                        warnings.append(f"[부록무태그] {msg}")
                    else:
                        failures.append(f"[무태그] {where}{msg}")
                continue
```
그리고 같은 함수 안의 다른 `failures.append(f"[오태그] 본문 {fid} …")`·`[미확정] 본문`·`[단위불일치] 본문`·`[값불일치] 본문` 네 곳의 리터럴 `본문 ` 을 `{where or '본문 '}` 로 바꾼다(부록이면 `부록 F001`, 본문이면 기존 문자열 그대로 → 기존 테스트 문자열 매칭 유지).

`verify()` (`:684-686`) 변경 후:
```python
    bn_fail, bn_warn = check_bound_numbers(body, facts)
    failures += bn_fail
    warnings += bn_warn
    # 부록(H1): 무태그만 면제, 오태그·미확정·값·단위 대조는 본문과 동일하게 적용. used 는 본문 태그만.
    ap_fail, ap_warn = check_bound_numbers(_appendix, facts, lenient_untagged=True, where="부록 ")
    failures += ap_fail
    warnings += ap_warn
```
(`_appendix` 변수명은 `:658` 의 기존 이름 그대로 쓰거나 `appendix` 로 바꾼다.)

**demo 개정** (`:761-764`) — "부록 999조원(F001) 통과 정상" 단언을 뒤집는다:
```python
        # 부록(H1): 태그는 '본문 사용'으로 안 세지만 값 대조는 받는다 — 999조원(F001) 은 FAIL
        appx = good + "\n## 부록\n- F001 전수표 999조원(F001)\n"
        (wp.root / "a.md").write_text(appx, encoding="utf-8")
        ra = verify(wp.root / "a.md", wd)
        assert not ra["ok"] and any("값불일치" in x and "부록" in x for x in ra["failures"]), ra
        # 긍정형 짝: 값이 맞으면 통과하고, 부록의 무태그 수치(환율)는 WARN 으로만 표면화
        appx_ok = good + "\n## 부록\n- F001 전수표 300.9조원(F001) · 환율 1,350원/달러 기준\n"
        (wp.root / "a2.md").write_text(appx_ok, encoding="utf-8")
        ra2 = verify(wp.root / "a2.md", wd)
        assert ra2["ok"] and any("부록무태그" in w for w in ra2["warnings"]), ra2
```

**기존 테스트 영향(모두 통과 유지, 확인만)**: `appendix_bypass_blocked`(부록 `45조원(F001)`·F001 pending → [미확정]·[값불일치] 가 추가되지만 단언은 `무태그` 존재라 OK) · `appendix_forward_bypass`(긍정형 짝 부록 `사내(F001)` 은 수치 없음 → OK) · `duplicate_appendix_marker_blocked`·`empty_body_blocked`(본문공백·마커중복 실패 유지) · E2E 부록 `폐기 0건은 audit 참조` → (b) 이후 `0건` 은 `[부록무태그]` WARN 이고 ok 유지.

**새 테스트** `appendix_value_mismatch_fails` (`appendix_forward_bypass` 아래):
```python
@case
def appendix_value_mismatch_fails():
    """H1: 부록은 무태그만 면제다 — 오태그·미확정·값불일치는 부록에서도 FAIL(본문에서 값불일치 맞은
    수치를 부록 '환산근거'로 옮겨 G3 를 통과하던 우회 차단). 긍정형 짝: 값 일치 + 무태그 수치는 WARN."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        good = "매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n<!-- FACTSHEET:APPENDIX -->\n## 부록\n"
        for bad, tag in (("- 환산근거: 매출 999조원(F001)\n", "값불일치"),
                         ("- 환산근거: 매출 300.9조원(F009)\n", "오태그")):
            (wp.root / "r.md").write_text(good + bad, encoding="utf-8")
            rep = verify_facts.verify(wp.root / "r.md", wd)
            assert not rep["ok"] and any(tag in f and "부록" in f for f in rep["failures"]), (bad, rep)
        db.add_fact({"claim": "시장 45조", "risk": "normal", "status": "pending",
                     "context": {"metric": "market_size", "entity": "x", "geography": "KR", "period": "2030"},
                     "value": {"raw": "45", "unit": "KRW_T"},
                     "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"}})
        (wp.root / "r.md").write_text(good + "- 미확정 병기: 45조원(F002)\n", encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("미확정" in f and "부록" in f for f in rep["failures"]), rep
        (wp.root / "ok.md").write_text(good + "- 환율 1,350원/달러 기준 · 매출 300.9조원(F001)\n", encoding="utf-8")
        rok = verify_facts.verify(wp.root / "ok.md", wd)
        assert rok["ok"] and any("부록무태그" in w for w in rok["warnings"]), rok
```

---

### (b) `verify_facts.py` — 접두 통화기호 + UNIT 확장 + 한글 수사 WARN

**파일·위치**: `UNIT` `:55-56` · `METRIC_NUM` `:62` · `_TIGHT_KRW_UNITS` `:67` · `_plausible` `:70-74` · `UNIT_SCALE` `:131-141` · `_SCALE_TOKEN/_UNIT_TOKEN` `:148-149` · `_resolve_unit` `:152-166` · `_qty` `:199-205` · `check_bound_numbers` 의 수치 수집 `:276` 과 차원 비교 `:292-293`,`:310-317`.

#### (b-1) 패턴(변경 후 전체 — 그대로 붙여 넣을 것)
```python
UNIT = (r"TWh|GWh|MWh|kWh|조원|억원|만원|억달러|백만달러|Nm³/h|Nm3/h|GW|MW|kW|㎿|톤|t/y|USD|KRW"
        # 통화코드(후행 영문 금지: 'EUROPE' 의 EUR 오탐 차단), 질량·면적(kt 는 소문자만 — 'KT'(통신사) 오탐 차단;
        # ha 는 'has/have' 오탐 차단). (?-i:…) 는 re.I 아래서 이 토큰만 대소문자 구분.
        r"|EUR(?![A-Za-z])|JPY(?![A-Za-z])|CNY(?![A-Za-z])|GBP(?![A-Za-z])"
        r"|(?-i:kt|Mt)(?![A-Za-z])|ha(?![A-Za-z])|㎡|배럴"
        r"|billion|million|퍼센트|원|달러|조|억|%"
        # 계수 단위(한국 실사 관행: 특허 1,234건·직원 4,500명·업계 2위·3.2배·120기·100만대·3개사).
        # bare '개' 는 넣지 않는다 — '4개 축'·'6개월' 같은 보고서 구조어 오탐(실측). 전부 _TIGHT 로 숫자에 붙을 때만.
        r"|건|명|개사|기|위|배|대")
METRIC_NUM = re.compile(rf"(?<!제)(?<!\d)({NUM})\s*({PRE})\s*({UNIT})", re.I)   # 변경 없음
# 접두 통화(H2): '$4.5B'·'US$175M'·'€120M'·'₩300조'·'USD 45 billion'. 배수어가 없으면 1 배.
# (?<![\w$€£¥₩]) 는 'US$' 를 '$' 로 다시 잡는 중복과 'S$' 부분매치를 막는다. [BMK] 뒤 영문 금지('Mt' 혼동).
CUR_NUM = re.compile(
    rf"(?<![\w$€£¥₩])(US\$|\$|€|£|¥|₩|USD|EUR|GBP|JPY|CNY|KRW)\s*({NUM})\s*"
    rf"(bn|billion|mn|million|[BMK](?![A-Za-z])|조|억|만)?", re.I)
# 한글 수사(H2 ③): '삼백조원'·'오천억원'·'이십 퍼센트' — 값 파싱은 안 하고 WARN 으로만 표면화.
KO_NUMERAL = re.compile(r"(?<![가-힣])[일이삼사오육칠팔구십백천]+[만억조]?\s*(?:원|달러|퍼센트|%|톤|건|명|기|대|배)")
TAG = re.compile(r"\(F\d{3,}\)")
_TIGHT_KRW_UNITS = {"원", "조", "억", "조원", "억원", "만원", "건", "명", "개사", "기", "위", "배", "대"}
# 약한 계수 단위: 수사 접두(만/천/억)·콤마·값≥100 중 하나가 없으면 사실주장으로 안 본다 —
# '3대 핵심 과제'(수사)·'20~30대 소비자'(연령대)·'3기 신도시'(고유명) 오탐 실측.
_WEAK_COUNT_UNITS = {"대", "기"}
_CUR_DIM = {"$": "USD", "US$": "USD", "USD": "USD", "€": "EUR", "EUR": "EUR", "£": "GBP", "GBP": "GBP",
            "¥": "JPY", "JPY": "JPY", "₩": "KRW", "KRW": "KRW", "CNY": "CNY"}   # ponytail: ¥=JPY 고정(CNY 혼용은 천장)
_CUR_SCALE = {"bn": _p(9), "billion": _p(9), "b": _p(9), "mn": _p(6), "million": _p(6), "m": _p(6),
              "k": _p(3), "조": _p(12), "억": _p(8), "만": _p(4)}
_CURRENCY_DIMS = set(_CUR_DIM.values())
```
(`_p` 는 `:127` 에 이미 있으므로 `_CUR_SCALE` 은 `_p` 정의 **뒤**에 둔다.)

#### (b-2) `_plausible` 변경 후
```python
def _plausible(seg: str, m: re.Match) -> bool:
    unit = m.group(3)
    if unit in _TIGHT_KRW_UNITS and re.search(r"\s", seg[m.end(1):m.start(3)]):
        return False
    if unit in _WEAK_COUNT_UNITS and not m.group(2) and "," not in m.group(1):
        v = _vals(m.group(1))
        if v is not None and v[0] < 100:
            return False
    return True
```
(`_vals` 는 `:176` 정의 — `_plausible` 보다 아래에 있지만 호출 시점엔 모듈 로드가 끝나 있으므로 문제 없음. 신경 쓰이면 `_plausible` 을 `_vals` 아래로 옮긴다.)

#### (b-3) `UNIT_SCALE` 추가 항목 (`:140` `"billion"…` 줄 뒤)
```python
    "eur": ("EUR", Decimal(1)), "jpy": ("JPY", Decimal(1)), "cny": ("CNY", Decimal(1)), "gbp": ("GBP", Decimal(1)),
    "kt": ("TON", _p(3)), "mt": ("TON", _p(6)), "㎡": ("M2", Decimal(1)), "ha": ("M2", _p(4)),
    "배럴": ("BBL", Decimal(1)), "bbl": ("BBL", Decimal(1)),
    "건": ("건", Decimal(1)), "명": ("명", Decimal(1)), "개사": ("개사", Decimal(1)), "개": ("개사", Decimal(1)),
    "기": ("기", Decimal(1)), "위": ("RANK", Decimal(1)), "배": ("X", Decimal(1)), "대": ("대", Decimal(1)),
```
PEM 실전 대장의 unit 상위값 실측: `%`·`건`(89)·`MW`·`USD`·`EUR`·`백만 EUR`·`십억 USD`·`Mt`·`개`·`배` — 위 표로 대부분 정확 매핑되고, 나머지(`정성`·`복합`·`text`)는 기존대로 `[단위미상]` WARN(fail-open).

#### (b-4) `_resolve_unit` — 통화토큰 + 한글 배수어 인식 (변경 후 전체)
```python
_SCALE_TOKEN = re.compile(r"million|billion|thousand", re.I)
_KO_SCALE = {"십억": _p(9), "백만": _p(6), "천": _p(3)}          # 실전 대장 '백만 EUR'·'십억 USD' 실측
_CUR_TOKEN = re.compile(r"USD|EUR|KRW|JPY|CNY|GBP|\$|€|£|¥|₩", re.I)
_UNIT_TOKEN = re.compile(r"TWh|GWh|MWh|kWh|GW|MW|kW|KRW|USD|EUR|JPY|CNY|GBP|%|건|명|개사|기|위|배|대|배럴", re.I)

def _resolve_unit(unit: str) -> tuple[str | None, Decimal]:
    u = (unit or "").strip()
    if not u:
        return None, Decimal(1)
    if u.lower() in UNIT_SCALE:
        return UNIT_SCALE[u.lower()]
    if u in UNIT_SCALE:
        return UNIT_SCALE[u]
    # 'USD_million' / 'EUR million' / '백만 EUR' / '십억 USD': 통화 차원 + 배수. 통화가 없으면 'N'(일반 배수).
    mul = None
    sm = _SCALE_TOKEN.search(u)
    if sm:
        mul = {"million": _p(6), "billion": _p(9), "thousand": _p(3)}[sm.group(0).lower()]
    else:
        for k, v in _KO_SCALE.items():
            if k in u:
                mul = v; break
    if mul is not None:
        cm = _CUR_TOKEN.search(u)
        dim = _CUR_DIM.get(cm.group(0).upper(), "N") if cm else "N"   # '$'.upper()=='$' 라 기호도 그대로 조회됨
        return dim, mul
    m = _UNIT_TOKEN.search(u)
    if m and m.group(0).lower() in UNIT_SCALE:
        return UNIT_SCALE[m.group(0).lower()]
    return None, Decimal(1)


def _dims_compatible(a: str | None, b: str | None) -> bool:
    """None 은 미상(호출측이 WARN), 'N'(bare million/billion) 은 통화 차원과 호환 — 대장 'USD_million' ↔
    본문 '120 million(Fxxx)' 정상 표기를 깨지 않기 위함. ponytail: 통화 종류($ vs €) 불일치는 안 잡음."""
    if a == b:
        return True
    return (a == "N" and b in _CURRENCY_DIMS) or (b == "N" and a in _CURRENCY_DIMS)
```
(`_SCALE_TOKEN` 에 `thousand` 추가는 무해.)

#### (b-5) 본문 수치 수집·차원 비교 — `check_bound_numbers` 변경 후 (해당 부분만)
```python
def _body_nums(seg: str) -> list[tuple[re.Match, str | None, list[Decimal] | None]]:
    """세그먼트의 수치 매치 목록 [(match, 차원, 정규화값)]. 접두 통화(CUR_NUM)가 METRIC_NUM 보다 우선 —
    '₩300조원'·'US$4.5 billion' 이 두 번 잡혀 [무태그] 가 중복되는 것을 막는다."""
    out = []
    spans = []
    for c in CUR_NUM.finditer(seg):
        dim = _CUR_DIM[c.group(1).upper()]                    # 'us$'→'US$', '$'→'$'
        mul = _CUR_SCALE.get((c.group(3) or "").lower(), Decimal(1))
        v = _vals(c.group(2))
        out.append((c, dim, None if v is None else [x * mul for x in v]))
        spans.append((c.start(), c.end()))
    for m in METRIC_NUM.finditer(seg):
        if not _plausible(seg, m):
            continue
        if any(s <= m.start() < e or s < m.end() <= e for s, e in spans):
            continue
        bd, bvals = _qty(m.group(1), m.group(2), m.group(3))
        out.append((m, bd, bvals))
    out.sort(key=lambda t: t[0].start())
    return out
```
`check_bound_numbers` 루프(`:275-283`) 변경 후:
```python
    for seg in split_segments(body):
        for km in KO_NUMERAL.finditer(seg):                      # H2 ③ 한글 수사 WARN
            warnings.append(f"[한글수사] 수치로 해석 못 하는 수사 표기: '{km.group(0)}' (문맥: {seg.strip()[:60]!r})")
        items = _body_nums(seg)
        if not items:
            continue
        nums = [t[0] for t in items]
        tags = list(TAG.finditer(seg))
        bind = _bind_pairs(seg, nums, tags)
        for idx, (m, bd, bvals) in enumerate(items):
            j = bind.get(idx)
            ...  # 이하 기존 로직 그대로. 단 두 군데 차원 비교만 교체:
```
- 폴백(`:292-293`): `(ld is None or bd is None or ld == bd)` → `(ld is None or bd is None or _dims_compatible(ld, bd))`
- 직접 결박(`:313`): `elif ld != bd:` → `elif not _dims_compatible(ld, bd):`
`_bind_pairs` 는 `m.start()/m.end()` 만 쓰므로 `CUR_NUM` 매치가 섞여도 변경 없음. `m.group(0)` 을 메시지에 쓰는 곳도 두 정규식 모두 group(0) 이 전체 표기라 그대로.

#### (b-6) 오탐 회피 — 어떻게 피하는지(구현자가 검증할 표)
이 세션에서 위 패턴 그대로 39케이스 프로브(`scratchpad/regex_probe.py`)를 돌려 **NG 0** 을 확인했다. 구현 후 같은 케이스를 `count_units_are_claims` 테스트로 고정한다.

| 오탐 후보 | 회피 장치 | 결과 |
|---|---|---|
| 연도 `2024년`, 날짜 `2026-08-21`, 월 `12월`, 페이지 `p.45`, 표 `표 3`, 각주 `[12]`, `E001`, `(F012)` | 해당 토큰이 UNIT 에 없음 | 무매치 |
| 표 행번호 `\| 3 \| 건수 \|` | `건` 은 `_TIGHT` → 숫자와 공백·`\|` 있으면 불인정 | 무매치 |
| `2024 has grown`, `2023 KT 매출`, `EUROPE 2024` | `ha(?![A-Za-z])`, `(?-i:kt)`, `EUR(?![A-Za-z])` | 무매치 |
| `제25조` | 기존 `(?<!제)` | 무매치 |
| `3대 핵심 과제`, `20~30대 소비자`, `50대 여성`, `3기 신도시` | `_WEAK_COUNT_UNITS`(접두/콤마/≥100 필요) | 무매치 |
| `6개월`, `4개 축` | bare `개` 미포함 | 무매치 |
| `₩300조원`, `US$4.5 billion` | CUR 우선 + 겹침 제거 | 1회 매치 |

알려진 미검출(허용): `4,500 명`(띄어쓰기) · `500대 기업`(대=top-500 오탐 가능, ≥100 규칙의 대가) · `$` 가 없는 `CAD$240M`(`D$` 는 `(?<![\w$])` 에 막힘 → `$240M` 로 안 잡힘; 캐나다달러는 이번 범위 밖).

#### (b-7) 테스트
- **개정** `numeral_and_energy_units_untagged`(`:522-537`): 긍정형 짝 `총 12건의 프로젝트를 3개사가 진행한다` 는 H2 결정에 따라 **이제 사실주장**이다. 그 두 줄(534-536)을 삭제하고 docstring 의 "'12건'·'3개사' … 오탐하지 않아야" 문장을 지운다. (긍정형 짝은 아래 `count_units_are_claims` 로 이관.)
- **신규** `currency_prefix_untagged_and_mistagged`:
```python
@case
def currency_prefix_untagged_and_mistagged():
    """H2 ①: 접두 통화 표기는 무태그도 오값도 통과하던 사각지대(probe B/C 실측). 긍정형 짝: 값 일치는 통과,
    대장 'USD_million' ↔ 본문 bare 'million' 호환도 유지."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        db.add_fact({"claim": "딜 120M", "risk": "normal", "status": "pending",
                     "context": {"metric": "deal", "entity": "x", "geography": "US", "period": "2025"},
                     "value": {"raw": "120", "unit": "USD_million"},
                     "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"}})
        _confirm(db, wp, "F002")
        for text in ("시장 규모는 $4.5B 에 달한다.\n", "US$4.5 billion 규모다.\n", "€120M 를 투자했다.\n",
                     "₩300조 시장이다.\n", "USD 45 billion 이다.\n"):
            (wp.root / "u.md").write_text(text, encoding="utf-8")
            rep = verify_facts.verify(wp.root / "u.md", wd)
            assert sum("무태그" in f for f in rep["failures"]) == 1, (text, rep)      # 중복 매치 없이 정확히 1건
        (wp.root / "v.md").write_text("딜 규모는 $999M(F002) 이다.\n", encoding="utf-8")
        rv = verify_facts.verify(wp.root / "v.md", wd)
        assert not rv["ok"] and any("값불일치" in f for f in rv["failures"]), rv
        (wp.root / "s.md").write_text("딜 규모는 $120B(F002) 이다.\n", encoding="utf-8")
        rs = verify_facts.verify(wp.root / "s.md", wd)
        assert not rs["ok"] and any("값불일치" in f for f in rs["failures"]), rs
        for ok_text in ("딜 규모는 $120M(F002) 이다.\n\n![c](_captures/F002.png)\n",
                        "딜 규모는 US$120 million(F002) 이다.\n\n![c](_captures/F002.png)\n",
                        "딜 규모는 120 million(F002) 이다.\n\n![c](_captures/F002.png)\n"):
            (wp.root / "ok.md").write_text(ok_text, encoding="utf-8")
            rok = verify_facts.verify(wp.root / "ok.md", wd)
            assert rok["ok"], (ok_text, rok)
```
- **신규** `count_units_are_claims`:
```python
@case
def count_units_are_claims():
    """H2 ②: 건·명·개사·기·위·배·대·kt·Mt·㎡·ha·배럴·EUR 무태그 사실주장 검출. 긍정형 짝: 연도·각주·페이지·
    표 행번호·F태그·연령대·'3대 과제'·'3기 신도시'·'6개월'·'4개 축'·'KT'·'has' 는 오탐하지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        claims = ("직원은 4,500명이다.", "특허 1,234건을 보유한다.", "업계 2위로 부상했다.", "매출이 3.2배 늘었다.",
                  "120기를 설치했다.", "100만대를 판매했다.", "1,200대를 보급했다.", "3개사가 참여한다.",
                  "연 30 kt 생산한다.", "배출량 5 Mt 이다.", "부지 3,000㎡ 규모다.", "3,000만 배럴을 수입했다.",
                  "EUR 120 million 을 조달했다.")
        for text in claims:
            (wp.root / "c.md").write_text(text + "\n", encoding="utf-8")
            rep = verify_facts.verify(wp.root / "c.md", wd)
            assert any("무태그" in f for f in rep["failures"]), (text, rep)
        clean = ("2024년 기준 3부 테마별 본론을 본다. 표 3 과 각주[12], p.45 참조. (F001) 태그. 2026-08-21 접근.\n"
                 "| 3 | 건수 | 12월 건설 |\n\n"
                 "20~30대 소비자와 50대 여성, 3대 핵심 과제, 3기 신도시, 6개월 연장, 4개 축으로 구성.\n"
                 "2023 KT 매출 보고서(EUROPE 2024)는 2024 has grown 이라 썼다. 제25조 규정.\n")
        (wp.root / "ok.md").write_text(clean, encoding="utf-8")
        rok = verify_facts.verify(wp.root / "ok.md", wd)
        assert not any("무태그" in f for f in rok["failures"]), rok
```
- **신규** `korean_numeral_warned`:
```python
@case
def korean_numeral_warned():
    """H2 ③: 한글 수사('삼백조원')는 값 파싱을 못 하므로 FAIL 대신 [한글수사] WARN 으로 표면화한다."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        (wp.root / "k.md").write_text("매출은 삼백조원 규모이며 300.9조원(F001) 이다.\n\n![c](_captures/F001.png)\n",
                                      encoding="utf-8")
        rep = verify_facts.verify(wp.root / "k.md", wd)
        assert rep["ok"] and any("한글수사" in w for w in rep["warnings"]), rep
        (wp.root / "n.md").write_text("삼성전자와 일부 원인을 본다.\n\n![c](_captures/F001.png)\n", encoding="utf-8")
        assert not any("한글수사" in w for w in verify_facts.verify(wp.root / "n.md", wd)["warnings"])
```

---

## 4. 2단계 — 게이트 무결성 3건 (구현 순서: (f) → (e) → (d). (e) 가 (f) 의 validate 를 쓴다)

### (f) `facts_db.py` — lead 재열람 이벤트에 `reread_sha256` 필수

**파일·위치**: `validate_fact` `:53-94`(lead 이벤트 `:79-82`, 강등 `:90-93`) · `add_verify_event` `:236-244` · demo `:336`,`:369`.

**변경 후**
```python
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.I)     # 파일 상단 import re 추가

def _lead_reread_events(fact: dict) -> list[dict]:
    return [e for e in (fact.get("verify_events") or [])
            if e.get("by") == "lead" and e.get("action") == "reread"]

# validate_fact 안, confirmed 블록 (:76-93) 변경 후
    # lead 재열람 이벤트는 재열람 산출물 해시(reread_sha256)가 있어야 한다 — by="lead" 는 누구나 쓸 수 있는
    # 관례라(M2·MEDIUM-2) 원문 미열람 자가신고를 구조적으로 막는다. 상태와 무관하게 형식은 항상 검사.
    for e in _lead_reread_events(fact):
        if not _SHA256_RE.match(str(e.get("reread_sha256") or "")):
            raise ValidationError(f"{fid}: lead reread 이벤트에 reread_sha256(64hex) 없음/형식오류")
    if fact["status"] == "confirmed":
        if not fact.get("evidence_ids"):
            raise ValidationError(f"{fid}: confirmed 인데 evidence_ids 비어있음")
        lead_events = _lead_reread_events(fact)
        if not lead_events:
            raise ValidationError(f"{fid}: confirmed 인데 팀리드(lead) reread verify_event 없음")
        ...(cs / discard_reason 검사 동일)...
        demoted_at = fact.get("demoted_at")
        if demoted_at and max((e.get("at") or "" for e in lead_events)) <= demoted_at:
            raise ValidationError(...)   # 동일 — lead_events 가 이제 'lead reread' 로 좁혀짐

# add_verify_event 변경 후
    def add_verify_event(self, fact_id: str, by: str, action: str, note: str = "", *,
                         reread_sha256: str | None = None) -> None:
        if by == "lead" and action == "reread" and not _SHA256_RE.match(str(reread_sha256 or "")):
            raise ValidationError(f"{fact_id}: lead reread 이벤트는 reread_sha256(재열람 원문 해시 64hex) 필수 — "
                                  "fetch.py get 의 sha256 / 로컬 PDF 해시 / WebFetch verbatim 의 sha256_text")
        facts = self.facts()
        for fr in facts:
            if fr["id"] == fact_id:
                ev = {"by": by, "at": _now(), "action": action, "note": note}
                if reread_sha256:
                    ev["reread_sha256"] = reread_sha256.lower()
                fr.setdefault("verify_events", []).append(ev)
                _write_jsonl_atomic(self.wp.facts, facts)
                return
        raise ValidationError(f"fact 없음: {fact_id}")
```
의미: (1) lead 가 `action="reread"` 가 아닌 이벤트(예: `demote`)는 해시 없이 허용. (2) confirmed 는 **lead reread** 이벤트가 있어야 한다(기존 "lead 이벤트" 에서 좁힘). (3) 스키마 `assets/facts-schema.json` 의 `verify_events` description 에 `reread_sha256` 을 적는다(검증은 코드가 함, 1줄): `"누적 검증 이벤트 [{by, at, action, note, reread_sha256(lead reread 필수)}]"`.

**G3 WARN 결박 검사** — `verify_facts.check_evidence_chain`(`:407-454`) 의 confirmed 루프 끝(증빙 검사 뒤)에 추가:
```python
        # D5: lead 재열람 해시가 이 fact 의 증거(sha256·local 실파일·verbatim) 어느 것과도 안 맞으면 WARN.
        # WebFetch 재열람(바이트 없음)이 남아 있어 FAIL 로는 못 올린다 — 자가신고를 드러내는 용도.
        if f["id"] in used:
            known = set()
            for eid in f.get("evidence_ids", []):
                e = evidence.get(eid) or {}
                if e.get("sha256"): known.add(str(e["sha256"]).lower())
                if e.get("verbatim"): known.add(gates.sha256_text(e["verbatim"]))
                lp = wp.root / e["local"] if e.get("local") else None
                if lp and lp.exists(): known.add(manifest.sha256_file(lp).lower())
            rr = {str(ev.get("reread_sha256") or "").lower()
                  for ev in f.get("verify_events") or [] if ev.get("by") == "lead" and ev.get("action") == "reread"}
            if rr and not (rr & known):
                warnings.append(f"[재열람미결박] {f['id']}: lead reread_sha256 이 evidence sha256/local/verbatim 해시와 불일치")
```
`check_evidence_chain` 은 현재 failures 리스트만 반환한다. **시그니처를 `-> tuple[list[str], list[str]]` 로 바꾸고** 함수 첫머리에 `warnings: list[str] = []` 를 두고 `return failures, warnings` 로 끝낸다. 호출부 `:691` 은 `ec_fail, ec_warn = check_evidence_chain(facts, evidence, wp, used); failures += ec_fail; warnings += ec_warn`.

**깨지는 픽스처와 수정 (전수)** — `add_verify_event(..., "lead", "reread")` 호출 전부에 `reread_sha256=` 추가:

| 파일:줄 | 수정 |
|---|---|
| `tests/test_adversarial.py:438` (`_confirm`) | `db.add_verify_event(fid, "lead", "reread", reread_sha256=_H)` — evidence 의 `_H` 와 같아 `[재열람미결박]` WARN 없음 |
| `tests/test_adversarial.py:166, 219, 262, 677, 693, 710, 743, 791` | 각각 `, reread_sha256=_H` 추가(693·710 은 `_H`/`real_hash` 와 맞춰도 되고 `_H` 로 통일해도 됨 — WARN 은 ok 판정에 무관) |
| `tests/test_e2e.py:83` | `db.add_verify_event(f["id"], "lead", "reread", "원문 표셀 재열람 일치", reread_sha256=hashlib.sha256(("e2e-" + fid).encode()).hexdigest())` (evidence sha 와 동일 → WARN 없음) |
| `scripts/verify_facts.py:740, 774` (demo) | `reread_sha256=_h("F001-E001")` / `_h("F002-E002")` |
| `scripts/facts_db.py:336, 369` (demo) | `reread_sha256=_h("F001-E001")` 두 곳. 336 바로 위에 부정형 1줄 추가: `try: db.add_verify_event("F001", "lead", "reread"); assert False, "reread_sha256 없는 lead 이벤트가 통과됨"` / `except ValidationError: pass` |
| `scripts/gates.py:472` 근처 | (e) 참조 — facts.jsonl 생성 필요 |
| `scripts/make_chart.py:235` (demo raw dict) | `make_chart` 는 `validate_fact` 를 안 부르므로 깨지지 않지만 **일관성 위해** `"reread_sha256": "0"*64` 추가(1줄) |
| `tests/test_adversarial.py:614-641 unvalidated_ledger_row` | 변경 불필요(실패 기대 케이스) |
| `status_regrade_blocked:791` | `_H` 추가 후에도 demoted_at 이후 lead reread 로 재승급 성공 유지 ✓ |

**새 테스트** `lead_event_requires_reread_sha256` / `reread_sha_unbound_warned`:
```python
@case
def lead_event_requires_reread_sha256():
    """M2·MEDIUM-2: by="lead" action="reread" 이벤트는 재열람 산출물 해시가 없으면 add 시점·validate 시점
    모두 거부. 워커 이벤트·lead 의 비-reread 이벤트는 해시 없이 허용(긍정형 짝)."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        db.add_evidence({"fact_id": "F001", "type": "table_cell", "source_url": "https://x", "sha256": _H})
        for bad in (None, "abc", "X" * 64):
            try:
                db.add_verify_event("F001", "lead", "reread", reread_sha256=bad)
                assert False, f"reread_sha256={bad!r} 가 통과됨"
            except ValidationError:
                pass
        db.add_verify_event("F001", "worker-1", "reread")                        # 워커는 해시 없어도 됨
        db.add_verify_event("F001", "lead", "demote", "정의차")                  # lead 비-reread 도 허용
        try:
            db.set_status("F001", "confirmed"); assert False, "lead reread 없이 confirmed 통과"
        except ValidationError:
            pass
        rows = db.facts()
        rows[0]["verify_events"].append({"by": "lead", "at": "2026-08-21T00:00:00", "action": "reread"})  # 손기록
        rows[0]["status"] = "confirmed"
        _write_jsonl_atomic(wp.facts, rows)
        (wp.root / "r.md").write_text("매출 300.9조원(F001).\n", encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("대장무결성" in f and "reread_sha256" in f for f in rep["failures"]), rep


@case
def reread_sha_unbound_warned():
    """D5: reread_sha256 이 그 fact 의 evidence sha256/local/verbatim 어느 해시와도 안 맞으면 [재열람미결박] WARN
    (FAIL 아님 — WebFetch 재열람 경로). 긍정형 짝: evidence sha 와 같으면 WARN 없음."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")                                                 # reread_sha256=_H == evidence sha
        md = "매출 300.9조원(F001).\n\n![c](_captures/F001.png)\n"
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert rep["ok"] and not any("재열람미결박" in w for w in rep["warnings"]), rep
        other = hashlib.sha256(b"elsewhere").hexdigest()
        db.add_verify_event("F001", "lead", "reread", reread_sha256=other)
        rows = db.facts(); rows[0]["verify_events"] = [e for e in rows[0]["verify_events"] if e.get("reread_sha256") != _H]
        _write_jsonl_atomic(wp.facts, rows)
        rep2 = verify_facts.verify(wp.root / "r.md", wd)
        assert rep2["ok"] and any("재열람미결박" in w for w in rep2["warnings"]), rep2
```

---

### (e) `gates.py` — `record_manual("[2]")` 가 대장을 계산하고 영수증을 결박

**파일·위치**: import `:29` · `record_manual` `:294-336`(레코드 생성 `:321-328`) · `successful_receipt` `:200-214` · `require_receipt` `:217-230` · demo `:471-472`.

**`facts_db.py` 에 투영 다이제스트 함수 추가** (`diff_facts` 위):
```python
def confirmed_digest(rows: list[dict]) -> str:
    """[2] 영수증 결박용 투영: confirmed 행의 id·value(raw/unit)·lead reread 이벤트(at, reread_sha256) 만.
    evidence_ids·claim-graph 필드는 [2] 이후 G2·[Bx] 가 정상적으로 바꾸므로 제외(D4)."""
    proj = []
    for r in sorted((r for r in rows if r.get("status") == "confirmed"), key=lambda r: r.get("id", "")):
        v = r.get("value") or {}
        ev = sorted((e.get("at") or "", str(e.get("reread_sha256") or "").lower())
                    for e in _lead_reread_events(r))
        proj.append([r.get("id"), v.get("raw"), v.get("unit"), ev])
    return hashlib.sha256(json.dumps(proj, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()
```
(`import hashlib` 추가.)

**`gates.py` 변경 후**
```python
from facts_db import ValidationError, _read_jsonl, confirmed_digest, load_schema, validate_fact   # :29 아래. 순환 없음(facts_db 는 skill_paths 만 import)

def _check_reverification(wp: WorkPaths) -> dict:
    """[2] 영수증은 기록이 아니라 계산이다(M1·HIGH-H): facts.jsonl 의 confirmed 전건에 lead reread 이벤트
    (+reread_sha256)가 있는지 validate_fact 로 검사하고, 결박용 다이제스트를 돌려준다."""
    if not wp.facts.is_file():
        raise GateError("[2] 재검증 선언인데 facts.jsonl 이 없음")
    rows = _read_jsonl(wp.facts)
    schema = load_schema()
    confirmed = [r for r in rows if r.get("status") == "confirmed"]
    for r in confirmed:
        try:
            validate_fact(r, schema)
        except ValidationError as exc:
            raise GateError(f"[2] 재검증 미완: {exc}") from exc
    return {"facts_db_sha256": sha256_file(wp.facts),
            "confirmed_digest_sha256": confirmed_digest(rows),
            "confirmed_count": len(confirmed)}

# record_manual 의 record 생성(:321-328) 뒤, G0 분기 옆에 추가
    if canonical == "[2]":
        record.update(_check_reverification(wp))

def _receipt_issues(record: dict, wp: WorkPaths) -> list[str]:
    """refs 재해시 + [2] 결박 다이제스트 대조. successful_receipt/require_receipt/check_gate 가 공유."""
    issues = _refs_from_record(record, wp)
    if normalize_gate(record.get("gate", "")) == "[2]":
        stored = record.get("confirmed_digest_sha256")
        if not stored:
            issues.append("[2] 영수증에 confirmed_digest 없음(구버전) — record [2] 재기록 필요")
        elif wp.facts.is_file() and confirmed_digest(_read_jsonl(wp.facts)).lower() != str(stored).lower():
            issues.append("[2] 영수증이 대장 confirmed 집합/값/재열람 이벤트와 불일치 — 재검증 후 record [2] 재기록")
    return issues
```
그리고 `successful_receipt`(`:212`)·`require_receipt`(`:227`) 의 `_refs_from_record(record, wp)` 호출을 `_receipt_issues(record, wp)` 로 바꾼다(**2곳만**). `check_gate`(`:255`) 의 "현재 게이트 자기 영수증" 검사는 **`_refs_from_record` 그대로 둔다** — 여기에 다이제스트를 넣으면 대장이 바뀐 뒤 `record [2]` 재기록 자체가 `check_gate("[2]")` 의 자기 영수증 드리프트에 막혀 영원히 재기록할 수 없게 된다. 드리프트는 `check G3`(선행 `[2]` 를 `require_receipt` 로 검사)에서 잡힌다. `record_script_result` 는 변경 없음.

**demo 수정** (`gates.py:471-472`): `record_script_result(wp, "G1", …)` 앞에 `wp.facts.write_text("", encoding="utf-8")` 한 줄(대장 파일 없으면 fail-closed 라 데모가 깨진다). `g5_receipt_owned_by_manifest_verify` 는 이미 빈 `facts.jsonl` 을 만들고 `[2]` 를 기록하므로(confirmed 0건 = 다이제스트 빈 리스트) 그대로 통과.

**G1 영수증 삭제는 이번 배치 제외 — 이유(범위 통제)**: 삭제하면 `PREREQUISITES` 3곳·`MANUAL/SCRIPT_OWNED` 설명·`owned_gate_cli_forgery_blocked` 긍정형 짝·`gates.demo`·`g5_receipt…`·`verify_facts` main 의 `check_gate("G3")` 선행 목록·SKILL.md `:95`·verification-gates.md `:69`·README 가 같이 움직여야 하고, 그중 SKILL.md/README 가 이번 배치 금지 파일이다. 실질 검사는 이미 G3 `check_ledger_integrity` 가 하므로 G1 영수증이 남아 있어도 **위조로 얻는 것이 없다**(G3 가 전행 재검증). 6단계(과잉 제거)에서 문서와 함께 뺀다.

**새 테스트** `receipt2_requires_lead_reread_and_binds_digest`:
```python
@case
def receipt2_requires_lead_reread_and_binds_digest():
    """M1·HIGH-H: record [2] 는 confirmed 전건 lead reread 검사 후에만 기록되고, 이후 confirmed 집합이
    바뀌면 영수증이 무효(G3 선행 실패) → 재기록해야 한다. G2 의 evidence 추가는 무효화하지 않는다(긍정형 짝)."""
    import gates
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        (wp.audit).mkdir(parents=True, exist_ok=True)
        (wp.audit / "research-plan.md").write_text("# plan\n", encoding="utf-8")
        gates.record_manual(wp, "G0", "approved")
        gates.record_script_result(wp, "G1", 0, "join")
        rows = db.facts(); rows[0].update({"status": "confirmed", "evidence_ids": ["E001"]})   # lead 이벤트 없는 손기록
        _write_jsonl_atomic(wp.facts, rows)
        try:
            gates.record_manual(wp, "[2]", "hand"); assert False, "lead 이벤트 없는 confirmed 가 [2] 를 통과"
        except gates.GateError:
            pass
        rows[0].update({"status": "pending", "evidence_ids": []}); _write_jsonl_atomic(wp.facts, rows)
        _confirm(db, wp, "F001")
        rec = gates.record_manual(wp, "[2]", "lead reread")
        assert rec["confirmed_count"] == 1 and rec["confirmed_digest_sha256"] and rec["facts_db_sha256"]
        assert gates.check_gate(wp, "G3")["ok"], gates.check_gate(wp, "G3")
        db.add_evidence({"fact_id": "F001", "type": "text_quote", "verbatim": "추가 증거",
                         "source_url": "https://y", "sha256": _H})                      # G2 경로: 무효화 안 됨
        assert gates.check_gate(wp, "G3")["ok"]
        db.add_fact({"claim": "x", "risk": "normal", "status": "pending",
                     "context": {"metric": "m", "entity": "e", "geography": "KR", "period": "2025"},
                     "value": {"raw": "1", "unit": "건"},
                     "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"}})
        _confirm(db, wp, "F002")                                                          # confirmed 집합 변경
        chk = gates.check_gate(wp, "G3")
        assert not chk["ok"] and any("[2]" in i and "재기록" in i for i in chk["issues"]), chk
        gates.record_manual(wp, "[2]", "lead reread again")
        assert gates.check_gate(wp, "G3")["ok"]
        # 원장 없는 작업폴더에서 [2] 는 fail-closed
        wd2 = resolve_work_dir("대장없음", base=td); wp2 = WorkPaths(wd2)
        (wp2.audit).mkdir(parents=True, exist_ok=True); (wp2.audit / "research-plan.md").write_text("# p\n", encoding="utf-8")
        gates.record_manual(wp2, "G0", "ok"); gates.record_script_result(wp2, "G1", 0, "join")
        try:
            gates.record_manual(wp2, "[2]", "hand"); assert False, "facts.jsonl 없이 [2] 기록됨"
        except gates.GateError:
            pass
```

---

### (d) `verify_facts.py:385-399` — [Bx] ①② FAIL 승격(본문 사용 high-risk 한정)

**변경 전** (`:385-399`, 전부 warning) → **변경 후**:
```python
        # [Bx] claim-graph 긍정 요건. risk=high ∧ confirmed ∧ 본문 사용이면 ①독립그룹≥2 ②반박검색은 FAIL —
        # 시장규모·CAGR·딜규모가 1출처로 confirmed 돼 "조사마다 다른 숫자"가 되는 것을 막는 유일한 기계 게이트
        # (H4·HIGH-G). ③기본소스 ④시간증거는 WARN 유지. 본문 미사용 high-risk 는 네 요건 모두 WARN.
        # 기권은 status=disputed 로 남기는 길이 이미 열려 있다(실전 마찰은 "정직하게 disputed" 뿐).
        # 실전 대장(PEM 620건·KERI 69건)은 이 필드가 전부 비어 있으나 해당 폴더는 이미 봉인·납품됐고 현재
        # G3 재실행 자체가 스냅샷유실/해시불일치로 FAIL 상태(2026-08-21 실측) — 회귀가 아니라 신규 조사부터 적용.
        if f.get("risk") == "high" and f.get("status") == "confirmed":
            hard, soft = [], []
            groups = set(g for g in (f.get("independent_groups") or []) if g)
            if len(groups) < 2:
                hard.append("독립 관찰그룹 부족(≥2)")
            if not (f.get("counter_search") or {}).get("query"):
                hard.append("반박검색 기록 없음(counter_search.query)")
            if not f.get("primary_source_ref"):
                soft.append("기본소스 참조 없음")
            if not (f.get("observed_at") or f.get("valid_at")):
                soft.append("시간증거 없음")
            if fid in used and hard:
                failures.append(f"[반박게이트] {fid}: " + "·".join(hard) + " — disputed 로 내리거나 요건 충족 후 재검증")
            elif hard:
                warnings.append(f"[반박게이트] {fid}(본문 미사용): " + "·".join(hard))
            if soft:
                warnings.append(f"[반박게이트] {fid}: " + "·".join(soft))
```
`set(...)` 으로 `["dart","dart"]` 같은 중복 라벨 손기입을 막는다. `independent_groups` 를 `evidence.observer_group` 에서 유도·교차검증하는 것(HIGH-G 보강)은 이번 배치 제외 — WARN 한 줄도 넣지 않는다(범위).

**기존 테스트 개정** — `claim_graph_fields_warned`(`:962-990`) 는 "승격 금지" 를 고정하고 있으므로 **이름과 단언을 바꾼다** (`claim_graph_high_risk_used_fails` 로 교체):
```python
@case
def claim_graph_high_risk_used_fails():
    """H4·HIGH-G: risk=high confirmed fact 가 본문에 쓰였는데 ①독립그룹≥2 ②반박검색이 없으면 [반박게이트] FAIL.
    ③기본소스 ④시간증거는 WARN. 본문 미사용 high-risk 는 WARN 만. 중복 라벨(['dart','dart'])은 1그룹.
    긍정형 짝: ①② 채우면 ok(③④ WARN 잔존), 네 필드 다 채우면 WARN 도 사라짐."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)          # F001 risk=high
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")       # _confirm 이 ①② 기본값을 채우므로 여기서 비워 결핍 상태로 시작
        rows = db.facts(); fr = rows[0]
        fr.update({"independent_groups": [], "counter_search": None}); _write_jsonl_atomic(wp.facts, rows)
        md = "매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n"
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("[반박게이트]" in f and "독립" in f and "반박검색" in f for f in rep["failures"]), rep

        fr.update({"independent_groups": ["dart", "dart"],
                   "counter_search": {"query": "q", "result": "없음", "found_stronger_refutation": False}})
        _write_jsonl_atomic(wp.facts, rows)
        rep_dup = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep_dup["ok"] and any("독립" in f for f in rep_dup["failures"]), rep_dup

        fr["independent_groups"] = ["dart", "irstatement"]; _write_jsonl_atomic(wp.facts, rows)
        rep2 = verify_facts.verify(wp.root / "r.md", wd)
        assert rep2["ok"] and any("반박게이트" in w and "기본소스" in w for w in rep2["warnings"]), rep2

        fr.update({"primary_source_ref": "E001", "observed_at": "2026-07-22", "valid_at": "2025-03"})
        _write_jsonl_atomic(wp.facts, rows)
        rep3 = verify_facts.verify(wp.root / "r.md", wd)
        assert rep3["ok"] and not any("반박게이트" in w for w in rep3["warnings"]), rep3

        # 본문 미사용 high-risk: WARN 만
        (wp.root / "u.md").write_text("본문에 F001 없음.\n\n![c](_captures/F001.png)\n", encoding="utf-8")
        fr.update({"independent_groups": [], "counter_search": None}); _write_jsonl_atomic(wp.facts, rows)
        ru = verify_facts.verify(wp.root / "u.md", wd)
        assert ru["ok"] and any("본문 미사용" in w for w in ru["warnings"]), ru
```
E2E 는 F001(high, 본문 사용)에 `independent_groups=["dart","irstatement"]`·`counter_search` 를 이미 넣고 있어(`:84-92`) 그대로 통과. `_base_db` 가 만드는 F001 은 `risk="high"` 라 **F001 을 본문에 쓰는 모든 기존 테스트의 긍정형 짝이 새 FAIL 을 맞는다** — 대응: `_confirm()` 안에서 claim-graph ①② 를 기본으로 채운다:
```python
def _confirm(db, wp, fid, with_capture=True):
    ...
    db.add_verify_event(fid, "lead", "reread", reread_sha256=_H)
    rows = db.facts(); fr = next(r for r in rows if r["id"] == fid)
    if fr.get("risk") == "high":      # (d) 이후 high-risk 본문 사용은 ①② 필수 — 긍정형 짝 픽스처 기본값
        fr.setdefault("independent_groups", ["dart", "irstatement"])
        fr.setdefault("counter_search", {"query": "정정 검색", "result": "없음", "found_stronger_refutation": False})
        _write_jsonl_atomic(wp.facts, rows)
    db.set_status(fid, "confirmed")
```
`_confirm` 을 안 쓰고 직접 confirmed 를 만드는 케이스 중 **F001 을 본문에 쓰고 ok=True 를 기대하는 것**은 없다(`:166,219,262,677,693,710,743,791` 전부 실패 기대 또는 `fake_evidence_hash` 긍정형 짝처럼 "특정 실패 없음" 만 단언). 단 `fake_evidence_hash` 긍정형 짝(`:700-716`)은 `rep["failures"]` 에 이제 `[반박게이트]` 가 섞이지만 단언이 `해시형식/해시불일치 없음` 이라 통과. `verify_facts.demo` 의 F001 은 `risk="normal"` 이라 영향 없음. `claim_graph_high_risk_used_fails` 는 위 코드처럼 `_confirm` 직후 두 필드를 비워 결핍 상태로 시작한다.

---

## 5. 실전 대장 "76건" 주석의 함의 — 기존 research 폴더 회귀

- 주석(`verify_facts.py:386-387`)의 76건은 과거 대장이고, 지금 남아 있는 실전 폴더는 PEM(620 confirmed/378 high/본문 사용 199)·KERI(69/22/22)·영수증OCR(12/2/2). **셋 모두 `independent_groups`·`counter_search`·`reread_sha256` 0건.**
- 그러나 PEM 폴더는 (d)·(f) 와 무관하게 **오늘 G3 재실행이 이미 FAIL** 이다(§0 실측: 스냅샷유실 289·해시불일치 191). 즉 "통과하던 폴더가 이 변경으로 떨어지는" 회귀는 없다. 이 폴더들은 납품 완료된 봉인 산출물이며, 재실행 시 원장 영수증도 `[2]` 다이제스트 부재로 `require_receipt` 가 "구버전 — 재기록" 을 낸다(의도된 fail-closed).
- **마이그레이션 스크립트는 만들지 않는다.** 재검증 없이 필드를 채워 넣는 것이 바로 HIGH-G 가 지적한 손기입이다. 재조사가 필요하면 `[2]`(reread_sha256)·`[Bx]` 를 실제로 수행한 뒤 `record [2]` 재기록 → G3.
- 주석은 (d) 코드블록의 문구로 교체한다(76건 언급 삭제).

## 6. 새 적대 테스트 요약(9건 — 항목당 1건 이상) · 기대 카운트

| 테스트 | 항목 | 기대 |
|---|---|---|
| `manifest_image_swap` | (c) | 변조 `changed`, 미봉인 IMAGES.md `new` |
| `appendix_value_mismatch_fails` | (a) | 부록 값불일치·오태그·미확정 FAIL(메시지에 `부록`), 긍정형 ok + `[부록무태그]` WARN |
| `currency_prefix_untagged_and_mistagged` | (b) | 5표기 각 정확히 무태그 1건, `$999M`·`$120B` 값불일치, `$120M`/`US$120 million`/`120 million` ok |
| `count_units_are_claims` | (b) | 13 사실주장 전부 무태그, 오탐 문단 무태그 0 |
| `korean_numeral_warned` | (b) | `[한글수사]` WARN·ok, 비수사 문장 WARN 없음 |
| `claim_graph_high_risk_used_fails` (기존 `claim_graph_fields_warned` 교체) | (d) | 본문 사용 ①② 결핍 FAIL, 중복 라벨 FAIL, ①② 충족 ok+③④ WARN, 전부 충족 WARN 0, 미사용 WARN |
| `receipt2_requires_lead_reread_and_binds_digest` | (e) | lead 없는 confirmed → GateError, 정상 기록에 다이제스트, evidence 추가는 유지, confirmed 변경 → G3 선행 실패 "재기록", 대장 없음 GateError |
| `lead_event_requires_reread_sha256` | (f) | None/짧은/비hex 거부, 워커·lead demote 허용, 손기록 행 → `[대장무결성]…reread_sha256` |
| `reread_sha_unbound_warned` | (f) | 불일치 → `[재열람미결박]` WARN·ok 유지, 일치 → WARN 없음 |

기존 개정 2건: `numeral_and_energy_units_untagged`(긍정형 짝 2줄 삭제) · `claim_graph_fields_warned` → 교체. **기대 합계: 60 − 0 + 8 = 68/68** (교체 1건은 수 불변).

## 7. 구현 순서(커밋 단위)와 검증 명령

순서: ① (c) → ② (a) → ③ (b) → ④ (f) → ⑤ (e) → ⑥ (d) → ⑦ 문서 4줄. 각 단계 뒤 아래 전부 통과시킨 뒤 다음 단계로.

```bash
cd F:/Claude/skills/market-deep-research/codes/market-deep-research
export PYTHONUTF8=1                                   # cp949 콘솔 디코드 오류 방지(실측)
python scripts/verify_facts.py demo                   # (a)(b)(d)(f) 데모 개정 포함 'verify_facts demo OK'
python scripts/gates.py demo                          # (e) — JSON 에 owned_gate_cli_blocked: true
python scripts/facts_db.py demo                       # (f) — 'facts_db demo OK'
python scripts/manifest.py demo                       # (c)
python scripts/make_chart.py demo                     # (f) 데모 1줄
python scripts/harvest_images.py demo                 # 무변경이지만 _images 계약 확인
python tests/test_adversarial.py                      # 68/68 검출 성공
python tests/test_e2e.py                              # 'E2E OK — facts=2 evidence=2 … G3 PASS, 무결성 OK'
```
추가 스모크(선택): `python tests/../scripts/skill_paths.py demo`. **`python scripts/install.py` 는 절대 실행하지 않는다**(설치본 mirror-sync; 동기화는 사용자가 별도 결정).

## 8. 가장 위험한 변경 1개와 그다음

1. **(d) [Bx] ①② FAIL 승격** — 파이프라인 차단 효과가 가장 크다. 실전 기준 본문 사용 high-risk 199/199 가 미충족이었다. 이제 시장규모·CAGR·딜규모를 본문에 쓰려면 독립그룹 2개 + 반박검색 1회가 없으면 **반드시 `disputed` 로 내려 7부 상충에 병기하거나 본문에서 뺀다.** 우회 유인(라벨 손기입)은 `set()` 중복 차단만 있고 observer_group 교차검증은 다음 배치 — 리뷰어가 알고 받아들인 천장.
2. (b) 단위 확장 — 오탐은 프로브로 0 을 확인했지만 실전 보고서 문장은 더 다양하다. FAIL 이 늘면 문장을 태그하거나 수치를 빼는 것이 정답이지 UNIT 을 줄이는 것이 아니다. 단 `대·기` 의 ≥100 규칙처럼 **검출을 포기한 곳**은 §3(b-6) 표에 적어 두었다.
3. (e)(f) 는 fail-closed 추가라 기존 흐름에서 "한 번 더 기록/인자 하나 추가" 비용만 생긴다.

## 9. 문서 후속(이번 배치 금지 파일 — 다음 PR)

- `SKILL.md:46-47` `[2]`·`[Bx]` 한 줄 요약에 "lead 이벤트 `reread_sha256` 필수 / ①② 본문 사용 시 FAIL" · `:98-104` [2] 절에 `add_verify_event(by="lead", reread_sha256=<fetch.py get 의 sha256>)` 와 "`record [2]` 는 confirmed 전건 검사 후 기록, 대장 confirmed 집합 변경 시 재기록" · `:109-111` [Bx] 통과조건에 FAIL/WARN 구분 · `:133-137` G3 에 부록 검사·접두통화·계수단위 · `:157` 영수증 커버리지에 `[2]` 다이제스트 결박.
- `README.md` G3 설명(부록 무검사 → 무태그만 면제) · 영수증 설명.
- 이번 배치에서 **허용된 문서 수정(4줄)**: `references/verification-gates.md:23`(lead reread 이벤트 `reread_sha256` 필수) · `:25-27`(①② 는 본문 사용 high-risk 에 한해 FAIL, ③④ WARN) · `:38-41` G3 한 줄(부록: 무태그만 면제·접두 통화·계수 단위) · `:67-69`(`[2]` 영수증은 confirmed 집합 다이제스트에 결박, 대장 변경 시 재기록).
- `verify_facts.py` 모듈 docstring `:1-25` 를 변경 내용에 맞게 갱신(부록·접두 통화·[Bx]·재열람미결박).
