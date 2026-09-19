# market-deep-research 모듈화 설계안 적대적 리뷰

0절의 사용자 확정 사항(하이브리드, 코어에 하네싱·오케스트레이션 유지, 목적 ①②③, 향후 HWPX 출력 모듈)은 전제로 받아들였다. 아래 평가는 그 전제를 바꾸자는 주장이 아니라, 현재 제안대로 구현할 때 그 전제를 실제로 지키지 못하는 지점을 공격한 것이다.

검토 기준선은 다음과 같다. 현행 소스에서 `python tests/test_adversarial.py`는 등록된 적대적 케이스 **68/68**, `python tests/test_e2e.py`는 **E2E OK**였다. 반면 `python -m pytest tests -q`는 **0 tests ran**이었다. 지정된 13개 스크립트의 `demo`도 모두 통과했다. 따라서 아래 지적은 기존 무관 실패를 모듈화 탓으로 돌린 것이 아니다.

## 1) 치명(설계를 이대로 실행하면 깨지는 것)

### C1. G3 봉인이 존재하지 않고, [4b]가 검증 뒤 변조를 합법 상태로 세탁한다

설계는 [4b] 소유자를 `render_pdf.py`에서 코어 `render_report.py`로 옮기는 데 집중하지만, 소유자를 바꿔도 봉인 순서 자체가 안전하지 않다.

- `verify_facts.py`의 실제 CLI PASS 경로는 G3 영수증만 기록하고 `manifest.build()`를 호출하지 않는다(`codes/market-deep-research/scripts/verify_facts.py:919`, `codes/market-deep-research/scripts/verify_facts.py:930`, `codes/market-deep-research/scripts/verify_facts.py:935`). `manifest` import의 실제 용도도 로컬 파일 해시 계산뿐이다(`codes/market-deep-research/scripts/verify_facts.py:536`, `codes/market-deep-research/scripts/verify_facts.py:567`).
- G3 영수증에는 `facts_db_sha256`가 기록되지만(`codes/market-deep-research/scripts/gates.py:395`, `codes/market-deep-research/scripts/gates.py:407`), 후속 영수증 유효성 검사는 refs와 [2]의 confirmed 투영만 확인한다(`codes/market-deep-research/scripts/gates.py:219`, `codes/market-deep-research/scripts/gates.py:231`, `codes/market-deep-research/scripts/gates.py:248`). 즉 기록한 G3 사실대장 해시를 다시 대조하지 않는다.
- 현 렌더 CLI는 G3 영수증만 요구한 뒤 렌더하고, 그 시점의 전체 파일을 새 매니페스트로 다시 만든다(`codes/market-deep-research/scripts/render_pdf.py:104`, `codes/market-deep-research/scripts/render_pdf.py:108`, `codes/market-deep-research/scripts/render_pdf.py:113`, `codes/market-deep-research/scripts/render_pdf.py:114`).
- `manifest.build()`는 기존 G3 항목을 보존·확장하는 함수가 아니다. 현재 상태를 전부 재스캔해 `manifest.json`을 통째로 덮어쓴다(`codes/market-deep-research/scripts/manifest.py:45`, `codes/market-deep-research/scripts/manifest.py:55`, `codes/market-deep-research/scripts/manifest.py:62`). 이후 G5는 이 새 기준선만 대조한다(`codes/market-deep-research/scripts/manifest.py:66`, `codes/market-deep-research/scripts/manifest.py:71`, `codes/market-deep-research/scripts/manifest.py:76`).
- E2E는 이 공백을 드러내지 않는다. 함수 호출로 G3 검증 후 `manifest.build()`를 수동 삽입하기 때문이다(`codes/market-deep-research/tests/test_e2e.py:106`, `codes/market-deep-research/tests/test_e2e.py:110`). 실제 CLI 경로와 다른 시험이다.

직접 재현했다. 정상 G0/G1/[2] 뒤 `verify_facts.py` CLI가 G3를 기록한 직후 `manifest.json`은 없었다. 그 뒤 `report.md`와 `facts.jsonl`을 변조하고 `render_pdf.py` CLI를 실행하자 G3 영수증은 여전히 유효했고, 변조된 상태가 재봉인되었으며, G4 영수증 뒤 `manifest.py verify`가 **exit 0 + G5 PASS 영수증**을 남겼다.

