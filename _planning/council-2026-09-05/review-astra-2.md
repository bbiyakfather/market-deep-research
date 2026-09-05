# market-deep-research 적대적 리뷰 2차

## 0. 리뷰 전 고정한 평가 기준

평가 대상은 3aaaf8ee6a1208e86c5d2995f970fc432223b941의 커밋 상태다. 실제 HEAD 12a50eab0b44839e5603dad7b9c3531cc80076e6과 대상 세 디렉터리의 git diff가 비어 있음을 확인했다. 진행 중 패치는 평가하지 않는다. 코드 수정 없이 소스 판독과 임시 디렉터리에서의 재현으로 평가한다.

아래 배점·검사 항목은 구현 검토와 재현 전에 고정했다. 항목은 모두 적용하며 사전 제외는 없다. pass=1, partial=0.5, fail=0, unverified=0. 각 차원 점수는 네 항목의 산술평균×배점이다. partial은 충족 조건과 미충족 조건을 모두 기술한다. 이 점수는 사실 정확도의 확률이 아니라 아래 고정된 통제 항목의 충족도다.

| 차원 | 배점 | 사전 고정 검사 항목 |
|---|---:|---|
| A. 게이트·봉인 무결성 | 20 | A1 선행 게이트·영수증 실패 폐쇄; A2 G3 이후 입력 변경 검출; A3 최종 산출물 전체 봉인·변조 검출; A4 영수증 발급·재발급·최종 판정의 단일 일관 경로 |
| B. 대장·스키마 무결성 | 15 | B1 중첩 스키마·필수·타입 제약; B2 ID·claim_key 고유성·증거 참조 무결성; B3 동시 쓰기·실패 시 원자성; B4 상태 승격·입력 전체 유효성 검사 |
| C. 증빙·주장 검증 | 15 | C1 원문·재열람·인용·본문 결박; C2 캡처 내용·위치·파일 실체 검증; C3 출처 독립성·시점·고위험 판정; C4 수치·계산·주장 범위 검증 |
| D. fetch·캡처 보안 | 15 | D1 최초 URL의 스킴·호스트·사설망 차단; D2 리다이렉트·DNS·우회 단계의 동일 경계; D3 다운로드·브라우저 자원 및 로컬 파일 경계; D4 실패·차단·비본문 결과의 명확한 구분 |
| E. 오케스트레이션 | 10 | E1 워커 마커 계약·위반 검출; E2 부분실패·타임아웃·재시도 회수; E3 확장 수렴·중복 리드·종료 조건; E4 동시 워커 소유권·병합·실패 전파 |
| F. 문서·목적 스킬 정합성 | 10 | F1 SKILL과 게이트 코드의 판정 강도; F2 references와 실제 CLI·반환 계약; F3 search 목적의 진입·인계 경계; F4 HWPX 목적의 경계·완료 선언 |
| G. 회귀 검증 | 10 | G1 기존 테스트 실행·성공 여부; G2 실제 CLI와 영수증 전체 경로 검증; G3 악성 스키마·동시성·통신 실패 검증; G4 SSRF·캡처·출력 변조 회귀 검증 |
| H. 운영 현실성 | 5 | H1 합법 수정 후 재검증 가능성; H2 최소 의존성·플랫폼·재개 경로; H3 수동 검토의 실행 가능성과 증적; H4 최종 판정의 자동화·재현 가능성 |

기지 여부는 두 맥락 문서와 대조한다. 실전 보고서 P0 4건은 반드시 [기지(旣知)]로 표시하며, 1차 리뷰에 이미 있던 미해결 결함도 [기지]로 분리한다. 신규 결함은 별도 집계한다. 심각도는 치명(검증되지 않은 결과의 최종 통과·중대한 보안 경계 우회), 중대(데이터 손실·조사 누락·일반 운영 실패), 경미(제한적 불편·진단성 저하)로 고정한다.
## 1. 검토 범위·재현 방식

- 파일 인용에서 `scripts/`, `references/`, `assets/`, `tests/`, `SKILL.md`는 모두 `codes/market-deep-research/` 기준이다. 목적 스킬은 `codes/mdr-*` 전체 경로를 쓴다. 기준 워크스페이스는 `C:/Users/eicic.AIDEN-DESKTOP/orca/workspaces/market-deep-research/adv-review-2`다.
- 1차 리뷰와 실전 수정방안 문서를 읽고, 코어 16개 스크립트의 실행 경로, 9개 참조문서, 스키마·자산, 두 테스트와 목적 스킬 경계를 대조했다. 모듈화 제안에만 존재하는 가상 파일은 현행 결함으로 세지 않았다.
- `python -B .../tests/test_adversarial.py`: **71/71, exit 0**. `python -B .../tests/test_e2e.py`: **E2E OK, exit 0**, 사실 2건·증거 2건·PDF 2쪽. PYTHONDONTWRITEBYTECODE를 설정했고 작업 cwd는 저장소 밖 scratchpad였다.
- 추가 재현은 임시 대장·PDF·PNG를 사용했다. 네트워크 실험은 직접 만든 loopback HTTP 서버만 사용했다. 공인 호스트를 모사하는 DNS/transport fixture의 사용 여부를 아래에 명시한다. 외부 서비스·실제 내부망에는 공격 요청을 보내지 않았다.
- 오케스트레이션은 문서 계약과 구현 유무를 평가했다. 실제 LLM 워커의 누락 빈도·비종료 빈도를 측정한 것은 아니다. HWPX는 원고 인계·split 경계만 실행했으며 한글 COM·전체 양식 품질을 재평가하지 않았다.
- 실행 증적은 이 리뷰와 같은 scratchpad의 `astra2-probes.json`, `astra2-security-probes.json`, `astra2-extra-probes.json`, `astra2-known-probes.json`, `astra2-image-ssrf-probes.json`에 보존했다. 각 결함의 재현 절차는 아래에도 기술한다.

## 2. 점수표

각 partial의 **충족 / 미충족**을 분리했다. 적용 항목 32개, 사후 제외 0개. 점수는 반올림하지 않았다.

