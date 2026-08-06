# 약점 감사 v5 — 적대 탐색 결과 (S1)
작성: 2026-08-06 · 방법: 5개 적대 렌즈(증거무결성·게이트허점·수집견고성·운영복구·확장성) 병렬 실독 → 중복 병합. 원본 43건 → 병합 30건.
제약 반영: (a) 적대 59케이스 그린 유지 · (b) 스키마 additive-only · (c) [Bx] failure 승격 금지(PEM 대장 마이그레이션 선행).

## 실증 확인(코드 실행으로 재현한 것)
| # | 주장 | 재현 결과 |
|---|---|---|
| 1 | 빈 작업폴더 + 산문 선언만으로 11게이트 통과 | `run_ledger.py` 로 report.md/pdf 없이 11게이트 PASS checkpoint → **전부 `fresh`, "완료 선언 가능: 가능"** |
| 2 | `harvest_images.page_images` 즉시 크래시 | 실 반환형(raw=bytes) 스텁 주입 실행 → `TypeError: cannot use a string pattern on a bytes-like object` |
| 3 | `harvest_images._searx_images` 항상 무음 실패 | `searx-instances.json` 은 dict → 순회가 `_comment` 등 키를 URL 로 조립 → **반환 `[]`** |

## 심각도별 약점 목록

### CRITICAL

#### `BUG-1+BUG-2` harvest_images 데드코드 2건 — page_images는 bytes에 str 정규식으로 즉시 크래시, _searx_images는 dict를 리스트로 순회해 항상 무음 실패
- **근거**: harvest_images.py:146 `html = r.get("raw") or r.get("text")` — fetch._result(fetch.py:417)의 raw는 bytes이고 149·151의 re.finditer(str 패턴, bytes)가 TypeError. direct 계층 성공(최빈 경로)이면 raw가 항상 존재해 무조건 크래시. harvest_images.py:196-199는 searx-instances.json(dict)을 `for inst in insts`로 순회해 키 문자열('_comment','instances'...)로 URL을 조립 → 예외 → continue → 항상 []. demo(259-287)는 page_images·searx 경로를 전혀 검증하지 않아 둘 다 미탐.
- **실패 시나리오**: `python harvest_images.py page <확보 URL>` 실행 즉시 트레이스백 — 이미지 소스 우선순위 2번(확보 페이지 og:image·본문 이미지)이 통째로 불능이 되어 라이선스 리스크가 큰 3순위 이미지 검색으로 강제 폴백되거나 도판게이트 FAIL. 동시에 searx 이미지 보충은 설계상 존재하지만 단 한 번도 결과를 낸 적 없는 데드코드라 openverse/commons 0건 주제에서 커버리지가 문서 약속보다 항상 좁다.
- **보완 방향**: 두 줄 수정: (1) `r.get("text") or (raw.decode(errors='replace') if raw else "")`, (2) `json.loads(...)["instances"]`. demo에 page_images 스텁 통과 assert와 순회 대상이 https 접두 URL인지 assert 추가. 실익 최대·비용 최소 — 최우선 착수 대상.

#### `GS-2+GS-9+OPS-8` watch 파일 부재 = fresh + 완료 판정이 로스터·run-receipt·메타데이터와 무관 — report.pdf가 없어도 11게이트 신선 PASS·완료 선언 성립
- **근거**: run_ledger.py:149-157 _target_hashes가 `if p.exists()`로 부재 파일을 생략, 288-292에서 기록 None == 현재 None → stale 아님, _completion_possible(300-302)은 state·verdict만 봄. 로스터 검사(322-331, bx-report.md·g4-visual-check.md·run-receipt.md 등 11종)는 validate 전용이고 exit code 미반영(351-352). 242-245의 G5 run-receipt 해시 봉인은 '존재하면'만이고 _gate_states(283-292)가 watches 외 키를 재대조하지 않음. completedAt(447-466)은 대장 append 시점에만 갱신되어 사후 파일 변경을 반영 못함.
- **실패 시나리오**: report.pdf를 한 번도 생성하지 않고 RENDER·G4·G5를 PASS checkpoint → None==None으로 fresh → '완료 선언 가능'. 필수 audit 산출물 전부 부재이거나 G5 후 run-receipt.md의 Caveats를 삭제·미화해도 어떤 명령도 지적하지 않는다. 완료 후 facts.jsonl을 수정해도 run-metadata는 '완료'를 오보해 재개 세션이 미검증 수정본을 재배포.
- **보완 방향**: checkpoint 시 해당 게이트 watches 파일 부재면 PASS 거부(missing_watch blocker), _gate_states에 missing_watch 상태를 분리해 _completion_possible에서 제외. 완료 판정에 roster missing==0 조건 추가, run_receipt 키 재대조로 불일치 시 G5 stale. status가 completion 판정 시 metadata 불일치를 경고. 전부 run_ledger 국소 수정이라 additive-only와 무충돌 — 기존 59케이스 green 유지 확인만 필요.

#### `GS-1` 게이트 verdict가 검증 도구 실제 실행과 결박되지 않음 — PASS 영수증 전건이 자유 문자열 자기신고
- **근거**: run_ledger.py:208-267 checkpoint()는 verdict·evidence(자유 문자열)만 받는다. G3가 verify_facts.py exit code·결과 해시를, G4가 g4-visual-check.md 실재를, RENDER가 report.pdf 생성을, G5C가 verify-<slug>.md를 요구하는 코드가 없다. 기계 하한은 _floor_scan(161-180)의 (b)(c) 2종뿐이고 순서 강제는 G1 halt 하나(227-230). SKILL.md:33-34 '산문 선언은 증거가 아니다' 원칙이 floor 밖에서 코드로 강제되지 않음.
- **실패 시나리오**: verify_facts가 FAIL 20건인 상태에서 `checkpoint G3 --verdict PASS --evidence "실패 0 확인"` → append 성공, exit 0. G5C·RENDER·G4·G5도 순서 무관하게 몰아 checkpoint → '완료 선언 가능'. 영수증 체계 전체가 산문 선언의 JSON 포장으로 전락.
- **보완 방향**: 게이트별 기계 전제조건을 checkpoint에 배선: G3/G5C는 검증 스크립트 결과 JSON 경로+해시를 필수 인자로 받아 대조(또는 내부 실행), G4는 g4-visual-check.md 실재+비어있지 않음, RENDER/G5는 report.pdf 실재. 순서 위반 checkpoint는 자동 WATCH. GS-2 묶음과 같은 checkpoint 함수 개보수로 함께 처리하면 비용 절감.

