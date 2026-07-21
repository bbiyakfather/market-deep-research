# extract-recipes — 증거유형 6종 추출 지침 · locator 규약 · PDF 파싱

fetch.py가 확보한 깨끗한 본문에서 조사원(LLM=extractor)이 evidence를 뽑아내는 규범. **추출은 사람(LLM)이, 수집은 도구(fetch)가** 한다 — fetch가 준 텍스트/PDF 안에서 값을 찾아 정확한 locator를 다는 것이 추출의 전부다. 원문에 없는 값을 만들지 않는다.

---

## 1. 증거유형 6종과 locator 규약

각 evidence는 `type` 하나와, 그 type에 맞는 **locator**(원문에서 그 값을 다시 찾아갈 좌표)를 가진다. locator 형식은 아래로 고정한다(facts-schema.json·agent-briefs.md와 1:1). 재현성의 핵심이므로 형식을 바꾸지 않는다.

### 1.1 `text_quote` — 본문 문장 인용
- locator: `{"page": <PDF 페이지>}` 또는 `{"selector": "<CSS/텍스트 셀렉터>"}` (웹)
- **`verbatim` 필수**: 원문 문장을 **글자 그대로**(생략·수정·번역 없이) 담는다. 수치는 원문 표기 그대로.
- 지침: 값이 서술 문장에 녹아 있을 때 사용. 문장 전체를 인용하되 앞뒤 맥락이 값의 정의를 바꾸면 그 절도 포함.

### 1.2 `table_cell` — 표 셀
- locator: `{"page": <페이지>, "row": <행 인덱스>, "col": <열 인덱스>}`
- row/col은 fitz `find_tables()`가 반환하는 표 격자 기준(머리행 포함 여부는 §2에서 통일). 병합셀·다단 머리행은 §2 주의.
- 지침: 재무제표·통계표 등 격자 데이터는 반드시 이 유형. 셀 값이 어느 행·열 라벨에 걸리는지 `verbatim`에 "행라벨 × 열라벨 = 값"으로 함께 적으면 오귀속 검증이 쉽다(선택).

### 1.3 `chart` — 차트/그래프 값
- locator: `{"page": <페이지>, "series": "<계열명>", "point": "<축 좌표/라벨>"}`
- 지침: 차트에 **데이터 레이블(숫자)이 찍혀 있을 때만** 값으로 채택. 눈금 사이 육안 보간은 추정이므로 금지(agent-briefs 철칙 §1). 레이블 없는 차트는 값이 아니라 "경향" 서술로만 인사이트에 쓴다.

### 1.4 `api_response` — 구조화 API 응답
- locator: `{"endpoint": "<URL>", "params": {...}, "json_path": "<경로>", "response_sha256": "<응답 해시>"}`
- 지침: KOSIS·OpenDART·KIPRIS·SEC EDGAR·arXiv 등 JSON/XML API. 응답 전문을 저장하고 `response_sha256`로 고정. `json_path`(예: `results[0].revenue`)로 값 위치를 못 박는다. 재조사 시 동일 endpoint+params로 재현 가능해야 한다.

### 1.5 `negative_search` — 부재의 증거
- locator: `{"query": "<검색/조회 문구>", "scope": "<조사 범위>", "as_of": "<조회 시점>"}`
- 지침: "X에 대한 공시/기록이 **없다**"는 주장은 이 유형으로만 낸다. 어디서(scope) 언제(as_of) 무엇으로(query) 찾았는지 명시. "못 찾음 = 없음"이 아니므로 scope를 정직하게 좁힌다(예: "DART 정기공시 2020~2025 한정").

### 1.6 `calculation` — 파생 계산값
- locator: `{"formula": "<식>", "inputs": [<입력 evidence 참조>]}`
- 지침: 원문 값들로부터 **투명하게 계산**한 값(합계·비율·성장률 등). `inputs`는 계산에 쓴 다른 evidence의 ID. 식을 명시해 재검산 가능해야 한다. 환산(통화/단위)은 기본 OFF이며, ON일 때만 verification-gates.md의 Decimal 검산 규약을 따른다. 임의 추정은 계산이 아니다 — 입력이 모두 원문 근거여야 한다.

---

## 2. PDF 파싱 (fitz)

1. **표**: `page.find_tables()` → `table.extract()`로 격자 회수. row/col 인덱스는 이 격자 기준으로 고정한다. 다단 머리행·병합셀이면 실제 값 셀의 좌표를 쓰고, 라벨을 `verbatim`에 병기해 오귀속을 막는다.
2. **숫자 표기 변형에 강건하게**: 같은 값이 원문·추출에서 다르게 보일 수 있다 — 천단위 쉼표(`1,234`), 공백/개행 삽입(`1 234`, 줄바꿈), **NBSP(U+00A0)**, 전각 숫자, 괄호 음수(`(1,234)`). 값 대조·캡처 검색 시 이 변형들을 정규화해 비교한다(단, `value.raw`에는 원문 표기를 보존).
3. **스캔 PDF(이미지)**: `find_tables()`·텍스트 추출이 비면 스캔본이다. OCR을 신뢰 추출로 쓰지 않는다 — **페이지 이미지 육안 fallback**(preview_pdf.py로 렌더 → 사람이 값 확인)으로 처리하고, 자동 추출 실패 상태를 남긴다.
4. 파싱한 PDF는 `_sources/`에 원본 그대로 보존(SHA-256). 캡처(capture_pdf.py)가 이 파일을 재사용한다.

---

## 3. LLM = extractor 원칙 (재확인)

- LLM(조사원)은 fetch가 준 텍스트/PDF **안에서만** 값을 찾는다. 배경지식으로 값을 "채우지" 않는다.
- 값을 못 찾으면 evidence를 만들지 않는다(폐기). 찾은 값은 정확한 locator로 좌표를 박는다.
- 추출 프롬프트에는 항상 원문 불신뢰 경고(agent-briefs 철칙 §4)를 포함한다.

---

## 4. 특수소스 recipe — 문서로만, v1 미배선

아래 소스들은 **참고용 recipe로만** 기록한다. v1에서는 `search.py`/`fetch.py`에 **배선하지 않는다**(범위 제외). 필요 시 조사원이 내장 도구로 개별 접근하되, 정식 evidence로 등재하려면 fetch 사다리를 거쳐 원문 URL·해시를 확보해야 한다.

| 소스 | 접근 방식(문서) | evidence type 후보 | 비고 |
|---|---|---|---|
| Semantic Scholar | Graph API(논문 메타·인용수) | `api_response` | v1 미배선. arXiv로 대체. |
| CrossRef | REST API(DOI 메타) | `api_response` | v1 미배선. |
| GitHub | REST/Search API(레포·릴리스) | `api_response` | v1 미배선. UGC → 등급 보수적. |
| Hacker News | Firebase API / Algolia | `api_response` | v1 미배선. UGC. |
| Reddit | JSON 엔드포인트 | `text_quote` | v1 미배선. UGC, 오귀속 주의. |
| X(Twitter) | 비공식/제약 큼 | `text_quote` | v1 미배선. 우회 금지 정책. |
| yt-dlp | 자막/메타 추출 | `text_quote` | **선택 의존성**(preflight optional). v1 미배선. |

이 표의 어떤 소스도 v1 파이프라인의 자동 계층에 넣지 않는다. "문서로만" 원칙을 지킨다.