| 차원 | 항목 | 판정 | 값 | 판정 근거·파일:라인 |
|---|---|---|---:|---|
| A | A1 선행 게이트·영수증 실패 폐쇄 | partial | 0.5 | 충족: 직접 선행 영수증 누락·실패·refs 변조 차단. 미충족: G5가 조상 실패·계획 변경을 재검사하지 않음(N04). `scripts/gates.py:248`, `scripts/gates.py:275`, `scripts/manifest.py:210` |
| A | A2 G3 이후 입력 변경 검출 | partial | 0.5 | 충족: TRACKED 파일 변조·기준 manifest 재빌드 거부. 미충족: 검증 원고 경로·렌더 입력·원격 리소스가 검증본에 결박되지 않음(N01·N02). `scripts/manifest.py:94`, `scripts/render_pdf.py:106`, `scripts/verify_facts.py:925` |
| A | A3 최종 산출물 전체 봉인·변조 검출 | pass | 1 | 코어 렌더가 반환한 모든 artifacts를 작업폴더 내부로 제한해 봉인하고, 사용자 지정 PDF도 저장 경로로 직접 재해시함. 내용의 적합성과는 별개로 출력 파일 바이트 변조 통제는 충족. `scripts/render_pdf.py:119`, `scripts/manifest.py:80`, `tests/test_adversarial.py:1653` |
| A | A4 발급·재발급·최종 판정 단일 경로 | fail | 0 | refs 재발급 막힘, 공개 API로 소유 게이트 자가발급, 재검증 뒤 정상 재렌더 막힘(N06·K04·K05). `scripts/gates.py:282`, `scripts/gates.py:372`, `scripts/manifest.py:66` |
| B | B1 중첩 스키마·필수·타입 | partial | 0.5 | 충족: 주요 required·enum·ID·lead 해시 검사. 미충족: 선언된 type과 이벤트 구조 미검사; 문자열 AB를 그룹 2개로 인정(N09). `scripts/facts_db.py:61`, `assets/facts-schema.json:18`, `assets/facts-schema.json:56`, `scripts/verify_facts.py:488` |
| B | B2 ID·claim_key·증거 참조 | partial | 0.5 | 충족: 중복 ID/문자열 claim_key 및 add 경로 orphan 거부. 미충족: 역참조 불일치·키 재계산·키 충돌(N10·N11). `scripts/facts_db.py:218`, `scripts/facts_db.py:237`, `scripts/verify_facts.py:518` |
| B | B3 동시 쓰기·실패 원자성 | partial | 0.5 | 충족: 개별 JSONL은 fsync+replace, 중앙 단일 writer 명시. 미충족: 두 대장 트랜잭션 없음; 동시 writer 계약 위반 시 갱신 손실(N12). `scripts/facts_db.py:175`, `scripts/facts_db.py:241`, `SKILL.md:69` |
| B | B4 상태 승격·전 행 검사 | partial | 0.5 | 충족: G3 원시행 재검증·반박/강등 후 무재검증 승격 차단. 미충족: [2] 이후 주장·대상·기간 교체를 같은 검증으로 인정(N05). `scripts/verify_facts.py:439`, `scripts/facts_db.py:89`, `scripts/facts_db.py:282` |
| C | C1 원문·재열람·인용·본문 결박 | partial | 0.5 | 충족: local 파일 해시와 태그 값 대조. 미충족: 재열람 미결박 WARN, 의미확장·foreign evidence 통과(K01·N10). `scripts/verify_facts.py:530`, `scripts/verify_facts.py:558`, `scripts/verify_facts.py:355` |
| C | C2 캡처 내용·위치·실체 | partial | 0.5 | 충족: 통상 _captures 경계·PDF 숫자 부분일치 차단. 미충족: 0바이트·실패 재시도 잔존·재구성 경로 우회(N13·N14·K02). `scripts/facts_db.py:109`, `scripts/capture_pdf.py:45`, `scripts/verify_facts.py:554` |
| C | C3 독립성·시점·고위험 | partial | 0.5 | 충족: 명시적 high의 그룹 수·검색 query 부족은 FAIL. 미충족: 실제 원출처 연결·risk 자동 승격·기본소스·시간증거 강제 없음(K06). `scripts/verify_facts.py:477`, `scripts/verify_facts.py:486` |
| C | C4 수치·계산·주장 범위 | partial | 0.5 | 충족: 일반 양수·통화·범위 Decimal 비교와 오태그 차단. 미충족: 부호·SI 접두사 파괴, CAGR 계산/의미 검사 없음(N07·N08·K03). `scripts/verify_facts.py:197`, `scripts/verify_facts.py:239`, `scripts/verify_facts.py:399` |
| D | D1 최초 URL 스킴·호스트·사설망 | pass | 1 | fetch 최초 HTTP(S)·호스트·DNS 응답의 private/loopback/link-local/reserved 등 선언된 차단 범주 검사. 접속 시점·다른 도구는 D2에서 별도 감점. `scripts/fetch.py:157`, `scripts/fetch.py:163`, `scripts/fetch.py:415`, `tests/test_adversarial.py:139` |
| D | D2 리다이렉트·DNS·우회 동일 경계 | fail | 0 | 이미지 다운로드의 두 transport에서 내부 redirect 파일 저장 성공. fetch 사후 IP 검사는 요청 송신을 예방하지 못함(N03). `scripts/harvest_images.py:555`, `scripts/fetch.py:237` |
| D | D3 자원·브라우저·로컬 파일 경계 | fail | 0 | 원고의 script 실행·loopback 리소스 요청을 실측. Chrome no-sandbox, 프로세스 timeout 없음. 이미지 curl 경로는 전량 수신 후 크기 판정(N02·N03). `scripts/render_pdf.py:37`, `scripts/render_pdf.py:58`, `scripts/harvest_images.py:561` |
| D | D4 실패·차단·비본문 구분 | partial | 0.5 | 충족: 짧은 challenge·일반 HTML 4xx·크기·MIME 검사. 미충족: PDF 503을 ok, 무관 RSS 전체를 ok, 검색 산출물에서 partial 미표시(N15·N16·N20). `scripts/fetch.py:195`, `scripts/fetch.py:426`, `scripts/source_index.py:153` |
| E | E1 마커 계약·위반 검출 | partial | 0.5 | 충족: 필수 마커·FIGURES 없음 표기 계약. 미충족: 완전성 검사·파서·실패 envelope 없음(N17). `references/agent-briefs.md:17`, `references/agent-briefs.md:53`, `tests/test_adversarial.py:1301` |
| E | E2 부분실패·timeout·재시도 | partial | 0.5 | 충족: BLOCKED 반환·raw 보존·부분실패 처리 지시. 미충족: deadline·retry 상한/카운터·필수 축 실패 차단 규약 없음(N17). `references/agent-briefs.md:62`, `references/verification-gates.md:20` |
| E | E3 수렴·중복 리드·종료 | partial | 0.5 | 충족: 축별 잔여·2웨이브·3회/12명 상한 명시. 미충족: stable lead ID·성공 관측 기반 무신규 판정·재개 누적 상한 정의 없음(N17). `SKILL.md:71`, `references/research-plan.md:22`, `tests/test_adversarial.py:1291` |
| E | E4 writer 소유권·병합·실패 전파 | partial | 0.5 | 충족: 워커 임시폴더/팀리드 중앙 writer. 미충족: 워커별 F/E-ID namespace·중앙 ID 재매핑·중복 증거 merge 경로 불명확(N11·N12·N17). `SKILL.md:69`, `references/agent-briefs.md:20`, `scripts/facts_db.py:213` |
| F | F1 SKILL↔게이트 판정 강도 | fail | 0 | 전부 필수인 high-risk 조건 일부가 WARN이며, G5c 내용검사 강제 주장과 달리 검사자가 없음(K03·K06). `SKILL.md:85`, `SKILL.md:110`, `scripts/verify_facts.py:493`, `scripts/gates.py:43` |
| F | F2 references↔CLI·반환 | partial | 0.5 | 충족: 수정된 G3 build/[4b] extend 설명·핵심 CLI 일치. 미충족: 실패 캡처 차단 보증·분쟁 사실 병기·fetch JSON 완전성 불일치(N13·N19·K07). `references/evidence-capture.md:16`, `references/report-format.md:16`, `scripts/fetch.py:661` |
| F | F3 search 진입·인계 | partial | 0.5 | 충족: 수집만/보고서 승격 시 대장 재생성 경계 명시. 미충족: 동일 본문 URL 덮어쓰기·partial와 실패 정보 소실(N20·N22). `codes/mdr-search/SKILL.md:12`, `SKILL.md:28`, `scripts/fetch.py:521` |
| F | F4 HWPX 경계·완료 | partial | 0.5 | 충족: standalone·비검증·봉인 미연동을 명시하여 HWPX를 G5 보호물로 가장하지 않음. 미충족: 코어 원고는 split의 로마숫자 계약과 달라 1개 서문으로만 인계(N21). `codes/mdr-hwpx/SKILL.md:14`, `codes/mdr-hwpx/SKILL.md:109`, `codes/mdr-hwpx/scripts/build_hwpx.py:599` |
| G | G1 기존 테스트 실행 | pass | 1 | 지정 두 테스트 직접 실행 성공: 71/71 및 E2E OK. `tests/test_adversarial.py:1681`, `tests/test_e2e.py:174` |
| G | G2 실제 CLI·영수증 전체 경로 | partial | 0.5 | 충족: 현 E2E가 G3·렌더·G5 CLI를 실행하므로 1차 리뷰의 함수 대체 문제는 수정됨. 미충족: 다른 원고·조상 실패·2회차 재렌더·G5c 누락을 검증하지 않음. `tests/test_e2e.py:130`, `tests/test_e2e.py:141`, `tests/test_e2e.py:157` |
| G | G3 악성 스키마·동시성·통신 | partial | 0.5 | 충족: 중복 ID·일부 스키마·승격 공격 fixture. 미충족: type 혼입·양방향 참조·쓰기 중간 실패·실제 워커 결과 파싱 시험 없음. `tests/test_adversarial.py:772`, `tests/test_adversarial.py:1012`, `tests/test_adversarial.py:1301` |
| G | G4 SSRF·캡처·출력 변조 회귀 | partial | 0.5 | 충족: redirect/IP·캡처 경계·manifest 변조 검사. 미충족: 네트워크 mock은 사후 exception만 검증하며 이미 도달한 요청을 세지 않음; harvest·활성 HTML·기존 PNG 재사용 누락. `tests/test_adversarial.py:281`, `tests/test_adversarial.py:428`, `tests/test_adversarial.py:1596` |
| H | H1 합법 수정 후 재검증 | fail | 0 | refs 갱신과 PDF 존재 상태의 G3 복귀가 모두 정상 진행을 막음(N06·K04). `scripts/gates.py:282`, `scripts/manifest.py:39`, `scripts/render_pdf.py:118` |
| H | H2 최소 의존성·플랫폼·재개 | partial | 0.5 | 충족: Windows에서 기존 E2E 동작·목적별 standalone 경계·설치 allowlist. 미충족: 실질 필수 curl은 SOFT, fetch는 미설치 시 성공 transport가 없고 재개 리비전 불명확. `scripts/preflight.py:7`, `scripts/fetch.py:229`, `scripts/install.py:28` |
| H | H3 수동 검토 실행성·증적 | partial | 0.5 | 충족: lead 재열람 이벤트·raw·뷰포트 캡처 recipe·preview 생성. 미충족: G4 evidence 문자열만으로 모든 페이지 검토를 대체 가능하고 검토 PDF 해시/페이지 coverage가 필수가 아님. `references/evidence-capture.md:29`, `scripts/gates.py:325`, `scripts/preview_pdf.py:22` |
| H | H4 최종 판정 자동화·재현성 | fail | 0 | G5가 의미·계산·PDF 내부 태그/링크/캡처와 동일 revision 전체를 확인하는 finalize 경로가 아님(N01·N02·N04·K03·K05). `scripts/manifest.py:207`, `SKILL.md:108` |