제안서 4.1의 “디스패처가 manifest build와 [4b]를 소유”(`_planning/council-2026-08-22/modularize-proposal.md:47`)는 바로 이 취약한 순서를 그대로 옮긴다. 최소 조건은 G3에서 불변 기준선을 만들고, [4b]에서는 기존 항목이 한 바이트도 안 바뀌었음을 먼저 검증한 뒤 렌더 산출물만 **extend-only**로 추가하는 것이다. G3 영수증·기준 매니페스트·[4b] 영수증도 서로의 다이제스트로 결박해야 한다.

### C2. 제안된 범용 `out_path`와 HWPX 산출물은 매니페스트 보호 대상이 아니다

양식 계약은 임의 `out_path`를 반환하도록 일반화하지만, 코어 무결성 모델은 파일명 `report.pdf` 하나에 고정돼 있다.

- 매니페스트 추적표는 `report.md`와 정확히 `report.pdf`만 포함한다(`codes/market-deep-research/scripts/manifest.py:25`, `codes/market-deep-research/scripts/manifest.py:32`, `codes/market-deep-research/scripts/manifest.py:33`).
- `WorkPaths`도 출력 속성으로 `report_pdf`만 제공한다(`codes/market-deep-research/scripts/skill_paths.py:100`, `codes/market-deep-research/scripts/skill_paths.py:104`).
- 반면 현 PDF 렌더 함수와 CLI는 이미 임의 출력명을 허용한다(`codes/market-deep-research/scripts/render_pdf.py:68`, `codes/market-deep-research/scripts/render_pdf.py:71`, `codes/market-deep-research/scripts/render_pdf.py:104`, `codes/market-deep-research/scripts/render_pdf.py:105`). 제안 계약도 이를 `out_path`로 일반화한다(`_planning/council-2026-08-22/modularize-proposal.md:47`).

직접 `custom.pdf`로 렌더한 뒤 `manifest.build()`를 실행했다. `custom.pdf`는 entries에 없었고, 파일을 변조한 뒤에도 `manifest.verify()`는 **True**였다. `report.hwpx`도 같은 이유로 영구 미추적이다. 따라서 현 계약으로는 디스패처가 [4b] PASS를 기록해도 실제 출력물을 봉인했다는 뜻이 아니다.

출력 모듈은 단일 `out` 문자열이 아니라 `artifacts=[{path, role, media_type, sha256}]`를 반환해야 하며, 코어가 경로를 작업폴더 내부로 제한하고 실파일·해시·형식을 검증한 뒤 그 정확한 목록을 매니페스트에 추가해야 한다.

### C3. “풀어야 할 결합 3건”은 실제 import 결합을 다 세지 않아 독립 스킬이 import 단계에서 죽는다

제안 구조를 임시 디렉터리에 그대로 복제해 각 독립 CLI의 `demo`를 실행했다. 결과는 `mdr-collect/search.py → No module named skill_paths`, `mdr-figures/harvest_images.py → No module named fetch`, `mdr-figures/make_chart.py → No module named facts_db`, `mdr-render-pdf/render_pdf.py → No module named skill_paths`였다.

렌더와 차트는 4절에서 일부 리팩터링을 예고했지만, 목록 자체가 불완전하다.

- `search.py`는 import 시점에 `skill_paths.ASSETS`를 요구하고 곧바로 두 JSON 자산을 읽는다(`codes/market-deep-research/scripts/search.py:24`, `codes/market-deep-research/scripts/search.py:35`, `codes/market-deep-research/scripts/search.py:36`). 그런데 제안된 collect 모듈 파일 목록에는 모듈 로컬 경로 유틸도, 이 import를 없애는 작업도 없다(`_planning/council-2026-08-22/modularize-proposal.md:33`, `_planning/council-2026-08-22/modularize-proposal.md:46`).
- `harvest_images.py`는 `fetch`의 함수·상수 네 개와 코어 `skill_paths.ASSETS`를 동시에 import한다(`codes/market-deep-research/scripts/harvest_images.py:32`, `codes/market-deep-research/scripts/harvest_images.py:33`). 함수 안에서도 다시 `fetch.fetch`를 import하며(`codes/market-deep-research/scripts/harvest_images.py:343`, `codes/market-deep-research/scripts/harvest_images.py:345`), collect로 옮길 자산을 현 `ASSETS`에서 읽는다(`codes/market-deep-research/scripts/harvest_images.py:387`, `codes/market-deep-research/scripts/harvest_images.py:414`).
- `make_chart.py`의 결합은 `FactsDB`만이 아니다. `WorkPaths`와 `slugify`도 코어 import다(`codes/market-deep-research/scripts/make_chart.py:18`, `codes/market-deep-research/scripts/make_chart.py:19`, `codes/market-deep-research/scripts/make_chart.py:198`, `codes/market-deep-research/scripts/make_chart.py:202`). 제안 4.2는 앞의 import만 제거한다(`_planning/council-2026-08-22/modularize-proposal.md:48`).
- `render_pdf.py`도 `ASSETS`, `WorkPaths`, `gates`, `manifest`, `_find_chrome`의 다섯 결합을 가진다(`codes/market-deep-research/scripts/render_pdf.py:19`, `codes/market-deep-research/scripts/render_pdf.py:23`). 제안은 영수증·봉인·Chrome 탐지만 명시하고, 모듈 로컬 style 경로와 CLI의 `WorkPaths` 제거를 계약에 적지 않았다.