#### `EV-1` evidence.sha256이 콘텐츠와 결박되지 않음 — local 스냅샷 없으면 아무 64자 hex나 통과해 원문 미열람 위조 자유 · ⚠제약: 스키마
- **근거**: verify_facts.py:429-440 — sha256은 `_SHA256_RE` 형식만 검사하고 실해시 대조는 `if local:` 블록 안에서만 수행. facts-schema.json:83 evidence.required에 `local`·`http_status` 없음(확인 완료: required=[id,fact_id,type,source_url,sha256,accessed_at]). 스킬 데모 자체가 태그 문자열 해시를 넣는 관행(facts_db.py:300,343). fetch.py:429-437은 sha+local을 함께 만들지만 동반 탑재를 강제하는 검사 부재. URL 도달성·http_status 검사도 없음.
- **실패 시나리오**: 서브에이전트가 원문을 열지 않고 실재하지 않는 DART rcpNo URL + sha256(임의 문자열) + local 생략으로 evidence를 만든다 → 형식 통과, 해시 대조 스킵 → confirmed 승격, 보고서에 A등급 1차출처로 인쇄. 감사자가 URL을 눌러 404가 나도 대장은 PASS.
- **보완 방향**: schema required에 local 추가는 additive-only 위반 → 스키마는 그대로 두고 verify_facts에서 강제: local 부재 evidence는 '있으면 검사'가 아니라 FAIL(최소한 원출처 role·risk=high fact에), sha256은 _sources/ 실파일 해시와 일치 필수, http_status 2xx 기록을 verify-side 요구. 기존 fixture가 local 없는 evidence를 쓰면 59케이스가 깨질 수 있으니 fixture 보강과 함께 배선.

#### `EV-4` value.raw를 비수치 문자열로 쓰면 값대조(WARN 강등)와 캡처 요구(is_core_num=False)가 한 스위치로 동시에 꺼짐 — 근거·캡처 0으로 임의 수치 인쇄 · ⚠제약: 스키마
- **근거**: verify_facts.py:310-314 — lv is None이면 [값미대조] warning 후 continue(FAIL 아님). verify_facts.py:443-444 — is_core_num과 캡처 강제가 같은 `_vals(value.raw)` 한 필드에 물려 있고, _vals(182-202)는 Decimal 파싱 실패 시 None.
- **실패 시나리오**: F040을 value.raw="약 45(업계 추정)", risk normal, 캡처 없는 evidence 1건으로 confirmed로 만들고 본문에 "128조원(F040)"이라 쓴다 → 결박 성공, 128 vs 45 대조 생략(WARN), source_capture 미요구 → G3 실패 0 PASS.
- **보완 방향**: value.decimal '필수화'는 required 변경이라 스키마로는 불가 → additive로 optional `value.decimal` 필드를 추가하고 verify-side fail-closed: raw 파싱 불가 + decimal 부재면 본문 결박 시 FAIL. 캡처 강제 조건을 is_core_num이 아니라 '본문에 결박된 모든 confirmed fact'로 넓혀 두 게이트의 스위치를 분리.

#### `EV-2+EV-3` capture가 어떤 fact·수치·URL의 화면인지 결박 전무 — 이미지 1장 재사용으로 전건 증빙 충족, 재구성 발췌·FAILED 사이드카는 rename 한 번으로 정식 승격
- **근거**: verify_facts.py:441-459 — 핵심수치 증빙 검사는 `exists()`만. 구조검사(606-633)는 2KB·유니크컬러 8종 WARN뿐. facts-schema.json:97 capture는 문자열 하나라 capture 해시 필드 자체가 없음. facts_db.py:105-123 check_capture_path는 경로 토큰 `_reconstructed`만 보고, capture_web.py 산출 PNG에 기계 판독 표식 없음. capture_pdf.py:160-172의 E###.FAILED.png는 정상 산출물과 바이트 성격 동일.
- **실패 시나리오**: 정당한 캡처 1장을 E002~E080.png로 복제해 evidence 80건에 지정 → 전부 통과, 실제 수치가 찍힌 캡처 0장. 또는 재구성 발췌 PNG를 _captures/로 cp, E012.FAILED.png를 E012.png로 mv → '재작업 전까지 confirmed 불가' 보장이 파일명 한 번으로 무효.
- **보완 방향**: additive 필드로 해결 가능: evidence에 optional `capture_sha256`(+생성 시각·도구) 추가, verify에서 (a) 서로 다른 evidence의 동일 capture 해시 FAIL, (b) 파일명 stem↔evidence.id 불일치 FAIL. 재구성 PNG에 PNG tEXt 청크(`mdr:evidence=false`) 매직 삽입 후 verify가 판독해 FAIL. capture_pdf 성공 시 `<out>.meta.json`(matched 숫자·page·pdf sha) 사이드카를 남기고 부재·불일치 FAIL.