| 차원 | 배점 | 항목값 합/항목수 | 획득점 |
|---|---:|---:|---:|
| A | 20 | 2/4 | 10 |
| B | 15 | 2/4 | 7.5 |
| C | 15 | 2/4 | 7.5 |
| D | 15 | 1.5/4 | 5.625 |
| E | 10 | 2/4 | 5 |
| F | 10 | 1.5/4 | 3.75 |
| G | 10 | 2.5/4 | 6.25 |
| H | 5 | 1/4 | 1.25 |
| **합계** | **100** | **32개 적용** | **46.875** |

### 점수와 독립적인 결함 집계

아래는 논리적 결함 ID 단위다. 한 결함의 여러 재현 변형·테스트 누락은 별도로 중복 집계하지 않는다.

| 구분 | 치명 | 중대 | 경미 | 합계 |
|---|---:|---:|---:|---:|
| 신규 N01~N22 | 4 | 17 | 1 | 22 |
| 기지 K01~K07 | 0 | 6 | 1 | 7 |
| **전체** | **4** | **23** | **2** | **29** |

## 3. 결함 목록 — 심각도순

### N01. G3가 검사한 원고와 봉인·렌더한 원고가 다른데 최종 PASS — 치명 / [신규]

- **공격·재현:** 정상 대장 `F001=45 USD`와 정상 원고를 만든다. 정상 원고를 `audit/reviewed.md`에 복사하고, 작업폴더의 `report.md`는 `999 USD(F001)`로 바꾼다. 정상 G0/G1/[2] 뒤 `verify_facts.py audit/reviewed.md <wd>` → `render_pdf.py <wd>/report.md` → G4 기록 → `manifest.py verify <wd>`를 실행한다. 실제 원고 직접 검사는 `[값불일치] FAIL`인데, 위 **G3/render/G5는 모두 exit 0**, PDF에 `999`가 들어갔다. 소유 게이트 위조나 함수 직접 렌더 없이 성립한다.
- **근거:** `scripts/verify_facts.py:925`는 임의 첫 인자를 검사하고 `scripts/verify_facts.py:938`은 별도 work_dir을 봉인한다. `scripts/manifest.py:38`은 이름 `report.md`만 스캔한다. `scripts/render_pdf.py:106`, `scripts/render_pdf.py:110`은 입력 경로와 G3 검증 원고의 동일성을 확인하지 않는다. G3 result_summary는 판정/statistics의 해시이지 검토한 문서 경로·내용 해시가 아니다(`scripts/verify_facts.py:831`, `scripts/verify_facts.py:941`).
- **최소 수정안:** G3 영수증에 정규화된 입력 원고 경로·해시를 필수 결박하고, 렌더 직전에 그 정확한 원고와 리소스 집합을 다시 확인한다.

### N02. 오프라인 렌더가 원격 자원을 읽고 원고 script를 실행 — 치명 / [신규]

- **공격·재현:** 원고에 loopback 테스트 서버의 PNG URL과 정상 `[그림] 출처:` 캡션, `<script>document.body.append("UNREVIEWED_SCRIPT_OUTPUT");</script>`를 넣었다. G3 CLI가 통과했고, 렌더 중 서버는 `/render-image` GET을 받았다. PDF 텍스트에서 script가 추가한 문자열을 확인했다. G4 수동 영수증 뒤 **G5도 exit 0**이었다. 원격 이미지가 G3 이후 바뀌거나 script가 숫자를 조립하면 원고 숫자 검사와 원문 봉인 밖에서 결과가 바뀐다.
- **근거:** 외부 URL/data URI는 실재 검사에서도 무조건 True(`scripts/verify_facts.py:663`). pandoc에 raw HTML·원격 리소스를 제한하지 않은 `--embed-resources`를 전달하고(`scripts/render_pdf.py:37`), Chrome을 `--no-sandbox`로 실행한다(`scripts/render_pdf.py:58`). 두 subprocess 모두 timeout이 없다(`scripts/render_pdf.py:41`, `scripts/render_pdf.py:63`). 오프라인 약속은 `scripts/render_pdf.py:5`, `references/report-format.md:53`이다.
- **최소 수정안:** G3 전 리소스를 허용된 로컬 스냅샷으로 고정하고 active HTML/script를 제거하며, 렌더 프로세스의 네트워크·로컬 파일 범위·실행시간을 제한한다.