제안 3.3의 “subprocess CLI 호출”도 현 상태에서는 대체재가 아니다. `harvest_images.page_images()`는 fetch의 raw HTML이 필요하지만(`codes/market-deep-research/scripts/harvest_images.py:343`, `codes/market-deep-research/scripts/harvest_images.py:348`), fetch CLI는 `text`와 `raw`를 제거한 JSON을 다시 1,500자로 잘라 출력한다(`codes/market-deep-research/scripts/fetch.py:566`, `codes/market-deep-research/scripts/fetch.py:574`). 긴 trace면 JSON 자체도 잘린다. 즉 안정된 IPC 계약을 새로 만들지 않는 한 “5줄 로케이터 또는 subprocess”는 구현 선택지가 아니다.

### C4. “경로만 추가해 84함수 그린”이라는 1차 완료기준은 성립하지 않는다

제안은 테스트를 코어에 두고 `module_scripts()`로 경로만 추가해 현 테스트를 유지한다고 한다(`_planning/council-2026-08-22/modularize-proposal.md:53`). 실제 테스트는 경로뿐 아니라 파일명, 문서 위치, 반환 스키마, 파이프라인 순서를 고정하고 있다.

- 두 테스트 모두 코어의 단일 `scripts/`를 `sys.path`에 넣고 bare import한다(`codes/market-deep-research/tests/test_adversarial.py:18`, `codes/market-deep-research/tests/test_adversarial.py:21`, `codes/market-deep-research/tests/test_adversarial.py:29`, `codes/market-deep-research/tests/test_e2e.py:12`, `codes/market-deep-research/tests/test_e2e.py:17`).
- 새 핵심 경로인 `render_report.py`는 존재하지 않으므로 어느 테스트도 디스패처의 G3 전제·모듈 응답검증·manifest build·[4b] 자기기록을 시험하지 않는다. E2E는 `render_pdf.render()`를 직접 부르고 수동 재봉인한다(`codes/market-deep-research/tests/test_e2e.py:110`, `codes/market-deep-research/tests/test_e2e.py:115`, `codes/market-deep-research/tests/test_e2e.py:123`).
- 제안 계약은 반환 키를 `out`으로 바꾸지만 현 적대 테스트는 `r["pdf"]`를 고정한다(`codes/market-deep-research/tests/test_adversarial.py:671`, `codes/market-deep-research/tests/test_adversarial.py:689`).
- `source-ladder.md`를 collect로 옮기면 코어 `SKILL_ROOT/references/source-ladder.md`를 직접 읽는 문서정합 테스트가 깨진다(`codes/market-deep-research/tests/test_adversarial.py:1167`, `codes/market-deep-research/tests/test_adversarial.py:1291`, `codes/market-deep-research/tests/test_adversarial.py:1295`).
- `render_pdf`라는 SKILL 본문 절 제목까지 정규식으로 고정돼 있다(`codes/market-deep-research/tests/test_adversarial.py:1302`, `codes/market-deep-research/tests/test_adversarial.py:1314`).

따라서 “경로만 추가”와 “현행 그린”은 동시에 달성할 수 없다. 더 나쁜 점은 테스트를 억지로 경로만 고쳐 그린으로 만들어도 새 디스패처를 우회하므로 가장 위험한 영수증 경계를 검증하지 못한다는 것이다.

## 2) 중대(목적 ①②③을 해치는 것)

### M1. preflight가 PDF 전용 HARD 의존성을 코어 전체의 전제조건으로 유지한다