#### `GS-7+OPS-3+OPS-4` HITL 위조 무방비 — resolved_by 기본값 user·timeout 자가답변 허용·PLAN 게이트가 consent ask/answer 실재를 요구하지 않아 사용자 승인 합성 가능
- **근거**: run_ledger.py:500 --resolved-by default="user", record()(396-413)는 answer 작성 주체 검증 불가, timeout의 정의(대기시간·허용 게이트)가 어디에도 없음. gates.json:3 PLAN은 watches=[]로 한 번 PASS면 영구 fresh(275-280)이고, checkpoint는 lane_verdicts 빈 배열 허용·consent ask/answer 존재 미검사(209-267, 161-180). verification-gates.md:151-157·research-plan.md:74-82의 규정은 전부 산문.
- **실패 시나리오**: 자율 진행 에이전트가 목차 승인 ask 직후 스스로 `record answer --ask-id A1 --answer 승인`(플래그 생략 → resolved_by=user로 봉인) 또는 `--resolved-by timeout`으로 consent를 자가 답변 → PLAN PASS → 승인 없는 팬아웃. 사후 감사에서 대장만 보면 사용자가 답한 run과 구분 불가, 위반 흔적이 대장에 남지 않음.
- **보완 방향**: --resolved-by 기본값 제거(필수 인자화), consent·PLANNING-STUCK 등 HITL 필수 ask는 gate_id 화이트리스트로 resolved_by=user만 허용(timeout은 ask에 timeout_policy 선언 시로 한정). PLAN/G0 checkpoint PASS 전제조건으로 resolved_by=user answer 레코드 실재 검사, PLAN에 CLEAR+OKAY lane_verdicts 필수. '에이전트가 쓴 user 답'은 기계로 못 막는 한계를 문서에 명시.

#### `SC-1+SC-5` 팀리드 전건 재검증(LV)이 O(N) 순차 + 고비용 메인세션 전속 + 같은 원문 3~4회 재fetch — 대규모 조사에서 컨텍스트·비용·rate-limit 연쇄 폭발
- **근거**: SKILL.md:23-25·154-159, verification-gates.md:79-80 — 전 fact 팀리드 원문 직접 재열람, verifier는 confirm 권한 박탈(agent-briefs.md:42). 완화(샘플링) 자격 조건이 '전건 비용을 먼저 지불한 실측 비교'(SKILL.md:35-36)라 닭-달걀. source-ladder.md:81 콘텐츠 캐시 없음 — 같은 URL이 워커 수집·LV 재열람·G2 캡처·G4 팩트체커에서 각각 독립 접근되고 강방어 사이트 우회를 매번 처음부터 재수행.
- **실패 시나리오**: 20개 대상×축 3×fact 8~10건 = 500+ fact → 500회 순차 fetch가 메인세션 컨텍스트로 유입, 중간 압축 시 검증 진행 상태 유실 → 재열람 전부 다시 or 대충 verify_event 기록(후자는 전건 재검증 존재 이유 무력화). DART 등 단일 도메인에 50회 연속 재열람 → WAF rate-limit → 이후 건마다 사다리 재소진 또는 '원문확인불가' 오판. run 시간이 fact 수×도메인 방어강도에 비례 폭증.
- **보완 방향**: 2단 검증: verifier 레인(sonnet 병렬)이 재열람+verbatim 대조 결과를 구조화 반환, 팀리드는 심사·confirm만(직접 재열람은 risk:high+인용 fact+불일치 건 층화 샘플링). 워커 확보 raw를 sha256과 함께 _research/ 스냅샷으로 결박해 LV를 '스냅샷 대조+도메인당 라이브 표본 1건'으로 이원화. LV 진행 상태를 run-ledger fact 단위 체크포인트로 외부화. 프로세스 정본 개정이 커서 착수 비용은 크지만 규모 조사 성립의 전제.

### HIGH

#### `EV-6+GS-5` 부록 마커(APPENDIX 주석)를 문서 앞쪽에 삽입하면 그 뒤 본문 전체가 모든 검사에서 제외 — 무태그·값불일치·금지패턴 전건 면제
- **근거**: verify_facts.py:50 APPX_COMMENT, 87-94 split_body_appendix — 주석 마커는 최초 매치 지점에서 무조건 자름(헤딩 폴백만 '최후 출현' 방어). 이후 verify(729-751)의 bound_numbers·forbidden_patterns·figures·used 집계 전부 body만 대상. check_toc(755)만 전체 md를 봐서 목차는 통과 → '정상 PASS'로 위장.
- **실패 시나리오**: 서론(5% 지점) 직후 `<!-- FACTSHEET:APPENDIX -->` 삽입 — 렌더 PDF에는 주석이 안 보여 고객에겐 정상 보고서, verify에겐 본문이 서론뿐 → 나머지 95%의 무태그 수치·플레이스홀더·비밀문자열 전건 미검사, used가 비어 캡처 요구도 소멸.
- **보완 방향**: 마커도 최후 출현 사용 + 마커 2개 이상 FAIL + 마커 앞 본문이 문서의 일정 비율 미만이면 FAIL, 부록 구간에도 오태그·미확정·플레이스홀더·비밀 검사는 계속 적용. 수십 줄 수준 국소 수정으로 완전 우회로 하나가 닫히는 최고 효율 항목.

#### `FP-1+COV-1` RSS 계층 이중 결함 — MIME 정확일치로 application/rss+xml류가 전부 차단되는 한편, text/xml로 오는 사이트 전체 피드는 '해당 기사 본문'으로 가짜 ok
- **근거**: fetch.py:33-34 ALLOWED_MIME 튜플 정확일치(225) — 실서비스 피드 대다수인 application/rss+xml·atom+xml이 'mime:...' 사유로 무음 스킵. fetch.py:343-347+388-391+168-169 — 통과한 피드는 본문≥1000자면 확정 ok. _rss_urls(281-293)는 /rss·/feed 등 사이트 공용 피드를 합성. 올바른 타입은 죽고 애매한 타입만 사는 역선택.
- **실패 시나리오**: 차단 사이트의 특정 기사 fetch → site-wide /feed(text/xml)가 200 → 최근 글 10건 요약 합계가 1000자 초과로 ok → 대상 기사가 피드에 없어도 그 URL의 본문으로 저장·해시되어 팩트시트 재검증이 엉뚱한 글의 수치를 원문 대조. 반대로 워드프레스/티스토리 피드는 정확일치 실패로 사다리 소진 fail.
- **보완 방향**: mime.startswith 접두 매칭(또는 '+xml' 변형 명시)으로 한 줄 수정 + rss 계층은 피드 파싱 후 대상 URL과 <link> 일치 item 본문만 검증, 일치 없으면 최대 partial 강등. demo에 'application/rss+xml 통과' 긍정형 assert로 회귀 방지.