### N03. 이미지 수집은 SSRF redirect를 그대로 따라가며 fetch의 사후 IP 검사는 송신을 막지 못함 — 치명 / [신규]

- **공격·재현:** 직접 띄운 서버에서 공인 호스트 역할의 URL을 `http://127.0.0.1:<port>/private`로 리다이렉트했다. 최초 DNS 검사에는 공인 fixture IP를 반환하고 실제 연결은 테스트 서버로 연결했다(urllib는 DNS fixture, curl은 fixture host의 resolve 옵션). **harvest의 curl·urllib 두 경로 모두 내부 PNG 19,442바이트를 저장하고 `ok:true`**를 반환했다. 별도 fetch 실험에서는 사설 primary_ip로 `SsrfBlocked`가 발생했지만 서버가 `/private-probe` 요청을 이미 받았다. 사후 검출을 사전 송신 차단으로 해석하면 안 된다.
- **근거:** `scripts/harvest_images.py:557`의 검사는 최초 URL뿐이고 `scripts/harvest_images.py:559`, `scripts/harvest_images.py:565`는 자동 redirect를 허용하며 최종 IP 검사도 없다. curl 크기 제한도 `r.content` 전체 수신 이후다(`scripts/harvest_images.py:561`, `scripts/harvest_images.py:572`). fetch는 `creq.get` 다음에 IP를 검사하고, proxy 환경변수가 하나라도 있으면 그 검사마저 생략한다(`scripts/fetch.py:182`, `scripts/fetch.py:237`). search도 자동 redirect 및 curl 미설치 시 보안검사 무력화 경로가 있다(`scripts/search.py:26`, `scripts/search.py:43`).
- **최소 수정안:** 수집 도구가 공통 transport를 사용하게 하고, 검증 IP에 연결을 고정한 상태로 모든 redirect 홉·proxy 경로·스트리밍 크기를 통제한다.

### N04. 상위 게이트 실패·계획 변경 후에도 기존 하위 영수증으로 G5 재통과 — 치명 / [신규]

- **공격·재현:** 정상 G5까지 완료한 임시 조사의 G1에 exit 1 재시도 결과를 append하고 승인 계획도 변경했다. `check G3`는 G1 실패, `check G4`는 N8 계획 드리프트로 각각 실패했지만 **`manifest.py verify`는 다시 exit 0과 G5 PASS**를 기록했다. manifest 대상 외 audit만 바뀌므로 파일 해시 검사로는 보완되지 않는다.
- **근거:** `scripts/gates.py:43`의 관계표와 `scripts/gates.py:275`는 직접 선행만 확인한다. `require_receipt`는 조상·발급 순서·리비전을 확인하지 않고 해당 gate의 마지막 행만 확인한다(`scripts/gates.py:248`). G5는 [4b]·G4만 확인하고 G4의 N8 로직을 다시 호출하지 않는다(`scripts/manifest.py:210`, `scripts/gates.py:288`). `g3_result_summary_sha256`는 [4b]에 저장만 되고 G5가 대조하지 않는다(`scripts/render_pdf.py:129`).
- **최소 수정안:** 영수증을 부모 receipt ID·입력 revision에 결박하고, 최종 판정에서 전체 의존 체인의 최신 성공·현재 입력을 재검증한다.

### N05. [2] 재검증 이후 주장·대상·기간을 바꿔도 재열람이 유효 — 중대 / [신규]

- **공격·재현:** [2] 기록 후 F001의 claim, entity, entity_id, period, definition을 Acme/2024에서 Beta/2035 전망으로 바꾸되 raw·unit·lead 이벤트는 유지했다. **confirmed_digest 동일, [2] 유효, G3 CLI exit 0**이었다. 원문 문장 해시만 붙이는 P0 수정으로는 이 대장 수정의 재검증 무효화가 보장되지 않는다.
- **근거:** `scripts/facts_db.py:282`의 투영은 id·raw·unit·lead 이벤트뿐이며 `context`, `claim`, `risk`, `grade`, 증거 연결을 제외한다. `scripts/gates.py:222`가 이 투영만 비교한다. 기업 동일성 고정 약속은 `references/entity-identity.md:20`이다.
- **최소 수정안:** 대장 주장의 의미를 바꾸는 context/claim/risk/증거 provenance를 검증 다이제스트에 포함하고, 허용된 증거 추가만 별도 변화로 처리한다.

### N06. 정상 G3 재실행이 이전 report.pdf를 봉인해 재렌더를 영구 거부 — 중대 / [신규]

- **공격·재현:** 정상 G3→렌더를 끝낸 뒤 원고에 설명 문단만 추가했다. G3 재실행은 exit 0이지만 다음 렌더는 **`changed: ['report.pdf']`로 exit 1**이다. G3가 직전 PDF를 입력 기준선에 포함하고 새 렌더가 그것을 바꾸기 때문이다. 동일한 복귀 절차를 반복하면 같은 실패가 재발한다.
- **근거:** `scripts/manifest.py:39`, `scripts/manifest.py:66`이 존재하는 이전 PDF까지 기준선으로 넣는다. `scripts/render_pdf.py:53`은 이전 PDF 삭제 후 새로 쓰고 `scripts/render_pdf.py:118`은 그 뒤 extend한다. `scripts/manifest.py:109`는 이전 PDF의 변경을 거부한다. 문서는 파일 변경 시 G3 복귀를 안내한다(`references/verification-gates.md:70`).
- **최소 수정안:** G3 입력과 revision별 렌더 산출물을 분리하고 새 revision의 출력은 staging에서 생성한 뒤 검증·승격한다.

### N07. 음수의 부호가 사라져 손실과 이익이 같은 값으로 통과 — 중대 / [신규]

- **공격·재현:** 대장 raw `-45`, 본문 `45 USD(F001)`로 G3를 실행하면 경고·실패 없이 PASS. 반대 방향인 대장 `45`, 본문 `Loss -45 USD(F001)`도 `check_bound_numbers`의 failures/warnings가 모두 빈 배열이다.
- **근거:** 본문 `_NUM_CORE`에는 부호가 없고(`scripts/verify_facts.py:59`), 대장 `_vals`는 하이픈을 범위 구분자로 split한 뒤 빈 조각을 지워 `-45`를 `[45]`로 만든다(`scripts/verify_facts.py:250`).
- **최소 수정안:** 부호 있는 scalar와 range를 구분하는 파서를 사용하고 대장↔본문 비교에서 sign을 보존한다.

### N08. SI 접두사 대소문자 소실과 µW 누락으로 전력 수치 검증 붕괴 — 중대 / [신규]

- **공격·재현:** 대장 `45 mW`에 본문 `45 MW(F001)`를 넣어도 G3가 경고 없이 PASS했다. `45 µW`에 `999 µW(F001)`도 숫자 검사 실패·경고가 없다. 전자는 milli와 mega의 10억 배 차이를 없애고, 후자는 EH-PMIC에서 중요한 단위를 검사 대상에서 뺀다.
- **근거:** `scripts/verify_facts.py:65`의 단위 목록은 µW/uW/mW 구분을 갖지 않으며 본문 regex가 re.I다(`scripts/verify_facts.py:79`). `_resolve_unit`은 lower()로 `mW`와 `MW`를 모두 `mw`의 mega 배수로 해석한다(`scripts/verify_facts.py:174`, `scripts/verify_facts.py:201`).
- **최소 수정안:** SI 접두사는 대소문자를 보존하고 W·mW·µW/uW 및 Wh 계열을 명시적으로 정규화한다.