현 preflight는 `fitz`, `pandoc`, Chrome를 무조건 HARD로 둔다(`codes/market-deep-research/scripts/preflight.py:7`, `codes/market-deep-research/scripts/preflight.py:23`, `codes/market-deep-research/scripts/preflight.py:48`, `codes/market-deep-research/scripts/preflight.py:55`)며 하나라도 없으면 전체가 실패한다(`codes/market-deep-research/scripts/preflight.py:64`, `codes/market-deep-research/scripts/preflight.py:97`). 제안 4.1은 `_find_chrome` 이동만 말하고 `pandoc`·`fitz`의 선택적 검사와 HWPX 의존성 계약은 없다(`_planning/council-2026-08-22/modularize-proposal.md:47`).

그 결과 collect-only도 pandoc/Chrome가 없으면 G0에서 막히고, HWPX-only도 PDF 모듈이 없으면 막힌다. 목적 ③과 향후 출력 모듈 전제가 동시에 깨진다. 코어 preflight는 선택한 stage/format별 `probe()` 결과를 합성해야 한다.

### M2. “소유 스크립트만 영수증 기록”은 실제 소유권 검사가 아니라 CLI 한 경로의 블랙리스트다

`SCRIPT_OWNED`는 게이트 이름 집합일 뿐 소유자 매핑이 아니며(`codes/market-deep-research/scripts/gates.py:33`, `codes/market-deep-research/scripts/gates.py:39`), 공개 Python 함수 `record_script_result()`는 호출자와 선행조건을 확인하지 않고 무엇이든 append한다(`codes/market-deep-research/scripts/gates.py:372`, `codes/market-deep-research/scripts/gates.py:384`, `codes/market-deep-research/scripts/gates.py:415`). 차단은 CLI 분기에서만 일어난다(`codes/market-deep-research/scripts/gates.py:538`, `codes/market-deep-research/scripts/gates.py:541`). 테스트도 CLI 위조만 막고(`codes/market-deep-research/tests/test_adversarial.py:1334`, `codes/market-deep-research/tests/test_adversarial.py:1342`), 다른 테스트는 G3/[4b]를 그 공개 API로 직접 기록한다(`codes/market-deep-research/tests/test_adversarial.py:1371`, `codes/market-deep-research/tests/test_adversarial.py:1373`).

따라서 “모듈은 코어 영수증을 못 쓴다”는 보안 경계가 아니라 개발자 규약이다. 최소한 코어 전용 엔트리포인트가 선행조건·기준 매니페스트·정확한 artifact digest를 한 트랜잭션으로 검증·기록하고, 모듈에는 gates import 경로 자체를 주지 않아야 한다. 문서에는 이를 보안 격리가 아닌 신뢰 모델로 정직하게 표현해야 한다.

### M3. 독립 스킬의 단독 트리거와 코어 하네싱이 충돌한다

제안은 모든 모듈을 단독 트리거할 수 있게 한다(`_planning/council-2026-08-22/modularize-proposal.md:38`, `_planning/council-2026-08-22/modularize-proposal.md:44`). 하지만 raw `render()`에는 게이트나 재봉인이 없고(`codes/market-deep-research/scripts/render_pdf.py:68`, `codes/market-deep-research/scripts/render_pdf.py:77`), 그것들은 오직 현 CLI main에만 있다(`codes/market-deep-research/scripts/render_pdf.py:99`, `codes/market-deep-research/scripts/render_pdf.py:125`).

사용자가 기존 조사폴더에 “렌더만”을 요청했을 때 라우터가 `mdr-render-pdf`를 직접 고르면, 코어 디스패처를 우회해 봉인되지 않은 `report.pdf`를 만든다. capture-only/collect-only도 봉인 뒤 파일을 추가하면 manifest drift를 만든다. 목적 ③의 “부분 실행”을 raw 유틸 실행과 파이프라인 stage 재개 중 무엇으로 정의하는지, 어떤 경우 반드시 코어로 라우팅하는지 설계가 없다.

### M4. `harvest_images.py`는 도판 렌더러보다 수집기이며, 분리 비용만 만드는 경계다

이 파일은 PDF 도판 추출뿐 아니라 fetch 사다리 호출, 웹 HTML 파싱, SearX/curated 자산 읽기, SSRF 검증 다운로드를 수행한다(`codes/market-deep-research/scripts/harvest_images.py:144`, `codes/market-deep-research/scripts/harvest_images.py:343`, `codes/market-deep-research/scripts/harvest_images.py:387`, `codes/market-deep-research/scripts/harvest_images.py:511`, `codes/market-deep-research/scripts/harvest_images.py:555`). collect에 대한 결합은 우연이 아니라 기능의 본체다.