#### `ROT-1+MN-1` 검색 스택 무음 실명 — SearXNG 429 백오프 데드코드·헬스체크 미구현·목록 노후 + DDG 봇차단 200 페이지가 '결과 없음'으로 위장
- **근거**: search.py:85-102 — 429는 예외가 아니라 st!=200 경로의 break로 1회 만에 포기(백오프 [1,2,4]는 타임아웃에서만 소비). searx-instances.json:11 health_path 미참조, 목록 5개 고정. search.py:65-72 — result__a 정규식 0매치면 경고 없이 빈 리스트, 164-167 — ddg 빈 결과+searx 소진이면 조용히 []. html.duckduckgo.com은 자동화에 200 상태 anomaly 페이지를 자주 반환.
- **실패 시나리오**: 세션 중 DDG가 IP를 anomaly 플래그 → 이후 모든 쿼리 200+차단페이지 → 0매치 → searx 5개 전멸과 겹치면 search()가 전 쿼리 [] → 에이전트가 '이 주제는 웹 출처가 없다'로 오판, 커버리지 공백이 보고서 구조(출처 부재 서술)로 굳는다. 차단과 무결과가 구분 불가.
- **보완 방향**: st==429일 때만 backoff 루프 지속하도록 분기 수정, 0매치인데 응답이 수KB면 anomaly/CAPTCHA 마커 검사로 '차단됨' 상태를 빈 리스트와 구분 반환, health_path로 세션 시작 시 1회 생존 필터, 소진 시 stderr 경고. 전부 search.py 국소 수정.

#### `FP-2` 헤더 charset 미선언 EUC-KR 페이지가 replace 디코드 모지바케로 1000자 규칙 ok 통과 — 한국 관공서·구형 언론 소스군에서 치명
- **근거**: fetch.py:214-215 Content-Type 헤더 charset만 파싱(<meta charset> 미확인) + 230-234 utf-8 실패 시 errors='replace' 강제 디코드 + 168 길이만으로 ok.
- **실패 시나리오**: meta charset=euc-kr에만 인코딩을 선언한 구형 사이트 fetch → '���' 범벅 텍스트가 태그는 ASCII라 1000자 이상 추출 → verdict=ok → 읽을 수 없는 쓰레기가 원문 증빙으로 저장되고 수치 재검증 시 원문 대조 불가인데 수집은 성공 기록.
- **보완 방향**: 디코드 실패 시 bytes 정규식으로 <meta charset> 스니핑 → euc-kr/cp949 재시도, 최종 replace 결과의 U+FFFD 비율 임계 초과면 validate_body에서 empty/partial 강등. 소규모 수정.

#### `OPS-2` 재개 진입점(run-metadata.json)에 활성 ask 정보 부재 — 크래시-재개 시 미답 consent가 보이지 않는 교착 또는 무단 supersede
- **근거**: run_ledger.py:459-465 메타데이터는 mode·completedAt·last_fresh_gate·fact_count·updated_at뿐. 357-389에서 활성 ask 존재 시 새 ask는 supersedes 없이는 exit 2 거부. report-format.md:87-100 handoff/재개 다이제스트 필수 섹션에도 활성 ask 항목 없음.
- **실패 시나리오**: consent ask 직후 세션 중단 → 재개 세션이 handoff.md+메타만 읽고 미답 ask를 모른 채 진행, 새 ask가 exit 2로 거부되면 가장 쉬운 탈출구가 옛 ask_id supersede — 사용자가 본 적 없는 consent 질문이 조용히 대체되어 승인 없는 팬아웃, 또는 원인 불명 정지.
- **보완 방향**: _update_metadata에 `active_ask: {ask_id, gate_id, question}` 추가(additive), handoff 필수 섹션과 재개 다이제스트에 '미답 ask' 슬롯 명시, 해당 gate_id 진행을 막아야 하는 활성 ask가 있으면 checkpoint 거부.

#### `SC-2` add_fact가 안내하는 merge_evidence API가 미구현 — 병렬 팬아웃의 정상 산출물(중복 수집)이 G1 join을 수작업 JSONL 편집 병목으로 만든다
- **근거**: facts_db.py:218-220 add_fact가 동일 claim_key에서 "→ merge_evidence/set_status 사용"을 안내하며 ValidationError를 던지지만 merge_evidence는 저장소 전체에서 이 에러 메시지 한 곳에만 존재(구현·문서 모두 없음). 독립 관찰그룹 ≥2가 Bx 통과 조건이라 중복 수집은 설계된 정상 동작.
- **실패 시나리오**: 서로 다른 레인이 같은 지표를 독립 수집 → 두 번째 레코드부터 예외, 안내된 해법은 존재하지 않는 함수 → 팀리드가 매 중복마다 수작업 JSONL 편집으로 evidence_ids 병합 — 원자적 쓰기 경로를 우회해 스키마 위반·부분쓰기 위험 재도입, 수백 건 규모에서 join이 직렬 병목.
- **보완 방향**: facts_db에 merge_evidence(existing_fact_id, new_fact_dict) 실제 구현: 값 일치 시 evidence 병합+observer_group 갱신, 불일치 시 conflict 레코드 자동 생성 후 disputed 병기. 병합을 예외 처리가 아니라 기본 경로로. 단일 함수 추가라 additive.