### N09. 경량 스키마가 타입을 읽지 않아 문자열 AB로 독립그룹 2개 조작 — 중대 / [신규]

- **공격·재현:** `validate_fact`는 claim=42, context.entity=123, period=false, independent_groups="AB", 잘못된 이벤트 at를 받아들였다. 별도 정상 수치 fixture에서 `risk=high`, `independent_groups="AB"`, `counter_search={"query":" "}`, `primary_source_ref="E999"`, `valid_at="not-a-date"`로 G3가 **경고 없이 PASS**했다. 이 중 문자열 그룹 허용은 스키마에 선언된 array 타입을 어긴 경우다.
- **근거:** `assets/facts-schema.json:18`, `assets/facts-schema.json:22`, `assets/facts-schema.json:53`, `assets/facts-schema.json:56`의 type을 `scripts/facts_db.py:61`은 검사하지 않는다. `scripts/verify_facts.py:488`은 문자열의 글자들을 그룹으로 세며 query·시점은 truthiness만 본다(`scripts/verify_facts.py:491`).
- **최소 수정안:** 현재 선언된 스키마의 중첩 type·배열 item·이벤트 구조·공백값을 실제로 검증하고, 새 P0 필드도 동일 검증기에 연결한다.

### N10. evidence.fact_id 역참조가 틀려도 남의 증거를 정상 근거로 인정 — 중대 / [신규]

- **공격·재현:** 정상 `F001.evidence_ids=[E001]`을 유지하면서 `E001.fact_id=F999`로 바꿨다. F999는 존재하지 않아도 전체 G3가 **경고 없이 PASS**했다. 대장 직접 join·이행 과정의 잘못된 ID 매핑을 검출하지 못한다.
- **근거:** evidence 검증은 fact_id 형식만 검사한다(`scripts/facts_db.py:139`). add_evidence의 존재 검사는 해당 API를 사용할 때만 적용된다(`scripts/facts_db.py:237`). G3는 모든 evidence를 재검증하지만(`scripts/verify_facts.py:460`) F→E 존재 확인 뒤 `E.fact_id == F.id` 및 E→F 존재를 확인하지 않는다(`scripts/verify_facts.py:518`).
- **최소 수정안:** 전체 대장 검증 시 양방향 F↔E 연결의 존재·일치·누락을 검사하고 허용할 공유 evidence 모델을 명시한다.

### N11. claim_key가 의미와 분리되고 구분자 치환으로 다른 대상을 충돌시킴 — 중대 / [신규]

- **공격·재현:** 동일 context/값의 fact를 F002·임의 claim_key로 add_fact하면 별개 fact로 들어가고 G3도 PASS한다. 반대로 entity `A|B`와 `A/B`는 같은 키가 된다. entity_id와 연결/별도 definition이 다른 관측도 현재 키 구성에서는 충돌할 수 있다. 재조사 diff의 dict 변환은 이미 중복된 키를 마지막 행으로 덮는다.
- **근거:** `scripts/facts_db.py:155`는 `|`를 `/`로 손실 치환하고 context의 여섯 필드만 쓴다. `scripts/facts_db.py:212`는 제공된 claim_key를 신뢰하고 재계산하지 않는다. `scripts/facts_db.py:298`은 중복키를 검출하지 않고 dict로 만든다. 서로 다른 definition은 다른 claim_key라는 문서와도 어긋난다(`references/entity-identity.md:29`). 오류 메시지가 지시하는 `merge_evidence` 함수도 구현에 없다(`scripts/facts_db.py:222`).
- **최소 수정안:** 식별자·정의까지 포함한 정규화 tuple의 무손실 직렬화로 키를 계산·대조하고 중복 입력은 명시적 merge/diff 오류로 처리한다.

### N12. JSONL 파일별 원자성이 두 대장 일관성·동시 갱신을 보장하지 않음 — 중대 / [신규]

- **공격·재현:** add_evidence의 evidence 저장은 성공시키고 뒤 facts 저장만 OSError로 실패시켰다. 결과는 **evidence 2건, fact에는 E001만 연결**, 그 상태로 G3 PASS였다. 추가로 두 writer의 read가 끝난 뒤 쓰기 자체는 순차 실행하도록 통제했는데 두 add_fact가 모두 F001을 반환하고 디스크에는 1행만 남았다. 중앙 단일 writer 규약은 인정한다. 동시성 실험은 그 규약 위반 시의 영향이며, 주 결함인 두 파일 중간 실패는 단일 writer에서도 발생한다.
- **근거:** 개별 replace는 원자적이지만(`scripts/facts_db.py:175`) read-modify-write 잠금이 없다(`scripts/facts_db.py:211`). `scripts/facts_db.py:241`과 `scripts/facts_db.py:245` 사이에는 rollback·commit journal이 없다. G3는 역방향 연결 누락도 확인하지 않는다(N10).
- **최소 수정안:** 단일 트랜잭션 저장소 또는 두 파일 commit journal을 사용하고 writer lock·복구 가능한 실패 상태를 둔다.

### N13. 캡처 재시도 실패가 예전 성공 PNG를 남기고 CLI도 exit 0 — 중대 / [신규]

- **공격·재현:** 동일 E001.png로 숫자 45를 성공 캡처한 뒤 999를 재요청한다. 함수는 `ok:false`와 E001.FAILED.png를 반환하지만 **옛 E001.png는 동일 해시로 남고 G3는 PASS**, CLI도 exit 0이다. 변경된 주장에 대한 새 캡처 실패가 이전 이미지를 성공 증빙처럼 재사용하게 한다.
- **근거:** `scripts/capture_pdf.py:93`은 실패 sidecar만 쓰며 기존 out_png를 무효화하지 않는다. `scripts/capture_pdf.py:161`은 결과를 print만 하고 실패 종료코드를 설정하지 않는다. G3는 `.exists()`만 확인한다(`scripts/verify_facts.py:554`). 실패 시 out_png가 없어 재작업 전 confirmed가 불가능하다는 약속은 재시도에는 거짓이다(`references/evidence-capture.md:16`).
- **최소 수정안:** 요청/입력 해시에 맞는 캡처 성공 기록을 요구하고, 실패 재시도 시 이전 성공본을 현재 증빙에서 제외하며 CLI를 nonzero로 종료한다.

### N14. _reconstructed/../ 경로로 재구성 이미지를 증빙 폴더에 직접 생성 — 중대 / [신규]

- **공격·재현:** `out_png=<wd>/_captures/_reconstructed/../forged.png`로 reconstruct_excerpt를 호출하면 저장에 성공한다. 대장에는 정규 경로 `_captures/forged.png`를 넣는다. **check_capture_path는 None, 전체 G3도 PASS**였다. 사후 파일 복사 없이 생성기의 자체 경계 검사를 우회한다.
- **근거:** `scripts/capture_web.py:28`은 resolve 전 경로 조각 중 `_reconstructed` 존재만 검사하고 `scripts/capture_web.py:46`은 OS가 정규화한 경로에 저장한다. 후속 경계는 정상화된 별도 문자열만 받으므로 재구성 유래가 사라진다(`scripts/facts_db.py:117`).
- **최소 수정안:** 생성 전 resolve한 목적지가 승인된 reconstructed root 내부인지 검사하고 산출물 유형·입력 해시 provenance를 증거 검증에 연결한다.