이를 figures로 떼면 목적 ②를 위해 새 로케이터·IPC·버전 계약을 유지해야 하고, figures 단독 실행도 collect 없이는 불완전하다. 더 싼 경계는 `harvest_images`를 collect에 두고, figures에는 중립 데이터→SVG 같은 순수 생성기만 두는 것이다.

### M5. `make_chart`의 confirmed-only 보증을 “JSONL 약 10줄”로 복제하면 코어 계약이 두 군데가 된다

현 함수는 `FactsDB`뿐 아니라 작업폴더 경계와 동일 slug 규칙을 재사용한다(`codes/market-deep-research/scripts/make_chart.py:39`, `codes/market-deep-research/scripts/make_chart.py:41`, `codes/market-deep-research/scripts/make_chart.py:194`, `codes/market-deep-research/scripts/make_chart.py:206`). 직접 JSONL 읽기 자체는 가능하지만, 앞으로 confirmed 의미·대장 버전·경로 규칙이 바뀌면 figures가 독자 구현을 갖게 된다. 이는 목적 ②에 역행한다.

코어가 검증된 중립 `ChartSpec`(labels/values/unit/fact_ids/out_path)을 만들어 넘기고, figures는 그 spec으로 SVG만 만드는 편이 경계를 실제로 순수하게 만든다.

### M6. 다중 스킬 설치는 소스 루트·허용목록·원자성·버전 호환 계약이 없다

현 설치기는 `SKILL_ROOT` 한 트리만 복사하고(`codes/market-deep-research/scripts/install.py:56`, `codes/market-deep-research/scripts/install.py:66`) 그 타깃 내부 stale만 지운다(`codes/market-deep-research/scripts/install.py:80`, `codes/market-deep-research/scripts/install.py:85`). `SKILL_ROOT`는 파일 위치의 부모로 계산된다(`codes/market-deep-research/scripts/skill_paths.py:34`).

제안처럼 `SKILL_ROOT.parent/*/SKILL.md`를 일반화하면 개발본에서는 `codes/*`지만 설치본에서 실행할 때는 사용자의 **모든 설치 스킬**이 후보가 된다. 명시적 MDR 모듈 allowlist가 없다. 또 모듈 하나를 제거·개명하면 소스 스캔에 더는 나타나지 않아 옛 `~/.claude/skills/mdr-*` 폴더가 그대로 남고, 설치 중간 실패 시 코어와 모듈 버전이 갈린다. `--target`이 단일 스킬 경로인지 부모 경로인지도 정의되지 않았다(`codes/market-deep-research/scripts/install.py:156`, `codes/market-deep-research/scripts/install.py:168`).

번들 manifest(모듈명·계약버전·해시·설치대상)와 staging 후 일괄 교체가 없으면 목적 ②가 나빠진다.

### M7. `sys.path` 주입은 모듈 로케이터가 아니라 전역 import 오염이다

제안은 모듈 scripts 경로를 `sys.path`에 넣는다(`_planning/council-2026-08-22/modularize-proposal.md:42`). 현 코드는 `fetch`, `manifest`, `skill_paths` 같은 bare 이름에 의존한다(`codes/market-deep-research/scripts/harvest_images.py:32`, `codes/market-deep-research/scripts/render_pdf.py:20`, `codes/market-deep-research/scripts/search.py:28`). 이미 같은 이름이 `sys.modules`에 있으면 새 경로를 앞에 넣어도 의도한 모듈을 얻는다는 보장이 없다.

또 개발 코어가 개발 모듈 누락 시 설치본으로 조용히 폴백하면 서로 다른 커밋을 섞어 시험하게 된다. 계약버전 검사도 없다. 목적 ②를 위해서는 namespaced package import 또는 명시적 `spec_from_file_location`/안정된 subprocess 프로토콜이 필요하다. 개발 모드와 설치 모드는 섞지 말고 한 루트를 선택해야 한다.

### M8. UTF-8 안정성이 import 부수효과에 매여 있고, 분리 후 사라진다