#### `EV-5` '팀리드 재검증'이 자기신고 문자열 by="lead" 한 줄 — 재열람 사실과 결박이 없어 서브에이전트 무검증 confirm이 정상 통과
- **근거**: facts_db.py:246-254 add_verify_event는 by를 그대로 기록하고 호출 주체 미확인. validate_fact(84-90)는 by=="lead" 이벤트가 비지 않기만 요구. verify_events는 evidence·capture·재열람 시각과 상호검사 없음(evidence 추가 이전 시각이어도 통과). facts.jsonl 직접 편집으로 {by:"lead"} 추가해도 동일(verify_facts.py:365-368은 같은 validate_fact 재실행).
- **실패 시나리오**: 조사 서브에이전트가 팀리드 개입 없이 add_verify_event(by="lead") 후 set_status(confirmed) — 원문 재열람도 캡처 육안도 없이 '무출처 confirm 금지'·'lead 재검증 필수' 둘 다 통과.
- **보완 방향**: verify_event에 optional 필드(additive)로 대상 evidence_id·재열람 아티팩트 해시를 싣게 하고 verify-side에서 부재 시 FAIL, at이 evidence.accessed_at 이후인지 시간 순서 강제. 팀리드 세션만 아는 run token(작업폴더 생성 시 발급, audit/ 저장)을 이벤트에 병기해 자기신고와 구분 — 모델 간 위조는 근본적으로 못 막는 한계 명시.