### N15. PDF fast path가 HTTP 오류 상태 검사를 우회 — 중대 / [신규]

- **공격·재현:** `_fetch_once` 형태의 응답 fixture에 status=503, raw=`%PDF-...`, is_pdf=true를 넣어 실제 fetch 사다리에 전달했다. 반환은 **status=ok, http_status=503, note=pdf**였다. 실제 PDF로 포맷된 접근오류·장애 안내문도 원문 확보로 승격된다.
- **근거:** `_fetch_once`는 MIME/바이트 검사 후 상태코드와 무관하게 ok=True를 만든다(`scripts/fetch.py:260`, `scripts/fetch.py:271`). `scripts/fetch.py:426`은 validate_body보다 먼저 반환한다. 상태코드 우선 약속과 일반 HTML 검사는 `references/source-ladder.md:57`, `scripts/fetch.py:197`이다.
- **최소 수정안:** PDF/HTML 분기 전에 허용 HTTP 성공 상태를 공통 검사하고 PDF도 파싱·본문 유효성 검사를 통과해야 성공으로 기록한다.

### N16. 요청 기사와 무관한 RSS 전체 피드가 원문 확보 ok가 됨 — 중대 / [신규]

- **공격·재현:** missing-article URL에 대한 RSS 후보로 다른 기사 두 건만 담긴 4천 자 이상의 XML을 반환했다. 사다리는 **status=ok, note=rss, final_url=/feed**로 끝났다. archived_url은 남지만 대상 기사 존재·일치 검사는 없고, 이후 더 정확한 원문 탐색을 중단한다.
- **근거:** `scripts/fetch.py:317`은 사이트 전체 feed를 합성하고 `scripts/fetch.py:378`은 본문 그대로 전달한다. `scripts/fetch.py:204`의 길이 기준과 `scripts/fetch.py:431`의 조기 성공은 entry URL/GUID/제목 일치를 확인하지 않는다.
- **최소 수정안:** RSS에서 요청 URL·GUID에 대응하는 entry만 추출하고 미일치 feed는 탐색 자료 또는 partial로 남긴다.

### N17. 워커 마커는 기계 파싱 약속뿐이며 완료·실패·수렴의 입력 계약이 없음 — 중대 / [신규]

- **공격·재현 절차(정적 계약 검증):** raw A에는 `BLOCKED: timeout`만, raw B에는 FIGURES/EXPAND를 빠뜨린 EVIDENCE만, raw C에는 같은 URL을 이름만 바꾼 LEAD를 넣는다. 현재 저장소에는 이들을 받는 join/마커 파서·완전성 검사·상태 전이 실행기가 없다. 누락 EXPAND를 리드 0으로 보거나 실패한 웨이브를 무신규로 세어도 자동 위반 검출이 없고, 이름 변경 리드는 dedup 동등성 정의도 없다. 두 워커가 모두 F001/E001을 반환하면 중앙 add는 충돌을 거부하지만 인사이트 F-ID까지 재매핑할 규약이 없다. 실제 모델이 반드시 누락한다고 주장하는 것이 아니라, 어떤 처리가 유효한지/언제 실패해야 하는지가 계약으로 닫혀 있지 않다는 결함이다.
- **근거:** “팀리드가 기계 파싱”과 nested fact/evidence 반환은 `references/agent-briefs.md:17`, `references/agent-briefs.md:20`; BLOCKED와 부분 보존은 `references/agent-briefs.md:62`; 제한적 재요청은 `references/verification-gates.md:21`; 수렴·즉시 스폰은 `SKILL.md:71`. `rg -n 'EVIDENCE|CLAIMS|BLOCKED|DEAD END|EXPAND' codes/market-deep-research/scripts`에는 처리기가 없다. 테스트는 실제 worker 결과 대신 문서의 AXIS 문자열을 검사한다(`tests/test_adversarial.py:1301`).
- **최소 수정안:** run/task/lead ID와 완료상태·필수 섹션·부분결과·실패 사유를 가진 envelope 및 join 검증기를 두고 성공 웨이브 기준·누적 retry/depth cap·ID 재매핑을 정의한다.

### N18. 부록 마커를 한 번만 앞당기면 뒤 결론의 무태그·고위험·캡처 검사가 완화됨 — 중대 / [신규]

- **공격·재현:** 본문에 제목과 정상 이미지 하나를 둔 뒤 APPENDIX 마커를 하나 배치하고, 그 뒤 `# Executive conclusions`와 `Market 999 USD.`를 넣었다. **G3 PASS**, 무태그 수치는 `[부록무태그] WARN`만 남고 body_tags=0이다. 중복 마커나 본문 공백도 아니므로 기존 방어를 피한다. 부록에서도 본문과 같은 태그 검사는 유지되지만, 무태그 및 used 기반 high-risk/capture 조건은 다른 문제다.
- **근거:** `scripts/verify_facts.py:115`가 첫 마커부터 전부 부록으로 정한다. used는 그 앞만 세고(`scripts/verify_facts.py:783`), 뒤 숫자는 lenient 검사한다(`scripts/verify_facts.py:806`). 중복/공백만 차단하며 실제 승인 부록 위치는 확인하지 않는다(`scripts/verify_facts.py:792`).
- **최소 수정안:** 승인 목차의 실제 부록 헤딩과 마커 위치를 결박하고 결과·권고 구역의 주장에는 부록 면제를 적용하지 않는다.

### N19. 문서가 요구하는 disputed 수치 병기가 G3에서 금지됨 — 중대 / [신규]

- **공격·재현:** 반박·정의차를 정직하게 기록하려고 F001을 disputed로 내리고 상충 절에서 `45 USD(F001)`로 인용하면 `[미확정] status=disputed`로 FAIL한다. 숫자에서 태그를 빼면 무태그 FAIL이다. 따라서 핵심 본문에서 근거를 단 채 상충 상태를 표현할 정식 통로가 없다.
- **근거:** `references/report-format.md:16`은 상반 수치·disputed 병기를 요구하지만 `scripts/verify_facts.py:355`는 모든 본문 태그에 confirmed만 허용한다. `references/verification-gates.md:91`은 disputed를 정상 상태로 정의한다.
- **최소 수정안:** 상충 인용의 provenance 확인과 주장 진실성 상태를 분리하고, 명시적인 disputed 문맥에서는 출처 결박된 병기를 허용한다.

### N20. 동일 본문을 가진 서로 다른 URL의 provenance가 덮어써지고 partial도 산출물에 숨음 — 중대 / [신규]

- **공격·재현:** URL A와 B가 같은 축약 본문을 반환하도록 각각 fetch.save했다. **meta는 한 개, source_index는 B 한 행만** 남았다. 그 행의 status=partial이지만 sources.md에는 partial 표시가 전혀 없다. 동일 기사 전재 관계·접근 경로를 보존해야 하는 후속 조사에 원본 URL 집합이 전달되지 않는다.
- **근거:** raw 해시 앞 12자리로 메타 파일명까지 결정하고 매번 덮어쓴다(`scripts/fetch.py:492`, `scripts/fetch.py:508`, `scripts/fetch.py:521`). 인덱스는 sha별 한 행이고(`scripts/source_index.py:108`), status를 읽어도 표·발췌에는 출력하지 않는다(`scripts/source_index.py:83`, `scripts/source_index.py:150`). `codes/mdr-search/SKILL.md:33`은 사용자에게 이 목록을 결과로 제공한다.
- **최소 수정안:** blob 중복 제거와 URL별 retrieval/provenance 기록을 분리하고 sources.md에 ok/partial·대체표현물 여부를 표시한다.

