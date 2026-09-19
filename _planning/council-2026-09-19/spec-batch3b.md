이 작업은 전용 구현 레인에서 호출 시 지정된 모델·reasoning effort 로 실행된다. 그 선택은 의도된 것이며 아무것도 대체되지 않았다.
사용자/프로젝트 지침 파일이 다른 오케스트레이션 흐름을 기본으로 요구해도, 이 레인은 그 기본에서 명시적으로 opt-out 한 것으로 보고 진행한다. 그 파일의 다른 지침은 그대로 적용한다.
질문하지 말고 가정을 적고 진행, 막히면 막힌 곳을 적고 종료, 결과는 파일로·stdout 은 요약.

# 배치 3B — 렌더 입력 이미지 봉인 (R02)

## 1. 목표
3차 적대적 리뷰(`F:/Claude/skills/market-deep-research/_planning/council-2026-09-19/review-astra-pr18-adversarial.md`)의 R02 를 닫는다.
현재 `report.md` 가 참조하는 로컬 이미지가 `assets/`·`_images/`·`_captures/` 밖(예: 작업폴더 바로 아래 `chart.png`)에 있으면 G3 는 통과하지만
`manifest` 봉인 대상에 들어가지 않아, G3 뒤에 이미지 내용을 바꿔도 `manifest.verify` 가 ok 를 낸다.
완료 기준: **원고가 참조하는 모든 로컬 이미지가 G3 기준선 manifest 에 들어가고**, G3 뒤 그 파일을 바꾸면 `manifest.py verify` 가 실패하며, 기존 테스트 431개가 전부 통과한다.

## 2. 파일
작업 디렉터리 기준 `codes/market-deep-research/`. 코드 그래프 탐색 결과(호출 흐름·원문 포함): `F:/Claude/skills/market-deep-research/_planning/council-2026-09-19/explore-3b.txt`
- `scripts/manifest.py` — :36 `TRACKED`, :56 `_tracked_paths`, :64 `_scan`, :69 `build(for_g3=)`, :135 `extend`, :322·:453 verify/finalize 의 재해시
- `scripts/verify_facts.py` — :830 부근 G3 도판검사(이미지 참조 파싱·실재 확인·캡션 검사). **이 구간만** 만진다.
- `scripts/render_pdf.py` — :61 부근 렌더가 읽는 리소스 경로 해석(파서 재사용이 필요할 때만)
- `references/verification-gates.md` — "G3 도판검사" 절에 5줄 이내로 계약 추가
- 새 테스트: `tests/test_batch3b_regressions.py` (새 파일 하나에만 추가)

## 3. 인터페이스 (결정 사항 — 그대로 구현)
- 원고의 로컬 이미지 참조를 뽑는 함수는 **하나만** 둔다. `verify_facts.py` 의 기존 도판검사 파서를 `report_image_refs(report_text: str) -> list[str]`(원고에 적힌 상대경로 그대로, 중복 제거·순서 보존)로 공개하고, `manifest.py` 가 그것을 호출한다. 파서를 복제하지 않는다. (import 순환이 생기면 파서를 `skill_paths.py` 가 아닌 새 작은 모듈로 빼지 말고, manifest 쪽에서 함수 내부 지연 import 를 쓴다.)
- `manifest._tracked_paths(root)` 가 `TRACKED` glob 결과에 더해, `report.md` 가 있으면 그 참조 이미지 중 **작업폴더 안에 실재하는 파일**을 라벨 `"report_image"` 로 추가한다. 이미 다른 라벨로 잡힌 경로는 기존 라벨을 유지한다(중복 항목 금지).
- 참조 경로가 작업폴더 밖으로 해석되면(`..`, 절대경로, 드라이브 경로) G3 도판검사에서 FAIL `[도판경계]`. 원격 URL 은 기존 정책(렌더에서 차단)을 그대로 둔다. URL 인코딩(`%20`)·역슬래시는 기존 파서 규칙을 따른다.
- `_captures/` 증빙캡처를 본문 도판검사에서 제외하는 기존 규칙, 캡션 규칙(`[그림]`·`출처:`·`(Fxxx)`)은 바꾸지 않는다.
- `extend` 의 "기존 항목 불변 + 렌더 산출물만 추가" 계약은 그대로다. `report_image` 항목은 G3 기준선에 이미 들어 있어야 하며, G3 뒤에 원고에 새 이미지를 추가하면 지금처럼 원고 해시 변경으로 G3 복귀가 된다.

## 4. 제약
- `verify_facts.py` 의 수치·단위 파서(대략 1~470줄), 증거체인·high-risk·부록 분리(:470~:720, :870~:1040), `verify_claims.py`, `facts_db.py`, `gates.py` 는 **다른 배치 소유 — 수정 금지**.
- `manifest.py` 의 `finalize_report()` 시그니처와 CLI 인자 파싱은 배치 3A 가 고친다 — **건드리지 않는다**(재해시 대상 집합을 넓히는 것만 한다).
- `audit/**` 를 봉인 대상에 넣지 않는다(`TRACKED` 주석의 실측 경고 참고).
- 기존 테스트 단언 약화 금지. 새 의존성 금지. 주석·메시지·문서는 한국어, 식별자는 영어, 에러 접두는 `[대괄호]` 관례.
- `git commit`·`git push`·브랜치 변경 금지(팀리드가 한다). 외부 네트워크 호출·패키지 설치 금지. `_planning/` 아래 기존 파일 수정 금지.

## 5. 검증
```text
cd codes/market-deep-research
python -m pytest -q tests/test_batch3b_regressions.py
python -m pytest -q            # 기준선 431 passed — 0 failed 여야 한다
```
새 테스트는 최소: (1) 작업폴더 바로 아래 이미지가 G3 기준선 manifest 에 `report_image` 로 들어간다 (2) G3 PASS 뒤 그 이미지 내용을 바꾸면 `manifest.verify`/finalize 재해시가 실패한다 (3) `assets/` 이미지는 라벨이 `assets` 그대로이고 항목이 중복되지 않는다 (4) 작업폴더 밖 참조는 `[도판경계]` FAIL (5) 이미지가 없는 기존 흐름은 변화 없음.

## 6. REASONING: high

## 보고 형식
작업 디렉터리 루트에 `batch3b-report.md` 를 아래 형식으로 쓴다(한국어). 그 뒤 주입된 프리앰블의 절차대로 `worker_done` 을 보낸다.
```text
STATUS: <complete|partial|refused|unavailable>
CHANGES: <실제 diff 기준으로 파일별 한 줄>
VERIFIED: <재실행한 명령과 실제 출력 마지막 줄>
JUDGMENT CALLS: <스펙이 비워둔 결정과 채택한 가정>
GAPS: <남은 작업이나 막힌 지점, 없으면 없음>
```