UTF-8 재설정은 `skill_paths` import의 프로세스 전역 부수효과다(`codes/market-deep-research/scripts/skill_paths.py:26`, `codes/market-deep-research/scripts/skill_paths.py:31`). 현재 render/search/make_chart는 이 import에 우연히 기대지만, 제안대로 코어 import를 제거하면 그 효과도 잃는다. 반대로 “모든 스크립트가 skill_paths를 import한다”는 현황 설명(`_planning/council-2026-08-22/modularize-proposal.md:23`)도 사실이 아니다. 예를 들어 capture와 preflight는 자체 main에서만 재설정한다(`codes/market-deep-research/scripts/capture_pdf.py:150`, `codes/market-deep-research/scripts/preflight.py:87`), fetch도 마찬가지다(`codes/market-deep-research/scripts/fetch.py:557`).

각 CLI entrypoint가 명시적으로 공통 runtime bootstrap을 호출하거나, subprocess에서 `PYTHONUTF8=1`을 강제해야 한다. 경로 유틸 import에 인코딩 정책을 숨기면 독립 모듈 테스트와 라이브러리 import의 동작이 달라진다.

### M9. “순수 도구” 규칙과 실제 fetch의 상태 쓰기가 맞지 않는다

`fetch()`는 URL만 받지만 매 시도마다 현재 작업디렉터리의 `audit/`에 스냅샷과 JSONL을 쓴다(`codes/market-deep-research/scripts/fetch.py:117`, `codes/market-deep-research/scripts/fetch.py:127`, `codes/market-deep-research/scripts/fetch.py:144`, `codes/market-deep-research/scripts/fetch.py:406`). 실패는 삼킨다(`codes/market-deep-research/scripts/fetch.py:146`). import 시에는 CA 번들을 사용자 홈/ProgramData에 복사할 수도 있다(`codes/market-deep-research/scripts/fetch.py:77`, `codes/market-deep-research/scripts/fetch.py:94`, `codes/market-deep-research/scripts/fetch.py:110`).

따라서 제안 3.1의 “경로를 인자로 받는 순수 도구”(`_planning/council-2026-08-22/modularize-proposal.md:41`)가 이미 거짓이다. collect 단독 실행 시 영수증이 어느 조사폴더 소유인지도 불명확하다. `work_dir/audit_sink`를 명시 인자로 받고, import는 무상태로 만들어야 한다.

### M10. 컨텍스트 절약의 비용·효과가 측정되지 않았다

현재 `SKILL.md`는 184행·9,338자이고, 백엔드 구현 세부로 넓게 잡을 수 있는 구간도 대략 45행·2,929자(31.4%)였다. 그러나 그 구간의 증거 의미·게이트 순서·부분 실행 규칙은 코어에 남아야 하므로 실제 제거량은 더 작다. 반면 네 모듈 description 약 600자는 모든 세션에 상시 추가된다고 제안서 스스로 인정한다(`_planning/council-2026-08-22/modularize-proposal.md:51`, `_planning/council-2026-08-22/modularize-proposal.md:52`). 전체 시장조사에서는 여러 모듈 지침을 결국 다시 읽을 가능성이 높다.

코어에서 실제로 뺄 수 있는 것은 fetch 백엔드 순서의 상세, pandoc/Chrome 플래그, 이미지 검색 구현, 캡처 CLI recipe 같은 **백엔드 사용법**이다(`codes/market-deep-research/SKILL.md:97`, `codes/market-deep-research/SKILL.md:114`, `codes/market-deep-research/SKILL.md:126`, `codes/market-deep-research/SKILL.md:143`, `codes/market-deep-research/SKILL.md:164`). 영수증 순서·증빙 인정 기준·confirmed-only·출력 검증은 코어에서 빠질 수 없다. 전후 토큰 측정과 full-run/부분-run 각각의 로드 모델 없이는 목적 ① 달성 주장이 아니다.

## 3) 경미/개선