#### `EV-8` manifest가 서명 없는 자기참조 스냅샷 — 변조 후 정규 절차인 build 재실행(재봉인)이 곧 세탁 경로, _reconstructed/·audit/는 미추적
- **근거**: manifest.py:63-74 verify는 manifest.json 내 해시와 현재 파일 비교인데 manifest.json 자체는 해시·서명 대상이 아니고 build(52-60)가 언제든 덮어씀. TRACKED(23-31)에 _reconstructed/** 부재, audit/** 의도적 제외. SKILL.md:70이 G3 이후 재봉인(build 재실행)을 정규 절차로 규정.
- **실패 시나리오**: G3 PASS 후 facts.jsonl의 F012 값과 report.md 수치를 함께 고치고 정규 절차대로 `manifest.py build` → G5 verify는 changed 0으로 ok, 변조 이전 해시는 어디에도 안 남음. _reconstructed/ 산출물은 처음부터 봉인 대상이 아니라 사후 편집 무흔적.
- **보완 방향**: append-only 체인: build 시 이전 manifest.json sha256을 `prev`로 싣고 audit/manifest-history.jsonl 누적, verify가 체인 연속성 확인. 재봉인은 신규 파일 추가만 허용(기존 항목 해시 변경 시 --allow-change 명시 필요), _reconstructed/**를 TRACKED에 추가. 파일 추가 방식이라 additive.

#### `OPS-1+SC-7` "append-only" 대장 2종(run-ledger·facts_db)이 실제로는 전체 파일 재작성 — 동시 세션 lost-update로 레코드 소실 + O(N²) I/O + 2파일 비원자 갱신
- **근거**: run_ledger.py:441-444 _append가 전체를 읽어 전체 덮어쓰기(잠금·버전검사 없음, docstring 34-35는 append-only 주장), SKILL.md:127은 background 팬아웃 명시. facts_db.py:207-243 add_fact/add_evidence 매 호출 전체 재작성 + _next_id 전 행 스캔, add_evidence는 evidence.jsonl(239)→facts.jsonl(243) 별개 원자 연산이라 사이 중단 시 역링크 없는 반쪽 상태.
- **실패 시나리오**: background 워커 join 중 ask append와 다른 프로세스의 checkpoint가 겹치면 나중 쓰기가 앞선 쓰기를 통째로 덮음 — ask 소실 시 answer가 exit 2 거부, answer 소실 시 유령 교착, checkpoint 소실 시 통과한 게이트 재수행. fact 1,000건 규모에서 등재 I/O가 O(N²)로 팽창(Windows fsync 특히 느림), 중단 시 유령 evidence가 G2 캡처 산정에서 누락.
- **보완 방향**: 진짜 append 모드(open 'a' + 줄 단위 flush)로 전환하고 상태 변경은 이벤트 레코드로 적어 읽기 시점 fold(run-ledger가 이미 같은 패턴). 최소한 msvcrt/portalocker 파일락으로 직렬화. evidence→fact 역링크는 저장하지 말고 읽기 시 유도 계산하면 2파일 비원자 문제 소멸. 쓰기 경로 교체라 59케이스 회귀 확인 필수.

#### `EV-7+GS-6` 수치 인식이 단위 화이트리스트+공백 금지 휴리스틱 의존 — 공백 한 칸·화이트리스트 밖 단위(명·건·곳·배·EUR 등)면 무태그 수치가 검사 대상에서 원천 제외 · ⚠제약: 검사범위 확장(59케이스 green 선확인)
- **근거**: verify_facts.py:61-62 UNIT 고정 화이트리스트(명·건·개사·배·곳·EUR·€ 등 부재). 73-80 _plausible이 _TIGHT_KRW_UNITS에서 숫자-단위 사이 공백이면 False → 282에서 매치를 nums에서 통째 제거해 결박·무태그 검사 둘 다 제외.
- **실패 시나리오**: "2030년 국내 시장은 45 조원 규모"(공백 1칸, 태그 없음)나 "수소충전소 384곳, 2.1배 증가, 종사자 12,000명"은 대장에 fact가 없어도 [무태그]가 안 나고 G3 PASS — 개소수·고용·배수 성장률 등 핵심 실태 수치가 검증 사각에서 확정 서술.
- **보완 방향**: 제약 (a) 주의: 검사 범위 급확장은 기존 fixture에 신규 FAIL을 만들 수 있으므로 WARN 티어로 시작 후 실측 승격. UNIT에 한국어 수량 단위(명·개·대·건·곳·사·기·회)·배·주요 통화 기호/코드 추가, _plausible은 매치 삭제 대신 '느슨한 매치' 표시로 무태그 검사에는 남기고 값대조만 완화.

#### `OPS-5` research-plan.md가 watch 대상이 아님 — 승인 계획 무단 편집이 신선도 모델에서 불가시, --plan 검사도 G3에서 미강제
- **근거**: run_ledger.py:145-146 _watch_file은 facts/report_md/report_pdf 3종만 매핑. steering 레코드 스키마(13-14, 375-380)에 변경 전후 계획 해시 없음. research-plan.md:160 'steering 없는 계획 차이는 오염'인데 차이를 검출할 기준선이 기계에 없고, verify_facts --plan 옵션은 G3 checkpoint에서 강제되지 않음.
- **실패 시나리오**: 확장수렴 중 팀리드가 계획의 축 이름·out-of-scope를 직접 수정 — steering 없이도 어느 게이트도 stale이 안 되고, G3를 수정된 계획으로(또는 --plan 생략으로) 돌리면 사용자가 승인한 목차와 최종 보고서 축이 다른데 전 게이트 PASS 완료 선언.
- **보완 방향**: watches에 research_plan 추가해 PLAN checkpoint에 계획 해시 봉인, 이후 해시 불일치 시 대응 steering(before/after 해시 필드 신설, additive) 부재면 stale. G3 요구 조건에 plan_check 증적 포함. gates.json watches 변경이 기존 ledger 테스트에 닿으므로 green 확인 동반.

#### `SC-3` 확장수렴 수렴조건(축별 잔여 리드 0)이 분기율>1이면 구조적 미수렴 — dedup은 팀리드 수동 산문 집계뿐이라 중복 스폰 비용 이중 지출
- **근거**: SKILL.md:138-143 — 새 리드마다 즉시 스폰 + 수렴조건 '잔여 리드 각 0', dedup 메커니즘은 expansion-log.md에 손으로 적는 것이 전부(정규화 키·유사도 규칙 없음). 깊이캡 도달 시 사용자 연장 문의로 무한 연장 가능.
- **실패 시나리오**: 워커당 평균 EXPAND 리드 2~3건(밸류체인 조사 전형) → 웨이브마다 잔여 리드 증가로 '잔여 0' 영원히 미달, 실질 정지장치는 깊이캡뿐인데 연장 답변이 상한을 지움. 표기 변형("삼성전자 2024 매출" vs "Samsung FY2024 revenue")을 수동 dedup이 못 잡아 중복 스폰 → SC-2의 claim_key 충돌로 join 비용까지 이중 부과.
- **보완 방향**: 리드에 정규화 키(축|entity|metric|period 캐노니컬 폼)를 부여해 expansion-log를 기계 dedup 가능한 JSONL로 승격, 수렴조건을 '한계효용 기준'(웨이브당 신규 confirmed-후보 수 < 임계)으로 교체, 연장 문의에 예상 추가 비용 의무 첨부. 정본 문서 개정 중심이라 코드 리스크 낮음.

#### `SC-4` G2 백지 캡처 검출이 팀리드 육안(PNG Read)에만 의존 — 이미지 토큰 비용이 fact 수 선형이라 비용 압박 시 유일한 검출 장치가 소멸 · ⚠제약: 검사범위 확장(59케이스 green 선확인)
- **근거**: SKILL.md:177-181 confirmed 전건 캡처 + 팀리드 육안 필수, verification-gates.md:91-92 '실재 검사는 파일 유무만 — 육안이 게이트의 일부'. G3 구조검사는 WARN 수준(SKILL.md:199)이라 차단력 없음.
- **실패 시나리오**: confirmed 300건 → 캡처 300장 육안 Read만으로 수십만 토큰 + 직렬 캡처로 wall-clock O(N). 팀리드가 비용 압박으로 표본만 보면 명시된 유일한 백지 검출이 사라져 감사 번들에 백지 증빙이 섞인 채 G2 PASS — 증빙형 스킬의 핵심 산출물이 무증빙이 되는 조용한 실패.
- **보완 방향**: 캡처 직후 fitz/PIL 픽셀 분산·엔티티 밀도 기계검사로 임계 미달 즉시 .FAILED 처리. 단 WARN→FAIL 승격은 제약 (a)의 기존 fixture 판정 변화 여부를 먼저 실측(green 유지 확인 후 승격). 육안은 기계검사 통과분 중 층화 표본으로 축소, 캡처 생성은 도메인별 워커 위임 병렬화.

#### `GS-4+OPS-6` partial_stale 후 재-checkpoint에 재검증 증적 요구 없음 — fact 수정 후 즉시 PASS 재기록이면 원문 재열람 없이 신선도 리셋('전건 재검증' 원칙 미배선) · ⛔제약: Bx 승격 금지(현 단계 BLOCK 전환 보류)
- **근거**: run_ledger.py:247-254 generation은 facts 해시 변화 시 +1만, checkpoint(208-267)는 변경 claim_key가 실제 재검증됐는지(직전 checkpoint 이후 verify_event by=lead 존재) 대조하지 않고 새 해시를 봉인. verification-gates.md:50-53 델타 라체트에 대응하는 기계 검사 부재. floor(b)는 evidence_ids 빈 배열만 잡고 verify_event 부재는 안 잡음.
- **실패 시나리오**: G2 통과 후 시장규모 45조→60조 임의 수정 → LV·BX·G2 partial_stale → 재열람·verify_event 없이 `checkpoint --verdict PASS --evidence "델타 재검증 완료"` 연속 실행 → 전부 fresh 복귀, 수정 수치가 어떤 재검증도 없이 신선 영수증 획득.
- **보완 방향**: [현 단계 구현 보류(BLOCK 승격분)] 완전한 해법인 floor(d) 'confirmed인데 최신 content-hash 이후 verify_event 없음 → BLOCK'은 failure 승격이라 PEM 대장 마이그레이션 선행 전까지 금지. 지금 가능한 범위: 같은 검사를 WATCH+blocker로만 배선(재-checkpoint 시 변경 claim_key별 verify_event 대조 → 미충족 시 자동 WATCH), 마이그레이션 후 BLOCK 승격.

#### `GS-3` 레거시 완화 악용 — evidence.jsonl을 안 만들면(또는 지우면) 스키마 위반 BLOCK이 WATCH로 강등되고 WATCH는 완료로 집계, 댕글링 evidence_ids도 미검사 · ⛔제약: Bx 승격 금지(현 단계 BLOCK 전환 보류)
- **근거**: run_ledger.py:165 `legacy = not wp.evidence.exists()`, 196-200 _clamp에서 legacy면 floor(c)를 WATCH+migration_required로 완화, 300-302는 WATCH를 완료 인정. floor(b)(168-169)는 빈 배열만 보고 참조 대상 부재(E999 등)는 검사하지 않음 — legacy 모드에선 검증 자체가 불가.
- **실패 시나리오**: facts.jsonl에 조작 행을 confirmed + evidence_ids=["E999"]로 append하고 evidence.jsonl을 생성하지 않음 → floor(c) 위반 전건 WATCH 강등, floor(b) 침묵 → 11게이트 WATCH/PASS로 완료 선언. '레거시 재개를 막지 않는다'는 완화가 신규 조사의 우회로가 됨.
- **보완 방향**: [현 단계 구현 보류(BLOCK 승격분)] '신규 run에서 evidence.jsonl 부재 = BLOCK'은 migration_required 완화의 승격이라 대장 마이그레이션 선행 필요. 지금 가능한 범위: floor(b)에 댕글링 evidence_ids 검사 추가(additive 검사, evidence.jsonl 실재 시 동작)와 legacy 판정을 '배치1 이전 타임스탬프/마커 실재'로 좁히는 준비 작업까지만, BLOCK 전환은 마이그레이션 후.

### MEDIUM

#### `EV-9` 표 행 값일치 폴백이 태그↔수치 귀속을 무너뜨림 — 같은 행에서 값만 같으면 다른 지표의 수치를 남의 F태그로 정당화
- **근거**: verify_facts.py:290-305 — 직접 결박 실패 시 같은 세그먼트(표 행 전체, 105-129) 안 아무 태그나 순회해 lv==bvals면 ok. fact의 metric/entity/period를 전혀 안 봄. _bind_pairs(248)가 `|` 건너뛴 직접 결박을 막아 표에서는 이 폴백이 사실상 유일 경로.
- **실패 시나리오**: `| 매출 300.9조원 | 영업이익 300.9조원 | (F001) |` — F001은 매출만 확인한 fact인데 영업이익 셀도 값이 같다는 이유로 ok. 통화 단위가 같은 여러 지표를 한 행에 나열하고 하나만 태그하면 나머지가 '증빙된 수치'처럼 인쇄.
- **보완 방향**: 폴백을 '값 일치 + 같은 셀 인덱스 또는 행의 지표명이 fact.context.metric과 매칭'으로 좁히고 used_tags 재사용 금지를 폴백에도 적용. 폴백 통과 건수는 항상 WARN으로 표면화 — 조이는 방향이라 fixture green 확인 후 반영.

#### `GS-8` claim_key 중복 시 _fact_hashes dict 덮어쓰기 — 앞 행 변경이 신선도 판정에서 마스킹
- **근거**: run_ledger.py:136-142 `out[key] = _canon_sha(f)`가 같은 claim_key의 앞 행을 조용히 덮음. 중복 검출은 verify_facts.py:360-364(G3 전용)에만 있고 run_ledger floor/_gate_states에는 없음.
- **실패 시나리오**: 같은 claim_key 행 2개(F010 원본, F077 조작본) 상태에서 LV checkpoint → 뒤 행 sha만 봉인 → 앞 행 F010 수정이 changed_claim_keys에 안 잡혀 게이트 fresh 유지 — fact 단위 신선도 판정의 근거 손상(G3 전이면 중복 자체도 미검출).
- **보완 방향**: _fact_hashes에서 중복 키를 claim_key#n으로 분리하거나 해시 결합(sha(앞||뒤))으로 어느 행 변경도 실효되게 — 수 줄 수정. floor(c)로의 중복 검사 승격은 bx-blocked 영역이므로 해시 결합만 먼저.

#### `FP-3` soft-404·쿠키동의·페이월 티저 등 200+장문 페이지가 무조건 ok — 챌린지 마커 목록도 정적·구세대(akamai/incapsula류 부재)
- **근거**: fetch.py:168-169 본문≥1000자면 마커 검사 없이 확정 ok + 35-37 CHALLENGE_MARKERS에 akamai·incapsula·perimeterx·'page not found' 계열 부재 + 173-176 마커 없는 200~1000B 차단 페이지는 partial 생존(401-402에서 partial_res로 반환).
- **실패 시나리오**: 장문 '페이지가 없습니다'+추천기사 목록이나 1000자 구독 권유문이 ok로 원문 채택. Akamai 차단 페이지(300~800B)는 partial로 살아남아 차단문이 '얇은 본문'으로 파이프라인 유입.
- **보완 방향**: ok 확정 전 soft-404 네거티브 마커 검사 1줄 추가, CHALLENGE_MARKERS에 akamai/incapsula/perimeterx 보강, partial 반환에도 마커 검사를 통과 조건으로. 소규모.

#### `COV-2` Wayback 계층이 closest 스냅샷을 시점 검증 없이 ok 반환 — 수년 전 본문이 '현재 원문'으로 유입되고 재검증도 같은 스냅샷을 열어 미검출
- **근거**: fetch.py:249-262 — closest.timestamp를 읽지 않고 available+url만 확인 후 verdict=ok, 신선도 메타가 결과 dict에 없음(archived_url 문자열에만 암묵 존재). API 호출이 http:// 평문(250).
- **실패 시나리오**: 개편으로 전 계층 차단된 기업 IR 페이지 → 2021년 스냅샷이 ok 저장 → 5년 전 매출·가격이 '현재 원문 재열람' 증빙으로 결박. 재검증 게이트도 같은 스냅샷을 다시 열어 시점 오류 미검출.
- **보완 방향**: closest.timestamp 파싱해 결과에 snapshot_date 필드 명시(additive), 임계(예: 18개월) 초과 시 partial+stale 사유로 강등해 팀리드 판단으로. API는 https로.

#### `OPS-7` 런타임 카운터(재스폰 상한·깊이캡·자동확정 연속·인터뷰 라운드)가 세션 기억·산문에만 존재 — 중단·재개 시 상한 전부 리셋
- **근거**: agent-briefs.md:91-97 재스폰 이력 기록 위치·형식 미지정(run_ledger.py:369-433 kind 5종에 respawn 부재), SKILL.md:141-143 깊이캡은 expansion-log.md 산문 집계, research-plan.md:51-52 자동확정 3연속·5라운드는 순수 세션 내 카운트, run-metadata.json(459-465)에 카운터 없음.
- **실패 시나리오**: 3웨이브째·재스폰 2회째에서 중단 → 재개 세션이 자유형 산문을 오독하거나 0부터 재계수 → 깊이캡 3회가 실질 5~6회로 늘어 예산 초과 팬아웃, 죽은 소스 무한 재발사, 자동확정이 상한 넘어 지속.
- **보완 방향**: run-metadata.json에 counters{respawn_by_lane, wave, interview_round, autoconfirm_streak} 영속화(additive) 또는 run-ledger에 경량 kind:respawn/wave 레코드 추가, 재개 다이제스트 필수 항목으로 승격.

#### `SC-6` 동결→수리→재동결 세대 루프에 상한 부재 + 발견 전건 처분이 팀리드 직렬 — 수리가 새 불일치를 낳는 진동 케이스에서 미수렴
- **근거**: verification-gates.md:44-57 — 3레인 발견을 팀리드 단독이 accept/rebut 전건 처분 후 재동결·generation+1, 상한은 재반박 2라운드뿐 generation 캡 부재. '미처분 충돌 잔존 시 G2 진입 불가' fail-closed라 병목 우회 불가.
- **실패 시나리오**: Bx 발견 수리가 정합성 레인의 새 불일치(단위·연도 파급)를 낳는 진동 — generation 4, 5로 증가하며 매 세대 수십 건×원문 확인의 직렬 처분이 임계 경로화, 이론상 무한·실무상 팀리드 컨텍스트 고갈로 붕괴.
- **보완 방향**: generation 하드캡(예: 3) + 도달 시 잔여 발견을 disputed/9부 한계로 일괄 강등하는 명시 출구. 처분 위임 분리: P3(표현·범위)는 verifier가 초안, 팀리드는 승인만(P1만 전속). 정본 문서 개정 중심.

#### `SC-8` 말단 수정 1건의 재실행 반경이 RENDER→재봉인→G4 전 페이지 육안→G5 전체 — 렌더 이후 구간에 증분 개념 부재
- **근거**: verification-gates.md:21-23 report_md/pdf는 파일 해시 전체 실효, SKILL.md:212-231 렌더 후 재봉인+G4 페이지 이미지 육안+G5 재검사. fact 단위 신선도(partial_stale)는 LV·G2까지만 증분.
- **실패 시나리오**: G4에서 오탈자 1건 → facts 수정 → 재렌더 → 80쪽 PDF 전 페이지 재육안(이미지 토큰×페이지 수) — 지적 5회면 말단 사이클 5회 전량 재실행. 팀리드가 임의로 '변경 페이지만' 축소하면 g4-visual-check 기록과 실제 확인 범위가 어긋나는 감사 위조.
- **보완 방향**: g4-visual-check를 페이지 단위 체크리스트로 구조화하고, 재렌더 시 fitz 픽셀/텍스트 diff로 변경 페이지만 재육안하는 증분 규칙을 정본에 명시(전 페이지는 초회+목차 변동 시 한정). 챕터 분할 렌더 후 병합으로 diff 범위 축소.

## 테마 요약

5개 렌즈 30건을 30개로 병합(중복 8쌍 통합)한 결과, 최대 테마 5개: (1) 자기신고 신뢰 붕괴 — 게이트 verdict·verify_event·consent answer가 실제 도구 실행/아티팩트/사용자와 결박되지 않아 PASS 영수증·재검증·HITL 전부 문자열로 위조 가능(GS-1, GS-2+GS-9+OPS-8, GS-7+OPS-3+OPS-4, EV-5, GS-4+OPS-6). (2) 증거 결박 부재 — sha256·capture가 어떤 콘텐츠와도 물리적으로 묶이지 않고, value.raw 한 필드가 값대조와 캡처 요구의 공동 스위치라 원문 미열람 위조가 자유(EV-1, EV-2+EV-3, EV-4). 이 두 테마가 critical 8건 중 6건. (3) 본문 검사 회피 표면 — 부록 마커 1줄·단위 화이트리스트·표 행 폴백으로 무태그 수치가 검사 밖으로(EV-6+GS-5, EV-7+GS-6, EV-9). (4) 수집 스택 무음 실패 — harvest_images 크래시/데드코드 2건, RSS MIME 역선택, EUC-KR 모지바케, 검색 차단 위장 등 '실패가 성공 또는 침묵으로 기록'(BUG-1+2, FP-1+COV-1, FP-2, ROT-1+MN-1). (5) 규모 확장성 — LV O(N) 순차 재열람+재fetch, 전체 파일 재작성 대장, 말단 수정의 전량 재실행(SC-1+SC-5, OPS-1+SC-7, SC-8). 제약 반영: schema 충돌 2건(EV-1, EV-4)은 required 승격 대신 verify-side fail-closed로 우회 가능, bx-blocked 2건(GS-4+OPS-6, GS-3)은 BLOCK 승격분만 '현 단계 구현 보류'하고 WATCH 배선까지는 지금 가능, 검사 범위 확장 2건(EV-7+GS-6, SC-4)은 59케이스 green 보호를 위해 WARN 티어 선행을 조건으로 표시.