### N21. 코어 보고서를 HWPX 부별 워크플로에 그대로 넘기면 전부 서문 한 파일 — 중대 / [신규]

- **공격·재현:** 커밋된 `tests/test_e2e.py`의 REPORT를 `build_hwpx.py split report.md --out manuscript`에 넣었다. **exit 0, 산출물은 `00_서문.md` 하나**였다. 코어의 Executive Summary/테마별 본론 등 일반 헤딩을 로마숫자 부로 변환하는 인계 절차가 없으므로 부별 병렬 빌드·부 간 정합성 검토의 전제가 사라진다. 원문 내용 자체가 삭제된 것은 아니다.
- **근거:** 목적 라우팅은 `SKILL.md:27`; 코어 원고 사례는 `tests/test_e2e.py:50`; HWPX 분할 계약은 `codes/mdr-hwpx/SKILL.md:38`, 실제 regex는 `codes/mdr-hwpx/scripts/build_hwpx.py:71`. 매칭이 없어도 서문 파일을 쓰고 성공한다(`codes/mdr-hwpx/scripts/build_hwpx.py:599`, `codes/mdr-hwpx/scripts/build_hwpx.py:620`).
- **최소 수정안:** 코어→HWPX 인계 시 승인 목차와 부 ID를 보존하는 변환기를 두고, 기대 부 수와 split 결과가 다르면 명시 실패한다.

### K01. F130 유형의 의미확장을 태그·숫자 검사로 막을 수 없음 — 중대 / [기지(旣知)]

- **공격·재현:** 정상 수치 원고에 근거 없는 “Battery-free sensors have been commercially deployed.”를 추가했다. 전체 G3는 경고 없이 PASS했다. 실제 F130 사례는 실전 수정방안 29행의 P0이며, 이번 리뷰는 해당 보고서 원문 사실성을 새로 심사한 것이 아니다.
- **근거:** `scripts/verify_facts.py:355`는 등장한 태그의 상태만 확인하고 `scripts/verify_facts.py:368`은 인식할 숫자가 없으면 건너뛴다. 본문 전체 주장 목록·원문 의미 검토는 `scripts/verify_facts.py:802`의 검사 조합에 없다. 기지 문서: `F:/Claude/work/navion-market-research/keri-business-model/market-deep-research_스킬_수정방안.md:29`.
- **최소 수정안:** 제안된 문장별 claim-review를 전 주장 inventory 및 검토 원고·evidence revision에 결박하고 미지원 속성의 최종 게재를 차단한다.

### K02. E130 유형의 차단·백지 캡처를 유효 증빙으로 인정 — 중대 / [기지(旣知)]

- **공격·재현:** 정상 E001.png를 0바이트로 바꾸었는데 전체 G3가 PASS했다. 실제 Cloudflare E130 사례를 그대로 중복 재현한 것은 아니며, 동일한 파일 존재 통제의 한계를 더 작은 fixture로 확인했다.
- **근거:** `scripts/verify_facts.py:554`는 `.exists()`뿐이며 디코딩·크기·내용·검토 기록·이미지 자체 digest를 확인하지 않는다. `references/verification-gates.md:37`도 백지 자동 검출 불가를 인정한다. 기지 문서: `F:/Claude/work/navion-market-research/keri-business-model/market-deep-research_스킬_수정방안.md:30`.
- **최소 수정안:** capture_review를 이미지 해시에 결박하고 디코딩·차단/본문 상태·주장 가시성 검토를 최종 증빙 수에 반영한다.

### K03. F091 CAGR 미검산뿐 아니라 G5c 산출물 자체도 강제되지 않음 — 중대 / [기지(旣知)]

- **공격·재현:** 대장 raw=`4.5(2025)->12.8(2035)`에 본문 CAGR `17.8%(F001)`를 넣으면 G3는 `[값미대조] WARN`만 남기고 PASS한다. 별도 완주 fixture는 `audit/verify-*.md` **0개로 G5 PASS**했다. 산술 스크립트만 추가하고 최종 검사에 연결하지 않으면 미실행 우회가 남는다.
- **근거:** free-string 파싱 실패를 허용하는 `scripts/verify_facts.py:239`, `scripts/verify_facts.py:400`; G5c가 렌더/G5의 선행이 아닌 `scripts/gates.py:43`; audit를 추적하지 않는 `scripts/manifest.py:29`. 내용검사로 강제된다는 약속은 `SKILL.md:110`, `references/verification-gates.md:81`. 기지 문서 P0: `F:/Claude/work/navion-market-research/keri-business-model/market-deep-research_스킬_수정방안.md:31`.
- **최소 수정안:** 구조화 계산 검사와 입력 다이제스트를 G3 전 필수 단계로 만들고, 대상별 계산 결과의 존재·완전성·현재 revision을 최종 판정에서 요구한다.

### K04. 변경된 refs를 합법적으로 재검증해도 [2]/G4 영수증 재발급 불가 — 중대 / [기지(旣知)]

- **공격·재현:** [2]에 `audit/lead-review.md` v1을 refs로 기록한 뒤 v2로 수정하고 새 evidence/refs로 record [2]를 호출했다. **`[2] 선행조건 미충족: refs 해시 불일치`**로 거부됐다. confirmed 투영 변경만으로 [2]를 재기록하는 경우와 구별해야 한다. 현재 코드는 그 경우 재발급은 허용하며, 모든 재기록이 실패하는 것은 아니다.
- **근거:** `scripts/gates.py:336`이 check_gate를 부르고, `scripts/gates.py:282`가 같은 gate의 이전 성공 refs까지 검사한다. 기지 문서: `F:/Claude/work/navion-market-research/keri-business-model/market-deep-research_스킬_수정방안.md:32` 및 10절.
- **최소 수정안:** 현재 영수증 검사와 새 발급의 선행조건 검사를 분리하고 supersedes·revision으로 과거 기록을 보존한다.

### K05. 소유 스크립트만 발급한다는 보증이 공개 API·수정 가능한 JSONL 앞에서 무너짐 — 중대 / [기지]

- **공격·재현:** 빈 조사폴더에서 `gates.record_script_result(wp,"G3",0,"unexecuted")`를 호출하면 검사 실행 없이 G3가 성공 영수증으로 인정된다. 같은 권한으로 원장을 편집할 수 있는 프로세스 사이에 보안 소유권이 있다는 주장도 성립하지 않는다. CLI 한 경로만 차단하는 것은 실수 방지로는 유효하다.
- **근거:** `scripts/gates.py:372`에는 호출자·소유자·선행 검사가 없고 `scripts/gates.py:121`은 평문 append다. CLI 차단만 `scripts/gates.py:550`에 있다. 기지 맥락: `_planning/council-2026-08-22/review-codex-modularize.md:68`의 M2 절(제목과 해당 문단 기준).
- **최소 수정안:** 동일 프로세스/파일 권한의 신뢰 한계를 문서화하고, 최종 승격은 영수증 존재 대신 현재 입력의 실제 검증 결과를 한 경로에서 계산한다.