1. 소유자 이름이 주석·오류문구에 `render_pdf.py`로 하드코딩돼 있다(`codes/market-deep-research/scripts/gates.py:36`, `codes/market-deep-research/scripts/gates.py:544`). `render_report.py`로 옮길 때 기능은 우연히 동작해도 진단과 문서가 거짓이 된다.
2. 제안 계약은 `{"ok","out","size","at"}`인데 현 PDF 구현과 테스트의 키는 `pdf`다(`codes/market-deep-research/scripts/render_pdf.py:77`, `codes/market-deep-research/tests/test_adversarial.py:689`). 문자열 dict 대신 버전이 있는 schema/dataclass가 필요하다.
3. 상대경로 갱신 대상은 단순 `scripts/fetch.py` 언급보다 넓다. core의 `agent-briefs.md`가 search/fetch와 core facts-schema를 함께 가리키고(`codes/market-deep-research/references/agent-briefs.md:9`, `codes/market-deep-research/references/agent-briefs.md:18`), figures의 `image-research.md`는 collect 자산을 가리키며(`codes/market-deep-research/references/image-research.md:32`, `codes/market-deep-research/references/image-research.md:35`), core `report-format.md`는 PDF renderer/style과 figures 문서를 가리킨다(`codes/market-deep-research/references/report-format.md:51`, `codes/market-deep-research/references/report-format.md:55`). 문서 링크 그래프 검사 없이는 stale 경로가 남는다.
4. 현 테스트 러너는 pytest가 수집하지 못하고 자체 `main()`만 실행한다(`codes/market-deep-research/tests/test_adversarial.py:1553`, `codes/market-deep-research/tests/test_adversarial.py:1566`, `codes/market-deep-research/tests/test_e2e.py:144`). 목적 ②를 내세우려면 표준 수집 가능 테스트로 바꾸거나 실행 계약을 명시해야 한다.
5. 모듈 description 150자 제한은 길이만 있고 상호 배타적 트리거, full-run에서 중복 트리거 방지, “기존 MDR 작업폴더의 렌더”를 코어로 보내는 음성 규칙이 없다. 라우팅 테스트가 필요하다.

### 조사 중 기각한 가설

- **capture 경계도 숨은 코어 import 때문에 깨질 것**이라는 가설은 기각했다. 두 capture 스크립트는 stdlib+fitz만 import하고 명시 경로를 받는다(`codes/market-deep-research/scripts/capture_pdf.py:10`, `codes/market-deep-research/scripts/capture_pdf.py:59`, `codes/market-deep-research/scripts/capture_web.py:10`, `codes/market-deep-research/scripts/capture_web.py:24`). 이 분할은 현 제안 중 가장 건전하다.
- **manifest가 차트와 수확 이미지를 빠뜨린다**는 가설은 기각했다. `assets/**/*`와 `_images/**/*`는 이미 추적된다(`codes/market-deep-research/scripts/manifest.py:28`, `codes/market-deep-research/scripts/manifest.py:29`)며 회귀 테스트도 있다(`codes/market-deep-research/tests/test_adversarial.py:693`, `codes/market-deep-research/tests/test_adversarial.py:710`). 문제는 출력 확장과 재봉인 방식이다.
- **PDF 양식 경계 자체가 성립하지 않는다**는 강한 가설은 기각했다. style과 Chrome 탐색을 PDF 모듈로 옮기면 실제 렌더 엔진 결합은 제거할 수 있다(`codes/market-deep-research/scripts/render_pdf.py:25`, `codes/market-deep-research/scripts/render_pdf.py:32`, `codes/market-deep-research/scripts/render_pdf.py:46`). 문제는 그 위의 코어 계약·검증·preflight가 빠졌다는 점이다.

## 4) 설계안 6절 질문 5개에 대한 직접 답

1. **분할 경계가 틀린 곳은?** capture와 renderer 경계는 타당하다. `harvest_images`는 figures가 아니라 collect에 두는 편이 맞다. `make_chart`는 코어의 validated `ChartSpec` 생성부와 figures의 순수 SVG 생성부로 갈라야 한다. preflight/preview는 renderer별 capability로 묶되 선택·영수증은 코어가 소유해야 한다.
2. **의존 규칙 1~3이 실제 코드에서 깨지는 곳은?** `search→skill_paths/ASSETS`, `harvest→fetch+collect assets+skill_paths`, `make_chart→FactsDB+WorkPaths+slugify`, `render_pdf→skill_paths+gates+manifest+preflight`에서 깨진다. receipt는 CLI만 소유권을 흉내 내며, G3 해시를 재검사하지 않는다. manifest는 `report.pdf`만 추적하고 [4b]에서 기존 해시를 덮어쓴다. UTF-8은 `skill_paths` import 제거와 함께 사라진다.
3. **양식 모듈 계약이 HWPX에도 성립하는가?** 현재 형태로는 아니다. `render(md,out,resource_dir)`라는 표면은 재사용할 수 있지만, 최소한 `probe/capabilities`, template/options와 그 해시, `artifacts[]`, format-specific `validate`, 실제 renderer 기반 `preview`, renderer/contract version이 더 필요하다. 코어 manifest와 G5도 확장된 artifact 목록을 받아야 한다.
4. **컨텍스트 절약이 실제로 나는가?** 입증되지 않았다. core에서 뺄 수 있는 것은 백엔드 사용법뿐이고 하네싱 의미는 남아야 한다. 전체 실행에서는 네 모듈 설명과 필요한 모듈 지침이 다시 들어온다. 현재 9,338자 대비 full-run/부분-run별 실제 로드 토큰을 계측하기 전에는 절약이라고 판정할 수 없다.
5. **더 싼 대안이 목적 ①②③을 못 충족한다는 근거가 충분한가?** 전혀 충분하지 않다. 오히려 현재 각 스크립트는 이미 독립 CLI를 갖는다(`codes/market-deep-research/scripts/fetch.py:12`, `codes/market-deep-research/scripts/capture_pdf.py:7`, `codes/market-deep-research/scripts/harvest_images.py:8`, `codes/market-deep-research/scripts/render_pdf.py:7`). 한 스킬 안의 namespaced 하위패키지+짧은 router+필요시만 읽는 reference 문서로 ①②③을 모두 달성할 수 있다.

