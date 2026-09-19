# SPEC — 배치 2A: 수집·렌더 파이프라인 방어 강화 (적대적 리뷰 N02·N03·N14·N15·N16·N22·K07)

REASONING: xhigh

## 배경

우리 스킬 저장소 `F:/Claude/skills/market-deep-research/codes/market-deep-research/` 의
자체 수집·렌더 스크립트에 대한 품질보증 리뷰
`F:/Claude/skills/market-deep-research/_planning/council-2026-09-05/review-astra-2.md` 가
방어 공백을 찾았다(해당 결함 절 N02·N03·N14·N15·N16·N22·K07 을 먼저 읽어라 — 재현 절차와
파일:라인 근거가 있다). 이것은 **자사 도구의 방어 강화**다: 우리 스크립트가 신뢰할 수 없는
웹 콘텐츠를 다루므로, 스크립트 자신이 내부망 접근·원격 코드 반영·오판 성공을 하지 않도록
닫는다. 이 7건만 고친다. 다른 결함(N04~N13·N17~N21·K06)은 이번 범위가 아니다.

직전 커밋 5a058ac(P0 수정) 기준 워킹트리는 깨끗하다. 커밋 금지 — diff 로 남겨라.

## 수정 항목

### N02 [치명] 렌더 오프라인 보장
- `render_pdf.py`: pandoc 단계에서 raw HTML 을 본문에 반영하지 않게(원고 `<script>` 등
  active HTML 제거/이스케이프 — pandoc 옵션 `-f gfm-raw_html` 류 우선 검토), 원격 리소스
  로드 차단(로컬 파일·data URI 만 허용 — 렌더 전에 원고의 이미지 참조를 검사해 외부 URL 이
  있으면 exit 1 로 명확히 실패). Chrome 단계: `--no-sandbox` 제거 가능 여부 확인(Windows
  기본 Chrome 은 샌드박스 동작 — 실패 시에만 명시 플래그 폴백), 오프라인 강제 옵션, 두
  subprocess 에 timeout(기본 180s).
- `verify_facts.py` 의 도판 실재 검사에서 외부 URL/data URI 무조건 통과 분기(리뷰 근거
  `verify_facts.py:663` 부근)를 제거 — 본문 이미지 참조는 작업폴더 내부 파일만 인정.

### N03 [치명] 이미지 수집·검색의 요청 경계 통일
- `harvest_images.py`·`search.py` 가 `fetch.py` 의 공통 가드(스킴·호스트·사설/루프백 차단)
  를 재사용하게 통일(이중구현 금지). redirect 는 자동 추종 금지 — 홉마다 같은 가드로 검사
  후 진행(최대 5홉). 다운로드는 스트리밍으로 크기 상한 검사(전량 수신 후 판정 금지).
- `fetch.py`: 연결 전 IP 검사(사전 차단)로 이동 가능하면 이동, 불가하면 현재 사후 검사
  유지하되 한계를 코드 주석·`references/source-ladder.md` 한 줄로 명시. proxy 환경변수
  존재 시 검사 생략하는 분기(리뷰 `fetch.py:237` 부근)는 제거 — proxy 여부와 무관하게 검사.

### N14 [중대] 재구성 이미지 경로 경계
- `capture_web.py`: 저장 전 `resolve()` 한 최종 목적지가 `_captures/_reconstructed/` 내부
  인지 검사(문자열 조각 검사 대신). 이탈 시 거부.

### N15 [중대] PDF fast path 의 HTTP 상태 무시
- `fetch.py`: PDF/HTML 분기 **전에** HTTP 성공 상태(2xx) 공통 검사. 비 2xx 는 포맷이
  PDF 여도 실패로 기록.

### N16 [중대] 무관 RSS 전체 피드를 원문 확보로 승격
- `fetch.py` RSS 계층: 요청 URL/GUID/제목과 대응하는 entry 를 추출해 일치할 때만 ok.
  미일치 피드는 `partial`(탐색 자료) 로 기록하고 사다리를 계속 탄다.

### N22 [경미] 실패 집계 소스 불일치
- `source_index.py`: 존재하지 않는 `fetch-failures.jsonl` 대신 fetch 가 실제로 쓰는
  `audit/fetch-log.jsonl` 에서 URL 별 최종 확보 상태로 실패를 집계. 시도 실패 수와 최종
  실패 수 구분. sources.md 에 ok/partial 상태 열 표시(N20 의 provenance 재설계는 범위 밖,
  상태 표시만).

### K07 [경미] fetch CLI stdout 절단
- `fetch.py` CLI: stdout JSON 은 완전한 구조로 유지 — 긴 trace 는 배열 항목 단위 축약
  또는 파일(`audit/`) 로 내보내고 stdout 에는 경로만. `sha256`·`local` 키는 항상 보존.

## 제약
- 기존 테스트 154개 + 데모 3종 통과 유지. 신규 외부 의존성 금지(curl_cffi·trafilatura 등
  기존 SOFT 의존성 활용은 가능). 이중구현 금지 — 가드·상수는 fetch.py 한 곳.
- 각 항목에 부정 회귀 테스트 1개 이상(로컬 loopback 서버 fixture 는 tests 안에서만,
  외부 네트워크 접근 없는 테스트로). 리뷰의 재현 절차를 테스트로 옮겨라.
- 기존 우회 사다리의 **정상 기능**(모바일 지문·RSS 로 실제 원문 확보)은 유지 — 목적은
  오판 성공과 경계 이탈 차단이지 수집력 저하가 아니다. 회귀로 정상 케이스도 고정하라.
- Windows·utf-8 패턴 유지. 커밋 금지.

## 검증 (완료 전 전부, out 파일에 기록)
```
cd F:/Claude/skills/market-deep-research/codes/market-deep-research
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
PYTHONIOENCODING=utf-8 python scripts/gates.py demo
python scripts/preflight.py
```

## 완료 보고
out 파일에: 변경 파일 / 항목별 반영 방식 1줄 + 재현 차단 근거 / 테스트 결과 / 남긴 한계 /
요약 15줄. 질문하지 말고 가정을 적고 진행, 막히면 막힌 곳을 적고 종료. stdout 은 요약만.