### K06. high-risk의 “전부 필수”와 실제 WARN·자가신고 독립성이 불일치 — 중대 / [기지]

- **공격·재현:** high-risk에 유효 배열 `independent_groups=["a","b"]`와 임의 query만 주면 원출처 하나여도 그룹 수를 충족한다. primary_source_ref·시점이 없으면 WARN일 뿐이고, risk를 normal로 두면 hard 조건이 적용되지 않는다. 스키마 위반 없이도 성립하므로 N09의 타입 우회와 별개다. 기존 E2E도 high fact에 증거 하나를 넣고 그룹 두 개를 선언한다.
- **근거:** 전부 통과/불통과 disputed는 `SKILL.md:85`. WARN 구현은 `scripts/verify_facts.py:493`, risk 경고뿐인 경로는 `scripts/verify_facts.py:477`. 그룹을 evidence/observer_group에 조인하지 않는 코드는 `scripts/verify_facts.py:488`; fixture는 `tests/test_e2e.py:101`, `tests/test_e2e.py:111`. 기지 문서: `F:/Claude/work/navion-market-research/keri-business-model/market-deep-research_스킬_수정방안.md:35` 및 7.2·10.1절.
- **최소 수정안:** 원생산자·전재 관계에서 독립 그룹을 계산하고 고위험 판정과 필수/WARN 정책을 SKILL·references·코드에 일치시킨다.

### N22. 검색 결과의 실패 건수는 fetch가 만들지 않는 다른 로그를 읽음 — 경미 / [신규]

- **공격·재현 절차:** 실패 시도만 있는 `audit/fetch-log.jsonl`을 만들고 source_index를 실행한다. 실패 섹션·건수가 출력되지 않는다. 정상 mdr-search 흐름에는 별도의 fetch-failures.jsonl 생산자가 없으므로 사용자는 미확보와 미시도를 구분하기 어렵다. raw fetch 로그 자체는 남으므로 경미로 분류했다.
- **근거:** fetch의 생산 파일은 `scripts/fetch.py:144`의 fetch-log.jsonl이고 source_index는 `scripts/source_index.py:129`에서 fetch-failures.jsonl만 센다. demo는 존재하지 않는 생산 경로를 fixture로 직접 써 준다(`scripts/source_index.py:209`). 요구 결과는 `codes/mdr-search/SKILL.md:33`의 실패 URL 요약이다.
- **최소 수정안:** 실제 fetch 로그의 최종 URL별 확보 상태에서 실패를 집계하고, 시도 실패 수와 URL 최종 실패 수를 구분한다.

### K07. fetch CLI가 JSON을 1,500자로 잘라 해시·경로까지 소실 — 경미 / [기지]

- **공격·재현:** 여러 tier의 error trace가 1,500자를 넘는 결과를 CLI와 동일한 출력식으로 직렬화했다. **JSON 파싱 실패, sha256 키 미출력**이었다. save가 raw와 meta를 남기므로 데이터가 전부 사라지는 것은 아니지만, 팀리드/워커가 stdout JSON의 local·sha256을 사용하는 계약이 깨진다.
- **근거:** `scripts/fetch.py:654`, `scripts/fetch.py:661`의 `json.dumps(... )[:1500]`. save가 sha256/local을 trace 뒤에 추가한다(`scripts/fetch.py:523`). 기지 맥락: `_planning/council-2026-08-22/review-codex-modularize.md:46` C3의 fetch IPC 지적.
- **최소 수정안:** stdout은 완전한 구조화 JSON으로 유지하고 긴 trace는 파일로 내보내거나 배열 항목 단위로 축약한다.

## 4. 기각·범위 제한 및 테스트 공백 해석

- 1차 C1의 **G3 기준 manifest 누락·렌더 전면 재빌드 세탁**은 현재 수정돼 있다. `verify_facts.py:938`의 build와 `render_pdf.py:119`의 extend, G5의 manifest 결박 검사를 확인했다. N01/N04는 그 수정 이후에도 남는 다른 경로다.
- 1차 C2의 **custom.pdf 봉인 후 변조 미검출**도 현재 수정됐다. 저장 entries의 경로를 직접 재해시하므로 A3를 pass로 평가했다. HWPX 봉인은 목적 스킬이 명시적으로 미지원한다. 이를 구현했다고 오인한 신규 결함으로 세지 않았다.
- 모든 프로세스가 동일 권한으로 원장을 수정할 수 있는 환경에서 해시만으로 적대적 writer를 인증할 수 없다. K05는 이 신뢰 모델을 지적한 것이며, N01/N04는 그 모델을 감안해도 정상 CLI와 정식 수동 영수증만으로 재현되는 결함이다.
- 기존 71개 fixture의 성공률은 여기서 찾은 29개 결함의 부재를 뜻하지 않는다. 특히 E2E는 한 번의 정상 렌더만 하며, G4에 단순 문자열을 기록하고 PDF 내부 F태그·링크·캡처 수를 검사하지 않는다(`tests/test_e2e.py:153`, `tests/test_e2e.py:158`, `tests/test_e2e.py:165`).
- G3가 정상적인 숫자/해시/경계 위반을 잡는다는 사실은 점수에 반영했다. 반면 워커의 실제 출력 오류 빈도, 외부 브라우저 MCP의 현재 allowedDomains 구현, 한글 COM 렌더 품질은 실측하지 않았으므로 보장하지 않는다.

## 5. 총평 (20줄 이내)

1. **46.875/100, 최종 출고 판정에 사용하기에는 재검토 필요**다. 점수는 고정된 32개 통제 항목의 충족도다.
2. 신규 22건·기지 7건, 치명 4건은 모두 정상 경로/로컬 재현으로 확인한 검증·보안 경계 문제다.
3. 가장 먼저 막을 것은 검증 원고와 렌더 입력 불일치, active HTML·원격 리소스, 이미지 SSRF, 조상 영수증 무효화 누락이다.
4. 1차 봉인 수정은 실제로 작동하지만, 무엇을 검증했는지와 최종 PDF가 무엇에서 생성됐는지를 증명하지 못한다.
5. 정상 수정 후 재렌더가 막히는 N06은 절차 준수를 어렵게 만든다. refs 재발급 P0와 함께 revision별 출력 수명주기를 고쳐야 한다.
6. F130·E130·F091의 예정 P0 패치만으로 부호·SI 단위·키·양방향 참조·다중 파일 commit·워커 결산 문제는 해결되지 않는다.
7. claim/capture/calculation 검토 기록은 전건 coverage와 입력 digest, 실제 최종 판정 호출에 연결해야 한다. 필드만 추가하면 N09와 같은 무검사 데이터가 늘어난다.
8. 확장 루프는 문서의 상한만 있고 실패 관측·ID·재개 상태가 없다. 누락을 충분한 조사로 해석하지 못하도록 join 계약을 먼저 만들어야 한다.
9. 테스트는 전체 재설치보다 실제 CLI 두 번째 실행, 다른 원고, 조상 실패, 실패 PNG 재사용, 사설 redirect 도달 여부의 회귀를 우선 추가해야 한다.
10. 코드·원본 연구 산출물은 수정하지 않았다. 리뷰와 저장소 밖 재현 증적만 작성했다.

REVIEW_DONE score=46.875