## 5) 대안 제시와 근거

### 대안: 한 스킬 안의 하이브리드 패키지로 먼저 분리하고, 독립 스킬 래퍼는 계측 후 결정

0절 전제를 유지하면서 비용을 낮추는 구조는 다음과 같다.

```text
market-deep-research/
├── SKILL.md                    # 짧은 router + 코어 불변조건만
├── mdr/
│   ├── core/                   # facts, gates, manifest, verify, orchestration
│   ├── collect/                # fetch, search, harvest_images
│   ├── capture/                # capture_pdf, capture_web
│   ├── figures/                # ChartSpec -> SVG 같은 순수 생성만
│   └── renderers/
│       ├── pdf/                # style, render, validate, preview, probe
│       └── hwpx/               # template, render, validate, preview, probe
├── scripts/mdr.py              # collect/capture/figures/render/resume 단일 CLI
└── references/modules/         # 단계별 사용법, 필요할 때만 로드
```

이 대안이 더 싼 이유는 다음과 같다.

1. **컨텍스트(①)**: 현 SKILL 자체가 이미 “참조 문서는 필요할 때만 로드” 구조다(`codes/market-deep-research/SKILL.md:173`). 긴 백엔드 설명을 `references/modules/`로 옮기면 별도 스킬 네 개의 상시 description과 중복 라우팅 없이 같은 절약을 낸다.
2. **유지보수·테스트(②)**: `from mdr.collect.fetch import ...` 같은 namespaced import로 `sys.path` 주입과 모듈 충돌을 없앤다. 한 설치 트리라 현재 해시검증·stale 정리 모델도 크게 바꾸지 않는다. module unit test, clean-process import test, dispatcher E2E를 디렉터리별로 둘 수 있다.
3. **부분 실행(③)**: 현 스크립트가 이미 개별 CLI이므로 물리적으로 별도 skill일 필요가 없다. `mdr.py collect ...`, `capture ...`, `render --format pdf`처럼 subcommand로 노출하면 된다. 기존 MDR 작업폴더를 만지는 명령은 항상 core stage adapter를 거치므로 영수증을 우회하지 않는다.
4. **양식 확장**: renderer registry는 다음 계약을 가져야 한다.
   - `probe() -> dependencies/capabilities`
   - `render(RenderRequest) -> RenderResult(artifacts, renderer_version, diagnostics)`
   - `validate(request, result) -> validation evidence`
   - `preview(result, out_dir) -> preview artifacts`
   코어는 요청 경로·artifact 실재·magic/format·해시를 검사하고서만 [4b]를 기록한다.
5. **무결성 선행수정**: 모듈 이동 전에 G3 immutable manifest를 만들고, [4b]는 old entries 불변 확인 후 artifact만 추가하도록 바꾼다. [4b] 영수증에는 G3 receipt digest, renderer contract/version/code hash, artifact digest, 최종 manifest digest를 넣는다. 이 선행수정 없이는 어느 폴더 구조도 안전하지 않다.

정말 독립 트리거가 필요하다는 계측 결과가 나온 뒤에는 위 패키지 코드를 복제하지 않고 호출만 하는 얇은 `mdr-*` SKILL 래퍼를 추가할 수 있다. 먼저 다섯 설치 단위와 전역 import 로케이터를 만드는 것은 되돌리기 비싼 순서다.

## 6) 한 줄 판정

**재설계 — G3/[4b] 불변 봉인, 동적 artifact manifest, format-aware preflight/validation, 실제 import·테스트·설치 계약을 먼저 닫지 않으면 진행 불가.**
