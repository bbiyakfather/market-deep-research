# v5 우선순위 점수화 · 채택 결정 (S3)

작성: 2026-08-06 · 방법: 독립 3심사관(무결성/실용/아키텍처) 병렬 채점 → 상위 12건 적대 리뷰 → 최종 결정.
점수 = impact x feasibility x fit (각 1~5, 3심사 평균의 곱).

## 채점 랭킹 (전 30건)

| 순위 | 약점 | impact | feas | fit | 총점 | 심사편차 |
|---|---|---|---|---|---|---|
| 1 | `EV-6+GS-5` | 4.67 | 5 | 4.67 | **108.9** | 1 |
| 2 | `GS-2+GS-9+OPS-8` | 5 | 3.67 | 5 | **91.7** | 0 |
| 3 | `FP-1+COV-1` | 4 | 4.67 | 4.67 | **87.1** | 2 |
| 4 | `BUG-1+BUG-2` | 3.67 | 5 | 4.67 | **85.6** | 2 |
| 5 | `COV-2` | 3.67 | 4.67 | 5 | **85.6** | 1 |
| 6 | `ROT-1+MN-1` | 4 | 4.33 | 4.67 | **80.9** | 2 |
| 7 | `GS-7+OPS-3+OPS-4` | 5 | 3.67 | 4.33 | **79.4** | 0 |
| 8 | `OPS-2` | 3 | 5 | 5 | **75** | 0 |
| 9 | `FP-2` | 3.67 | 4.33 | 4.67 | **74.1** | 1 |
| 10 | `SC-2` | 3.67 | 4 | 5 | **73.3** | 1 |
| 11 | `EV-8` | 3.67 | 4 | 4.67 | **68.4** | 1 |
| 12 | `GS-8` | 2.67 | 5 | 5 | **66.7** | 1 |
| 13 | `OPS-7` | 2.67 | 5 | 5 | **66.7** | 1 |
| 14 | `GS-1` | 5 | 3 | 4.33 | **65** | 0 |
| 15 | `FP-3` | 3.67 | 4 | 4.33 | **63.6** | 1 |
| 16 | `SC-4` | 4 | 3.33 | 4.33 | **57.8** | 0 |
| 17 | `EV-5` | 4.33 | 3 | 4.33 | **56.3** | 1 |
| 18 | `EV-4` | 4 | 3 | 4 | **48** | 0 |
| 19 | `SC-6` | 3 | 4 | 4 | **48** | 0 |
| 20 | `EV-1` | 4.67 | 2.33 | 4.33 | **47.2** | 1 |
| 21 | `SC-3` | 3 | 3.67 | 4 | **44** | 2 |
| 22 | `OPS-5` | 3.33 | 3 | 4.33 | **43.3** | 1 |
| 23 | `EV-9` | 3.33 | 3 | 4.33 | **43.3** | 1 |
| 24 | `EV-2+EV-3` | 4.33 | 2.33 | 4 | **40.4** | 2 |
| 25 | `GS-4+OPS-6` | 4.67 | 2 | 4 | **37.3** | 1 |
| 26 | `OPS-1+SC-7` | 3.67 | 2.67 | 3.67 | **35.9** | 1 |
| 27 | `GS-3` | 4.33 | 2 | 4 | **34.7** | 1 |
| 28 | `SC-8` | 3 | 3 | 3.67 | **33** | 0 |
| 29 | `EV-7+GS-6` | 3.67 | 2.33 | 3.33 | **28.5** | 1 |
| 30 | `SC-1+SC-5` | 4.33 | 2 | 3 | **26** | 1 |

## 적대 리뷰 판정

| 약점 | 판정 | 이유 | 선행 |
|---|---|---|---|
| `EV-6+GS-5` | **adopt-with-change** | 봉쇄 방향 자체는 맞다 — split_body_appendix 는 주석 마커에 대해 '최초 출현'(APPX_COMMENT.search)을 쓰고 헤딩만 '최후 출현'(heads[-1])을 쓴다. 즉 문서 맨 앞줄에 마커 한 줄만 넣으면 문서 전체가 부록이 되고, verify() 는 body 만 check_bound_numbers/check_forbidden_patterns 에 넘기므로 무태그·값불일치·플레이스홀더·비밀 검사가 통째로 면제된다(실제 우회 경로 성립). 그러나 '마커 앞 본문 비율 60%' 임계는 기존 그린 픽스처를 즉시 빨갛게 만든다 — appendix_forward_bypass 의 긍정형 짝(good) 은 body 37자 / 전체 86자 = 비율 0.43 으로 실측된다. 또 '부록에도 검사 계 | none |
| `GS-2+GS-9+OPS-8` | **adopt** | 실패 시나리오를 실제로 막는다. 재현 완료: facts 만 있고 report.md·report.pdf 가 전혀 없는 작업폴더에서 RENDER·G4·G5 를 PASS 로 checkpoint 한 뒤 status 를 부르면 세 게이트 모두 'fresh' 로 나온다(_target_hashes 가 부재 파일을 아예 기록하지 않고, _gate_states 가 None != None 비교로 일치 판정). 즉 지금은 산출물 0개로 완료 선언이 가능하다. 심사관들이 든 반대 근거는 두 건 다 사실이 아니다 — (a) test_run_ledger.py:146 이 checkpoint 직전에 report_md 를 쓰고 있어 :147 은 '산출물 없이 G3 PASS' 가 아니며, completion_declaration_rules | none |
| `FP-1+COV-1` | **adopt-with-change** | MIME 쪽 진단은 정확하다 — ALLOWED_MIME 에 'application/rss' 가 있지만 판정은 `mime not in ALLOWED_MIME` 완전일치라, 실제 서버가 보내는 application/rss+xml·atom+xml·rdf+xml 은 전부 차단된다(즉 'application/rss' 항목은 죽은 상수다). 피드 계층 진단도 정확하다 — _rss_urls 는 base+'/rss' 같은 사이트 전역 피드를 합성하고, fetch() 는 validate_body 가 본문 1000자 이상이면 무조건 'ok' 를 주므로 요청한 기사와 무관한 피드 전문이 그 URL 의 본문으로 채택된다. 그러나 제안된 메커니즘의 후반부('그 외 타입은 차단이 아니라 bozo 플래그로 강등')는 기존 적대 케이스 | none |
| `BUG-1+BUG-2` | **reject** | 저장소 정본에는 두 버그가 이미 고쳐져 있다. harvest_images.py:145-148 이 `if not html: raw=r.get('raw'); html=raw.decode('utf-8','replace') if isinstance(raw,bytes)...` 로 폴백을 갖고 있고, :199 는 이미 `[...]['instances']` 를 파싱한다. 제안이 '심으라'는 demo 긍정형 assert 두 개도 이미 존재한다(page_images 스텁 통과 + 'https 접두' 전수 assert + instances https assert). demo 를 직접 실행해 OK 를 확인했다. 이 항목이 버그로 보인 이유는 채점이 설치본을 읽었기 때문이다 — 설치본 C:/Users/.../.claude/ski | none |
| `COV-2` | **adopt-with-change** | 진단은 맞다 — _via_wayback 은 closest 스냅샷 URL 만 res['archived_url'] 로 싣고 timestamp 를 어디에도 남기지 않아, 2019년 스냅샷이 '오늘 확인한 사실'로 대장에 들어갈 수 있다. Availability API 를 평문 http:// 로 부르는 것도 실측 확인(중간자가 스냅샷 URL 을 바꿔치기하면 증거 원문이 통째로 교체된다 — 이쪽이 시점 표기보다 심각한데 제안에서는 곁가지로 취급됐다). 59케이스에 wayback 픽스처가 없어 회귀 위험은 실제로 낮다. 다만 CDX 추가 호출과 target_window 강등은 값어치 대비 비용이 크고, 사다리 최후단이라 창을 좁히면 강방어 사이트의 유일한 생존 계층이 사라진다. | none |
| `ROT-1+MN-1` | **adopt-with-change** | 진단이 정확하고 재현 가능하다 — _ddg 는 예외를 잡아 [] 를 반환하고(:61-63), HTTP 200 에 챌린지 다이얼로그가 실려 와도 result__a 정규식이 안 걸려 조용히 [] 를 낸다. search() 는 이를 '결과 부족' 으로 읽고 searx 로 보강만 하므로, '차단됨' 과 '검색 결과 없음' 이 호출자에게 구분 불가다. _searx 의 백오프도 사실상 데드코드다 — 예외가 아닌 429/503 응답은 except 를 안 타고 :101 의 break 로 즉시 다음 인스턴스로 넘어가 delay 리스트가 한 번도 소비되지 않는다(제안이 지목한 status_forcelist 미명시와 동형 결함이 이 코드에 실재). 다만 suspend 상태를 프로세스 메모리에 두면 세션 재개마다 리셋돼 방어가  | OPS-7 |
| `GS-7+OPS-3+OPS-4` | **adopt-with-change** | 이 항목의 핵심 주장('에이전트가 쓴 user 답과 사용자가 쓴 답은 같은 프로세스에서 기계적으로 구분 불가')은 옳고, 그렇다면 airflow HITL 식 채널 분리는 이 실행모델에서 원리적으로 재현 불가다. 절반만 구현하고 '동의 위조를 막았다'고 문서에 쓰면 그게 순증 위험이다. 실행 가능한 잔여분은 작다 — --resolved-by 기본값 'user' 제거는 run_ledger.py:500 한 줄이고, 유일한 관련 테스트가 이미 명시 전달하고 있어 안전하다(tests/test_run_ledger.py:225,227,229). 반면 'PLAN/G0 checkpoint 전제조건으로 consent 이벤트 실재 + CLEAR/OKAY lane_verdicts 검사' 는 completion_declaratio | none |
| `OPS-2` | **adopt** | 가장 값싸고 부작용이 거의 없다. _update_metadata 가 만드는 meta 는 mode/completedAt/last_fresh_gate/fact_count/updated_at 5필드뿐이라 활성 ask 는 재개 시점에 어디에도 안 보인다. _active_ask() 헬퍼가 이미 존재하므로 additive 필드 1개를 붙이는 데 새 로직이 필요 없다. run-metadata 는 파생물이라 기존 조사폴더 호환 문제도 없다(실존 폴더엔 파일 자체가 없음). 다만 '활성 ask 가 있으면 checkpoint 거부' 부분은 성격이 다르다 — 이건 정상 시나리오(사용자가 대화로 답했지만 answer 레코드를 아직 안 남긴 상태)를 막고, 에이전트가 '가짜 answer 를 먼저 기록해 거부를 푸는' 새 우회를 유 | GS-2+GS-9+OPS-8 |
| `FP-2` | **adopt-with-change** | 제안이 지목한 근본원인이 이 코드베이스에서는 사실이 아니다 — scripts/ 전체에 latin-1/ISO-8859-1/cp1252 가 단 한 번도 등장하지 않는다(grep 0건). 따라서 exclude_encodings=['ISO-8859-1'] 는 여기서 no-op 이고, '이게 EUC-KR 모지바케가 예외 없이 통과하는 진짜 원인' 이라는 서술은 틀렸다. 실제 잔존 구멍은 다른 데 있다: fetch.py:232-234 는 선언 charset 으로 strict 디코드를 시도하고 실패하면 utf-8 errors='replace' 로 떨어지는데, 이 경로는 U+FFFD 로 가득한 문자열을 ok=True 로 반환하고 validate_body 는 바이트를 못 보므로 길이만 보고 'ok' 를 준다. 즉 '선언은  | none |
| `SC-2` | **adopt-with-change** | merge_evidence 는 지금 '존재하지 않는 함수를 가리키는 에러 메시지' 다 — facts_db.py:219-220 이 `동일 claim_key 존재: ... → merge_evidence/set_status 사용` 을 던지는데 merge_evidence 는 저장소 어디에도 없다. 즉 조사원이 같은 사실을 두 출처에서 잡았을 때 규정된 다음 행동이 실행 불가이고, 실제로는 claim_key 를 미세하게 비틀어 별건으로 등재하는 우회가 유일한 출구가 된다(실존 조사폴더의 facts.jsonl 에 중복 claim_key 4건 이상이 남아 있는 것이 그 흔적으로 읽힌다). 다만 자동 병합은 값 위조보다 발견이 어려운 오병합을 만들고, 특히 independent_groups>=2 라는 Bx 통과 조건을 가 | none |
| `EV-8` | **defer** | 이 배치에서 값어치가 가장 낮다. (1) '기존 조사폴더 호환' 논의 자체가 무의미하다 — 유일한 실존 조사폴더의 manifest.json 은 {run_id, created_at, tool_versions, files, gate_state} 스키마인데 현행 manifest.verify() 는 `json.loads(...)['entries']` 를 하므로 이미 KeyError 로 죽는다. 즉 호환은 EV-8 때문에 깨지는 게 아니라 이미 깨져 있고, EV-8 이 이를 고쳐주지도 않는다. (2) '--allow-change 명시 필요' 는 SKILL.md:70 이 정규 절차로 규정한 '[4b] 재봉인 — manifest.py build 재실행' 을 매번 플래그 붙이는 절차로 바꾼다. 플래그가 습관화되는 순간 방 | none |
| `GS-8` | **adopt** | 우회를 직접 재현했다. facts.jsonl 에 같은 claim_key 를 가진 위조 행을 앞에, 정직 행을 뒤에 두면 _fact_hashes 의 dict 덮어쓰기가 정직 행의 해시를 남기므로 G1 상태가 'fresh', changed_claim_keys 가 [] 로 나온다 — 위조 행이 대장에 실재하는데 게이트는 무변경이라고 보고한다. 반대로 위조 행을 뒤에 두면 partial_stale 로 잡힌다(즉 순서만으로 탐지를 껐다 켰다 할 수 있다). 중요한 보강: watches=['facts'] 인 게이트(G1·LV·BX·G2·G5C)는 _gate_states 에서 파일 sha256 을 아예 대조하지 않고 fact_hashes 만 보므로(:283-292), '파일 해시가 어차피 잡는다' 는 반론은 성립하지 않 | none |

> 랭킹 밖 선행 지적: 두 건이 상위 12 밖인데 먼저 와야 한다.

(1) [신규 — 랭킹에 없음] 저장소↔설치본 mirror 드리프트 가드. 전 파일 CRLF 정규화 해시 대조 결과 드리프트는 scripts/harvest_images.py 단 1건인데, 하필 그 파일이 BUG-1+BUG-2 가 겨냥한 파일이다. 즉 상위 4위 항목(85.6점)이 통째로 '설치본을 정본으로 착각한 유령 버그'였다. 이 가드 없이 다음 배치를 돌리면 같은 착오가 반복되고, 더 나쁘게는 새로 넣은 방어가 설치본에 반영 안 된 채 '막았다' 고 기록된다. 조치는 작다 — install.py 에 --check 모드(저장소↔설치본 해시 대조, 불일치 시 exit 1)를 넣고 test_adversarial 에 파리티 케이스 1건 추가. 실측 근거: 설치본 harvest_images.py 314줄 vs 저장소 341줄, 설치본 :145 `html = r.get("raw") or r.get("text") or ""`(bytes 를 정규식에 투입).

(2) OPS-7(카운터 비영속, 66.7점, 랭킹 13위)은 ROT-1+MN-1(6위, 80.9점)의 하드 선행조건이다. ROT-1 의 엔진 격리(suspend 3600/86400초)를 프로세스 메모리에 두면 세션 재개마다 초기화되어 방어가 사실상 존재하지 않고, 그 상태로 '차단 엔진을 격리한다' 를 문서에 쓰면 순증 위험이다. 두 항목은 run-metadata 영속화라는 같은 배관을 쓰므로 하나의 작업으로 묶어 OPS-7 을 먼저 놓는 편이 총비용도 낮다.

부수 관찰(항목화는 불필요, 문서에만 남길 것): 유일한 실존 조사폴더 research_글로벌_PEM_수전해_프로젝트_20260721 은 이미 세 겹으로 레거시다 — evidence.jsonl 부재(floor(c) 완화 경로), facts.jsonl 에 kind='evidence' 행 108건 혼입(verify_facts 가 [대장오염]으로 전건 FAIL 시킬 대상), manifest.json 이 구스키마('files')라 manifest.verify() 가 KeyError. 따라서 이번 배치의 어떤 항목도 '기존 조사폴더 호환' 을 이유로 완화하거나 예외 경로를 팔 필요가 없다. 예외 경로는 곧 우회 경로다.

## 이번 배치 채택 (13건)

### 1. `INSTALL-DRIFT` 저장소↔설치본 파리티 가드 (install.py --check)

- **메커니즘**: install.py 에 이미 있는 _sha/_iter_files 를 재사용해 --check 모드 추가: 저장소 파일과 설치본을 CRLF 정규화 후 해시 대조, 불일치 파일 목록을 stderr 로 출력하고 exit 1. 새 모듈·새 의존성 없음(약 15줄).
- **손댈 파일**: F:\Claude\projects\market-deep-research\codes\market-deep-research\scripts\install.py, F:\Claude\projects\market-deep-research\codes\market-deep-research\tests\test_adversarial.py
- **완료 판정**: 신규 케이스 install_parity_drift_detected: 임시 설치본을 만들고 파일 1개를 변조한 뒤 install.check() 가 그 경로를 반환하고 exit code 1 을 내는 것. 동기 상태에서는 빈 목록 + exit 0. 그리고 이번 배치 종료 시 `python scripts/install.py --check` 가 실제로 0 을 반환할 것.
- 비고: 랭킹에 없던 신규 항목인데 1순위다. 이번 심사 4위(85.6점) BUG-1+BUG-2 가 통째로 유령이었던 원인이 이 드리프트다 — 저장소 harvest_images.py:145-148·:199 는 이미 수정본이고 demo assert 까지 있는데, 설치본(314줄, 저장소 341줄)만 미수정이었다. 가드 없이 다음 배치를 돌리면 새로 넣은 방어가 설치본에 없는 채 '막았다' 로 기록된다.

### 2. `GS-2+GS-9+OPS-8` watch 파일 부재를 fresh 가 아니라 missing_watch 로 반전 (게이트 자기신고 차단의 뿌리)

- **메커니즘**: _target_hashes 가 부재 파일을 생략하지 말고 missing 센티널로 기록하고, _gate_states 에 'missing_watch' state 를 신설, _completion_possible 에서 제외. checkpoint 자체는 거부하지 않는다(영수증은 남기고 완료 판정이 관문). 로스터 missing==0 을 완료 조건에 추가.
- **손댈 파일**: F:\Claude\projects\market-deep-research\codes\market-deep-research\scripts\run_ledger.py, F:\Claude\projects\market-deep-research\codes\market-deep-research\tests\test_run_ledger.py
- **완료 판정**: 재현 테스트: facts 만 있고 report.md/report.pdf 가 없는 작업폴더에서 RENDER·G4·G5 를 PASS checkpoint → 세 게이트 state 가 모두 'missing_watch' 이고 _completion_possible() 이 False, run-metadata.completedAt 이 None. 산출물을 만들고 재-checkpoint 하면 'fresh' + completedAt 채워짐. 기존 13개 ledger 케이스 전건 그린 유지.
- 비고: 현재 실측 재현 완료 — 산출물 0개로 11게이트 PASS + 완료 선언이 성립한다. 순서 2번인 이유: 대장 판정 경로 변경이라 뒤의 GS-8·OPS-7·OPS-2·GS-7 이 전부 이 함수 위에 얹힌다. legacy 예외 경로는 넣지 말 것 — 실존 조사폴더에 봉인된 PASS 가 없어 보호 대상이 없고, 예외 경로 자체가 '레거시로 위장하면 열린다' 는 새 우회로다.

### 3. `GS-8` claim_key 중복 시 해시 덮어쓰기 제거 — 정렬 후 결합

- **메커니즘**: _fact_hashes 의 out[key]=sha 덮어쓰기를 폐기하고, 같은 claim_key 그룹의 해시들을 정렬한 뒤 sha256(concat) 으로 결합. 어느 행이 바뀌어도 결합값이 실효되고, 행 순서 재배치는 값을 바꾸지 않는다.
- **손댈 파일**: F:\Claude\projects\market-deep-research\codes\market-deep-research\scripts\run_ledger.py, F:\Claude\projects\market-deep-research\codes\market-deep-research\tests\test_run_ledger.py
- **완료 판정**: (a) 같은 claim_key 위조행을 앞, 정직행을 뒤에 둔 facts.jsonl 에서 G1 state 가 'partial_stale' 이고 changed_claim_keys 에 그 키가 포함될 것(현재는 'fresh' + [] 로 나옴). (b) 순서 독립성: 두 행을 뒤바꿔도 _fact_hashes 결과가 동일할 것. 중복 없는 폴더는 값 불변(회귀 없음).
- 비고: watches=['facts'] 게이트(G1·LV·BX·G2·G5C)는 파일 sha256 을 아예 대조하지 않고 fact_hashes 만 보므로(run_ledger.py:283-292) '파일 해시가 어차피 잡는다' 는 반론은 성립하지 않는다. 해시 알고리즘 버전 폴백은 넣지 말 것 — '옛 규칙으로 비교' 가 곧 새 우회로다.

### 4. `OPS-7` 런타임 카운터 영속화 (ROT-1 의 하드 선행조건)

- **메커니즘**: _update_metadata 에 additive 로 counters{respawn_by_lane, wave, interview_round, autoconfirm_streak, suspended_engines} 를 대장 재생 결과로 산출·기록. 파생 상태를 직접 쓰지 않고 ledger 재생으로 계산하는 쪽을 정본으로.
- **손댈 파일**: F:\Claude\projects\market-deep-research\codes\market-deep-research\scripts\run_ledger.py, F:\Claude\projects\market-deep-research\codes\market-deep-research\tests\test_run_ledger.py
- **완료 판정**: counters 부재 대장에서 전 필드 0 으로 폴백하고, respawn/wave 레코드 append 후 status() 재호출 시 값이 증가해 있을 것. run-metadata.json 을 삭제하고 재계산해도 같은 값이 나올 것(재생 정본 확인).
- 비고: 단독 가치는 낮지만(예산 사고) ROT-1 의 엔진 suspend 를 프로세스 메모리에 두면 세션 재개마다 리셋되어 방어가 0 이 된다. 같은 _update_metadata 배관이라 OPS-2 와 한 덩어리.

### 5. `OPS-2` active_ask 를 재개 진입점에 노출 (additive, checkpoint 거부는 제외)

- **메커니즘**: 이미 존재하는 _active_ask() 헬퍼를 재사용해 _update_metadata 에 optional active_ask{ask_id, gate_id, question, asked_at} 를 싣고, handoff 필수 섹션과 재개 다이제스트에 '미답 ask' 슬롯을 명시. status 출력에도 표면화.
- **손댈 파일**: F:\Claude\projects\market-deep-research\codes\market-deep-research\scripts\run_ledger.py, F:\Claude\projects\market-deep-research\codes\market-deep-research\references\, F:\Claude\projects\market-deep-research\codes\market-deep-research\tests\test_run_ledger.py
- **완료 판정**: record ask 직후 metadata.active_ask 가 {ask_id, gate_id, question} 를 담고, 대응 answer 기록 후 None 이 될 것. 기존 ask/answer 케이스 2건 그린 유지.
- 비고: '활성 ask 가 있으면 checkpoint 거부' 는 뺐다 — GS-7 에서 확인했듯 answer 는 에이전트가 쓸 수 있으므로, 거부 게이트는 '가짜 answer 를 먼저 기록해 거부를 푸는' 새 우회를 유도하고 정상 시나리오(사용자가 대화로 답한 상태)만 막는다.

### 6. `GS-7(축소)` --resolved-by 필수 인자화 + consent 를 불변 이벤트로 + 한계 명문화

- **메커니즘**: run_ledger.py:500 의 default='user' 제거(필수 인자화), consent 를 한 줄 필드가 아니라 {ts, actor, actor_channel, payload} 불변 레코드로 기록(additive). 그리고 SKILL.md·verification-gates.md 에 '동의 위조는 이 실행모델에서 기계적으로 차단 불가 — 이 기록은 감사 흔적이지 인증이 아니다' 를 명문화.
- **손댈 파일**: F:\Claude\projects\market-deep-research\codes\market-deep-research\scripts\run_ledger.py, F:\Claude\projects\market-deep-research\codes\market-deep-research\SKILL.md, F:\Claude\projects\market-deep-research\codes\market-deep-research\references\verification-gates.md, F:\Claude\projects\market-deep-research\codes\market-deep-research\tests\test_run_ledger.py
- **완료 판정**: (a) `record answer --ask-id X --answer Y` 를 --resolved-by 없이 호출하면 exit 2(argparse required). (b) consent 레코드가 4필드를 모두 갖고 actor_channel 이 기록될 것. (c) 문서 앵커 테스트: verification-gates.md 에 '인증이 아니다' 취지 문구가 존재하는지 assert(기존 anchor assert 패턴 재사용).
- 비고: PLAN/G0 checkpoint 전제조건(consent 이벤트 실재 + lane_verdicts 검사) 은 뺐다 — completion_declaration_rules 케이스가 11게이트를 ask/lane_verdicts 없이 PASS checkpoint 하므로 즉시 red 다. 기본값 제거는 안전함을 실측 확인(tests/test_run_ledger.py:225,227,229 가 이미 명시 전달). 이 항목의 절반은 코드가 아니라 한계 명시다 — 반쯤 구현하고 '막았다' 고 쓰면 그게 순증 위험이다.

### 7. `EV-6(축소)` 부록 마커 우회 봉쇄 — 최후 출현 + 개수 제한 + 부록 잔여검사 (비율 임계·AST 제외)

- **메커니즘**: split_body_appendix 의 APPX_COMMENT 를 헤딩 폴백과 동일하게 '최후 출현'(finditer 의 마지막) 으로 바꾸고, 마커가 2개 이상이면 즉시 FAIL. 부록 구간에도 [오태그]·[미확정]·플레이스홀더·비밀문자열 4종 검사는 계속 적용해 면제 구간을 없앤다.
- **손댈 파일**: F:\Claude\projects\market-deep-research\codes\market-deep-research\scripts\verify_facts.py, F:\Claude\projects\market-deep-research\codes\market-deep-research\tests\test_adversarial.py
- **완료 판정**: 신규 케이스 2건 — (a) 문서 첫 줄에 APPENDIX 주석 마커를 넣은 보고서가 verify() 에서 FAIL(현재는 본문 전체가 부록이 되어 무태그·플레이스홀더 검사가 전부 면제되어 PASS). (b) 마커 2개 문서가 전용 사유로 FAIL. 기존 appendix_bypass_blocked·appendix_forward_bypass 및 verify_facts.demo() 그린 유지.
- 비고: '마커 앞 본문 비율 60%' 임계는 반드시 제외 — appendix_forward_bypass 의 긍정형 짝이 body 37자/전체 86자 = 0.43 이라 켜는 순간 red 다. 부록 확대 검사도 [값불일치]·[무태그] 는 절대 포함하지 말 것(demo 부록 픽스처가 '999조원(F001)' 값 불일치를 의도적으로 담고 있음). 실효 8할이 2줄에 있고 AST 승격 없이도 마커 게임은 닫힌다.

### 8. `FP-1(축소)` MIME 정확일치 폐기 — +xml 접미 규칙 (bozo 강등은 제외)

- **메커니즘**: feedparser 의 판정 규칙만 이식: application/* 이면서 endswith('+xml') 이거나 명시 화이트리스트({application/xml, application/xml-dtd}) 면 XML 로 통과. 목록 밖은 지금처럼 차단 유지(octet-stream PDF 매직바이트 예외는 이미 있음). text/* 전면 개방 금지.
- **손댈 파일**: F:\Claude\projects\market-deep-research\codes\market-deep-research\scripts\fetch.py, F:\Claude\projects\market-deep-research\codes\market-deep-research\tests\test_adversarial.py
- **완료 판정**: 긍정형 신규 assert: application/rss+xml, application/atom+xml, application/rdf+xml 응답이 ok 로 통과. 기존 disallowed_mime_rejected(video/mp4 → not ok and reason.startswith('mime:')) 그린 유지.
- 비고: 현행 ALLOWED_MIME 의 'application/rss' 는 완전일치 판정(fetch.py:225) 아래에서 죽은 상수다 — 실제 서버가 보내는 rss+xml 은 전부 차단되고 있다. 'bozo 플래그로 강등' 은 채택하지 말 것: disallowed_mime_rejected 를 뒤집고 '아무 MIME 이나 경고만 달고 통과' 라는 새 우회로를 연다.

### 9. `COV-1` 피드 item↔대상 URL 일치 검증 — 남의 기사가 원문으로 저장되는 오염 차단

- **메커니즘**: _rss_urls 가 합성한 파생 피드(base+'/rss' 류)로 본문을 얻은 경우에 한해, 피드를 파싱해 <link> 가 대상 URL 과 일치하는 item 의 본문만 ok 로 인정하고 일치 없으면 partial 로 강등. 원 URL 자체가 피드인 정상 케이스에는 적용하지 않는다.
- **손댈 파일**: F:\Claude\projects\market-deep-research\codes\market-deep-research\scripts\fetch.py, F:\Claude\projects\market-deep-research\codes\market-deep-research\tests\test_adversarial.py
- **완료 판정**: 신규 케이스 feed_item_mismatch_downgraded: 대상 URL 이 없는 사이트 전역 피드를 스텁으로 주면 verdict=='partial' + 사유에 피드 불일치 명시. 일치 item 이 있으면 ok. 기존 fetch 케이스 그린 유지.
- 비고: EV-1 이 '해시가 아무거나' 라면 이건 '해시는 맞는데 내용이 남의 글' 이다 — validate_body 가 본문 1000자면 무조건 ok(fetch.py:164-166)라, 요청한 기사와 무관한 피드 전문이 그 URL 의 원문으로 저장·해시된다. 재검증 게이트가 같은 바이트열을 다시 열어 완벽히 일치한다고 보고하므로 원리적으로 미검출.

### 10. `FP-2(축소)` 디코드 사다리 + 모지바케 후검증 — '읽을 수 없는 쓰레기'를 성공에서 배제

- **메커니즘**: fetch.py:232-234 의 '선언 charset strict 실패 → utf-8 replace' 를 declared → utf-8 → cp949/euc-kr strict 순 재시도로 바꾸고, 최종 문자열의 U+FFFD 비율이 임계 초과면 결과에 mojibake 사유를 실어 validate_body 에서 partial 강등. 임계는 gates.json knob(초기값 0.02, 느슨하게).
- **손댈 파일**: F:\Claude\projects\market-deep-research\codes\market-deep-research\scripts\fetch.py, F:\Claude\projects\market-deep-research\codes\market-deep-research\assets\gates.json, F:\Claude\projects\market-deep-research\codes\market-deep-research\tests\test_adversarial.py
- **완료 판정**: (a) '선언은 utf-8, 실체는 euc-kr' 바이트열이 cp949 폴백으로 U+FFFD 0개로 디코드될 것. (b) 의도적 깨진 바이트열은 verdict=='partial' + mojibake 사유. (c) 기존 euckr_decoded_without_replacement 그린 유지.
- 비고: 제안된 근본원인('latin-1 이 모든 바이트를 디코드해서')은 이 코드베이스에서 사실이 아니다 — scripts/ 전체에 latin-1/8859/cp1252 가 0회 등장한다. 실제 구멍은 utf-8 errors='replace' 폴백이 U+FFFD 범벅 문자열을 ok=True 로 돌려주고 validate_body 는 길이만 본다는 것. charset_normalizer/bs4 도입 금지(preflight 의존성 밖). 한글 음절 비율 AND 조건도 넣지 말 것 — 영문 위주 한국 사이트에서 오탐.

### 11. `COV-2(축소)` Wayback 스냅샷 시점 병기 + https (target_window·CDX 는 제외)

- **메커니즘**: _via_wayback 의 Availability API 를 https 로 교체하고, closest.timestamp 를 파싱해 결과에 snapshot_date/actual_ts 를 additive 로 실어 evidence 에 병기. 본문은 배너·리라이팅 없는 id_ URL(/web/<ts>id_/<url>)로.
- **손댈 파일**: F:\Claude\projects\market-deep-research\codes\market-deep-research\scripts\fetch.py, F:\Claude\projects\market-deep-research\codes\market-deep-research\tests\test_adversarial.py
- **완료 판정**: 스텁 응답으로 _via_wayback 결과에 snapshot_date 가 ISO 날짜로 실릴 것, 호출 URL 이 https:// 로 시작할 것, 본문 요청 URL 에 'id_/' 가 포함될 것. 59케이스에 wayback 픽스처가 없어 회귀 위험 없음.
- 비고: 현재 평문 http:// 로 아카이브 URL 을 받아온다 — 중간자가 스냅샷 URL 을 바꿔치기하면 증거 원문이 통째로 교체되는데, 이쪽이 시점 표기보다 심각한데도 원안에서는 곁가지였다. target_window 강등과 CDX statuscode/digest 조회는 다음 배치 — 창을 좁히면 강방어 사이트의 유일한 생존 계층이 사라진다. 소급 판정 불가(신규 run 부터)를 문서에 명시.

### 12. `ROT-1+MN-1(축소)` 차단과 무결과의 타입 분리 + 429 백오프 데드코드 수리 + 엔진 격리 영속화

- **메커니즘**: (a) search.py:101 의 무조건 break 를 st==429/503 일 때만 백오프 루프를 지속하도록 고쳐 죽은 백오프 리스트를 살린다. (b) DDG 200-차단은 본문 마커(challenge-form id, DDG.deep.anomalyDetectionBlock)로 판정해 blocked 로 분리. (c) search() 반환을 {results, blocked_engines[]} 로 additive 확장(예외 승격 금지). (d) suspend 상태는 OPS-7 의 counters.suspended_engines 로 영속화. 마커 목록은 코드 리터럴이 아니라 assets JSON.
- **손댈 파일**: F:\Claude\projects\market-deep-research\codes\market-deep-research\scripts\search.py, F:\Claude\projects\market-deep-research\codes\market-deep-research\assets\, F:\Claude\projects\market-deep-research\codes\market-deep-research\tests\test_adversarial.py
- **완료 판정**: (a) 200 + 챌린지 본문 스텁 → results 빈 리스트이면서 blocked_engines 에 'ddg' 포함(현재는 그냥 [] 라 '결과 없음' 과 구분 불가). (b) 429 응답 스텁에서 백오프 sleep 이 실제로 소비될 것(sleep 호출 카운터 assert) — 현재는 첫 회 break 로 0회. (c) suspend 기록 후 새 프로세스에서 status() 를 불러도 격리가 유지될 것.
- 비고: OPS-7 선행 필수 — suspend 를 프로세스 메모리에 두면 세션 재개마다 리셋되어 '검사하는 척' 이 된다. 시그널 판독 실패는 cloudscraper 규약대로 '차단 아님' 으로 안전측 처리하고, 반환 타입을 예외로 바꾸지 말 것(search() 호출부 전부를 건드린다).

### 13. `SC-2(축소)` merge_evidence 실구현 — 존재하지 않는 함수를 가리키던 에러 해소 (fail-closed 규칙)

- **메커니즘**: add_fact 의 ValidationError 는 그대로 두고 merge_evidence 를 별도 진입점으로 추가. 규칙: (1) 병합은 claim_key 완전일치일 때만(유사도는 후보 제시용이며 자동 병합 근거로 쓰지 않는다), (2) 값이 다르면 무조건 conflict 레코드로 떨어뜨리고 자동 채택 금지, (3) evidence_ids 는 합집합이되 출처 도메인이 같으면 같은 observer_group 으로 접는다, (4) 모든 병합은 run-ledger 에 merge 레코드로 흔적을 남긴다.
- **손댈 파일**: F:\Claude\projects\market-deep-research\codes\market-deep-research\scripts\facts_db.py, F:\Claude\projects\market-deep-research\codes\market-deep-research\tests\test_adversarial.py
- **완료 판정**: (a) 같은 claim_key·같은 값 2건 병합 → fact 1건, evidence_ids 합집합, 같은 도메인 출처는 independent_groups 가 2가 아니라 1. (b) 값이 다르면 병합 거부 + conflict 레코드 생성 + 두 행 모두 잔존. (c) 병합 시 run-ledger 에 merge 레코드 1건. (d) 기존 dup_fact_and_claimkey(ValidationError 단언) 그린 유지.
- 비고: facts_db.py:220 이 저장소 어디에도 없는 merge_evidence 를 해법으로 안내한다 — 규정된 다음 행동이 실행 불가라서 실제 출구는 claim_key 를 비틀어 별건 등재하거나 JSONL 손편집이고, 실존 조사폴더 facts.jsonl 에 중복 claim_key 4건 이상이 그 흔적으로 남아 있다. rapidfuzz blocking/union-find 는 과설계 — 대장이 100건 단위라 O(N²) 로 충분하다. (3)번 규칙이 핵심: 없으면 병합만으로 Bx 의 '독립 관찰그룹 ≥2' 가 가짜 충족된다.

## 다음 배치로 유예 (12건)

| 약점 | 이유 | 선행 조건 |
|---|---|---|
| `EV-1` | 증거 무결성 축의 루트(아무 64자 hex 나 통과)라 impact 는 최상위지만, 이번 배치에 넣으면 '그린 유지' 가 아니라 '그린 재획득' 이 된다. 적대 테스트의 add_evidence 호출 18곳 중 local 을 실은 것이 2곳뿐이고, 전 confirmed fact 생성 경로인 _confirm() 헬퍼가 local 없는 evidence 를 만든다. | _confirm() 헬퍼가 _sources/ 에 실파일을 쓰고 그 실해시를 넣도록 픽스처를 승격하는 '픽스처 마이그레이션 배치' 를 먼저 돌릴 것. 그 배치는 EV-2+EV-3·EV-5·SC-4 와 픽스처 비용을 공유하므로 반드시 한 번에 지불한다. 적용 범위는 risk=high + 본문 결박 fact 로 먼저 좁혀 단계 배선. |
| `EV-2+EV-3` | 캡처 1장을 복제하면 evidence 80건이 통과하는 구멍은 실재하지만, 59케이스 중 11곳이 b'\x89PNG' 4바이트 스텁을 쓴다 — fitz 로 열리지 않아 dhash·tEXt 청크가 원리적으로 불가하고, 전부 바이트가 동일해 '동일 capture 해시 FAIL' 규칙에 즉시 대량 red. | EV-1 과 같은 픽스처 마이그레이션(진짜 PNG 생성) 완료. 그 뒤에도 최소 회수분(capture_sha256 중복 FAIL + 파일명 stem↔evidence.id 결박) 만 먼저 넣고, dhash 는 '1픽셀 회피' 가 실제 관측된 뒤에. 청크 부재는 WARN, 불일치만 FAIL 로 2단. |
| `SC-4` | 백지 캡처 기계검출은 육안 게이트를 지속 가능하게 만드는 옳은 방향이지만, 단독 착수 항목이 아니라 EV-2+EV-3 의 픽셀 접근 유틸의 부수효과다. 지금 넣으면 4바이트 스텁에서 예외를 던진다. | EV-2+EV-3 의 PyMuPDF Pixmap 유틸이 존재할 것. 그 뒤 검사를 capture_*.py 생성 시점에만 넣어 59케이스 무영향으로 시작하고, 임계는 gates.json knob 으로 노출한 뒤 실측 후 verify 쪽 승격. |
| `EV-5` | '팀리드 전건 재검증' 이 by="lead" 문자열 한 줄인 건 이 스킬 최대 차별점의 공백이지만, 공용 _confirm() 헬퍼가 add_verify_event(fid,'lead','reread') 최소 인자만 호출해 필드 필수화가 17개 케이스를 동시에 건드린다. | (1) 픽스처 마이그레이션, (2) GS-1 의 실행기록 구조체 모양 확정 — 따로 설계하면 대장에 유사하지만 다른 스키마가 두 벌 생긴다. 시간 순서 강제는 >= 로 완화(픽스처가 같은 초에 생성). |
| `GS-1` | '산문 선언은 증거가 아니다' 를 자료구조로 바꾸는 유일한 처방이고 재사용 반경이 가장 넓지만, 배선 범위가 이번 배치 예산을 통째로 먹는다. 전 게이트 일괄 배선은 G4(육안)·PLAN(합의)에서 교착이 되고, Windows subprocess 인코딩·경로 이슈를 새로 만든다. | 이번 배치의 missing_watch 상태 분리가 먼저 착지할 것(verify_cmd 결과가 먹일 state 가 있어야 한다). 그 뒤 gates.json 에 optional verify_cmd 를 선언한 게이트만 opt-in 으로 시작하고, 무거운 검증기는 '결과 JSON 경로 + 해시 대조' 모드를 병행 제공. |
| `EV-8` | 머클 체인 이전에 manifest 자체가 이미 깨져 있다 — manifest.verify() 는 json['entries'] 를 읽는데 실존 조사폴더의 manifest.json 은 {run_id, created_at, tool_versions, files, gate_state} 스키마라 KeyError 로 죽는다. 체인은 이를 고쳐주지도 않는다. 서명 없는 체인은 외부 앵커가 없어 재작성 공격을 원리적으로 못 막는다. | manifest 스키마 마이그레이션(구스키마 'files' 판독 시 죽지 않고 안내) 선행. 그 배치에서 TRACKED 에 '_reconstructed/**' 추가(capture_web.py:28-29·facts_db.py:113-114 가 이미 이 디렉터리를 특별 취급하므로 정합적)까지 같이. 머클 체인·manifest_root·TUF version 은 그 뒤. |
| `GS-4+OPS-6` | '45조→60조 수정 후 재열람 없이 PASS 재기록으로 fresh 복귀' 는 신선도 모델을 통째로 무의미하게 만드는 최상위 결함이지만, BLOCK 승격이 bx-blocked 라 지금 넣을 수 있는 건 WATCH 배선뿐이다. | PEM 대장 마이그레이션. 다만 이번 배치의 missing_watch 도입으로 WATCH 의 완료 집계 의미가 정리되므로, 마이그레이션 후에는 이 항목이 곧바로 값을 갖는다. 이 항목과 GS-3 두 건이 마이그레이션 비용을 정당화하는 근거다. |
| `GS-3` | 'evidence.jsonl 을 안 만들면 스키마 위반이 WATCH 로 강등' 이라는 공식 우회로는 impact 최상위지만 핵심 전환(신규 run 에서 부재=BLOCK)이 bx-blocked 다. 지금 가능한 조각(댕글링 evidence_ids 검사)은 evidence.jsonl 부재 모드에서 애초에 동작하지 않아 이번 악용 경로를 못 막는다. | PEM 대장 마이그레이션. 그리고 legacy 판정을 '파일 부재' 가 아니라 '배치1 이전 타임스탬프/마커 실재' 로 좁히는 작업 — 완화 조건이 '증거가 없음' 인 것 자체가 설계 오류다. |
| `OPS-5` | 승인된 계획과 최종 보고서 축이 다른데 전 게이트 PASS 가 나는 건 GS-7 과 같은 축의 실패지만, gates.json watches 에 research_plan 을 추가하는 순간 tests/test_run_ledger.py:60 의 화이트리스트 assert(set(watches) <= {facts, report_md, report_pdf})가 즉시 실패한다. | 이번 배치의 missing_watch 판정 규칙이 안정화될 것 — 신선도 판정 형태를 한 배치에서 두 번 흔들지 않는다. 그 뒤 watches 어휘 확장을 독립 변경으로. 계획 전문이 아니라 축·out-of-scope 핵심 섹션만 해시 대상으로 좁혀야 오탐 stale 과 형식적 steering 남발을 피한다. |
| `FP-3` | ok 판정이 원시 HTML 길이(1000자)에 걸려 있어 쿠키 동의창·페이월 티저·장문 404 가 원문으로 채택되는 건 맞고 trafilatura 는 이미 HARD 의존성이지만, 게이트 기준 교체라 fetch 관련 픽스처 다수가 반전될 수 있다. 이번 배치가 이미 validate_body 를 FP-1/COV-1/FP-2 로 세 번 만진다. | 이번 배치의 validate_body 변경이 착지하고 그린이 재확인될 것. 그 뒤 MIN_EXTRACTED_SIZE=250 전환을 단독 변경으로 하고, 베이스라인 프로브(오리진당 1회)는 강방어 사이트에서 스캐너로 인식될 수 있으니 우회 계층 앞에 두지 말 것. |
| `EV-4 / EV-7+GS-6 / EV-9` | 세 건 모두 _vals/_qty/UNIT/split_segments 라는 같은 코드 영역을 만진다 — 따로 착수하면 verify_facts 심장부를 세 번 흔들게 된다. 특히 EV-7 의 화이트리스트→denylist 반전은 검사 범위 급확장이라 report.md 픽스처에서 신규 [무태그] FAIL 이 다발한다. | '수치 인식·결박 리팩터' 라는 하나의 배치로 묶을 것. denylist 반전과 캡처 요구 확대는 반드시 WARN 티어로 먼저 배선하고 실측 후 승격. EV-9 의 GFM 표 파싱은 실패 시 기존 폴백으로 안전 복귀하는 경로를 남길 것. |
| `SC-1+SC-5 / SC-3 / SC-6 / OPS-1+SC-7 / SC-8` | 수렴·예산·스케일 계열은 대부분 정본 문서 개정이 본체이고 코드 회수가 작다. OPS-1(대장 락)은 lost-update 를 막지만 쓰기 경로 전면 교체라 회귀 반경이 가장 넓고, PEM 대장 마이그레이션과 같은 파일을 건드리므로 따로 하면 마이그레이션을 두 번 하게 된다. | OPS-1 은 PEM 대장 마이그레이션 배치에 합류(msvcrt 락은 강제 락이라 감사 번들 복사·Defender 스캔에서 PermissionError 가 나므로 temp+os.replace 에 지수 백오프 재시도 래퍼 동반 필수). SC-3/SC-6 은 termination_terms_unified·depth_cap_default_present·axis_scoped_convergence 3건이 문구를 직접 assert 하므로 문서 개정과 동시 갱신. SC-1 의 verify 캐시는 rule_set_sha 를 키에 반드시 섞을 것 — 빠뜨리면 '규칙을 조였는데 옛 PASS 가 살아있는' 상태가 되어 이번 감사가 잡은 결 |

## 하지 않기로 한 것 (10건)

| 항목 | 이유 |
|---|---|
| BUG-1+BUG-2 | 저장소 정본에는 이미 고쳐져 있다. harvest_images.py:145-148 이 raw bytes 디코드 폴백을 갖고 있고 :199 는 ['instances'] 를 파싱하며, 제안이 '심으라' 는 demo 긍정형 assert 두 개도 이미 존재한다. 채점이 설치본(314줄, 미수정)을 읽어 생긴 유령 항목이다 — 랭킹 4위(85.6점)에 배정된 작업량은 0 이다. 대신 order 1 의 INSTALL-DRIFT 로 대체했다. |
| EV-6 의 '본문 비율 60%' 임계 + AST 승격 | 비율 임계는 켜는 즉시 appendix_forward_bypass 의 긍정형 짝 픽스처를 red 로 만든다(body 37자/전체 86자 = 0.43 실측). 이건 '픽스처가 틀렸다' 가 아니라 '짧은 보고서 오탐' 의 증거다. AST 승격은 최후출현+개수제한만으로 마커 게임이 닫히므로 이번 라운드에 비용을 지불할 이유가 없다. |
| FP-1 의 'MIME 불일치는 차단이 아니라 bozo 강등' | disallowed_mime_rejected 케이스가 video/mp4 에 대해 reason.startswith('mime:') 차단을 직접 단언한다. 차단을 강등으로 바꾸면 그 케이스가 red 일 뿐 아니라 '아무 MIME 이나 경고만 달고 통과' 라는 새 우회로를 연다. 방어를 늘린다고 하면서 실제로는 게이트를 여는 변경이다. |
| GS-7 의 airflow 식 채널 분리 (방어로서) | '에이전트가 쓴 user 답' 과 '사용자가 쓴 답' 은 같은 프로세스 안에서 기계적으로 구분 불가하다 — 이 실행모델(에이전트가 CLI 를 직접 호출)에서 채널 분리는 원리적으로 재현 불가다. 근사만 구현하고 '동의 위조를 막았다' 고 문서에 쓰면 그게 순증 위험이다. 감사 흔적(불변 이벤트)까지가 도달 가능한 상한이고, 한계 명문화가 이 항목의 절반이다. |
| '활성 ask 가 있으면 checkpoint 거부' / EV-8 의 '--allow-change 필수' | 둘 다 마찰만 만들고 방어가 되지 않는 게이트다. 전자는 answer 를 에이전트가 쓸 수 있으므로 '가짜 answer 를 먼저 기록해 거부를 푸는' 경로를 유도하고, 후자는 SKILL.md:70 이 정규 절차로 규정한 '[4b] 재봉인' 을 매번 플래그 붙이는 절차로 바꿔 플래그 습관화 → 방어 0 으로 귀결된다. 변경 자체를 막지 말고 history 에 사유와 함께 남기는 쪽이 실효적이다. |
| COV-2 의 target_window 강등 + CDX 추가 호출 | wayback 은 사다리 최후단이라 허용창을 좁히면 폐업·개편 사이트의 유일한 증거가 통째로 사라져 커버리지가 급락한다. 시점 병기(additive)만으로 '5년 전 수치가 현재 원문으로 결박' 되는 문제의 판단 근거는 팀리드에게 넘어간다. CDX 는 요청 1회 추가 대비 회수가 작다. |
| '기존 조사폴더 호환' 을 이유로 한 legacy 예외 경로 일반 | 유일한 실존 조사폴더는 이미 세 겹으로 레거시다 — audit/run-ledger.jsonl 자체가 없고, facts.jsonl 에 kind='evidence' 행 108건이 혼입돼 verify_facts 가 [대장오염]으로 전건 FAIL 시킬 대상이며, manifest.json 이 구스키마다. 즉 보호할 봉인 상태가 없다. 예외 경로는 곧 우회 경로이고 '레거시로 위장하면 열린다' 를 만든다. |
| SC-2 의 rapidfuzz blocking + difflib 유사도 자동병합 + union-find | 대장 규모가 100건 단위라 O(N²) 로 충분하고 3단 설계는 과설계다. 더 중요하게 유사도 기반 자동 병합은 값 위조보다 발견이 어려운 오병합을 만들고, 서로 다른 사실을 한 claim_key 로 뭉쳐 은폐한다. 유사도는 후보 제시용까지만. |
| FP-2 의 exclude_encodings=['ISO-8859-1'] 서사 + charset_normalizer/bs4 도입 | scripts/ 전체에 latin-1/8859/cp1252 가 0회 등장하므로 여기서 no-op 이다 — '이게 EUC-KR 모지바케가 통과하는 진짜 원인' 이라는 진단이 틀렸다. 라이브러리 도입은 preflight 의존성 밖이라 라이브 환경에서 ImportError 로 수집 스택 전체가 죽는다. 실물 수정 4줄로 충분하다. |
| ROT-1 의 검색 반환 타입 예외 승격 + 마커 상수 하드코딩 | [] 반환을 blocked 예외로 바꾸면 search() 호출부 전부에 분기 추가가 필요하고 기존 fixture 가 빈 리스트를 기대하면 red 다. additive 반환({results, blocked_engines})으로 같은 정보를 얻는다. 차단 마커 목록은 노후하므로 코드 리터럴이 아니라 assets JSON. |

## 배치 요약

13건 채택. 세 필수 축을 모두 담았다 — (1) 실증된 무음실패 수정: ROT-1(search.py:101 의 break 로 429 백오프가 데드코드, 차단과 무결과가 구분 불가), FP-1(ALLOWED_MIME 의 'application/rss' 가 완전일치 판정 아래 죽은 상수라 실제 rss+xml 전량 차단), FP-2(utf-8 errors='replace' 폴백이 U+FFFD 범벅을 ok 로 반환), SC-2(존재하지 않는 merge_evidence 를 해법으로 안내). (2) 게이트 자기신고 차단: GS-2(산출물 0개로 11게이트 PASS + 완료 선언 — 실행 재현 완료), GS-8(중복 claim_key 해시 덮어쓰기로 위조행이 fresh 로 은폐 — 실행 재현 완료), GS-7(--resolved-by 기본값 user). (3) 증거 결박: EV-6(주석 한 줄로 본문 전체가 검사 면제 — APPX_COMMENT.search 최초출현 vs heads[-1] 최후출현 비대칭), COV-1(남의 기사가 대상 URL 의 원문으로 저장·해시), COV-2(스냅샷 시점 미기록 + 평문 http 아카이브 조회).

순서 원칙 두 가지를 지켰다. 첫째, 대장 판정 경로(GS-2 missing_watch)를 2번에 놓아 그 위에 얹는 GS-8·OPS-7·OPS-2·GS-7 이 전부 뒤따르게 했다. 둘째, OPS-7(카운터 영속화, 랭킹 13위)을 ROT-1(6위) 앞에 놓았다 — suspend 를 프로세스 메모리에 두면 세션 재개마다 리셋되어 엔진 격리가 '검사하는 척' 이 되기 때문이다. 랭킹 순서를 두 곳에서 뒤집은 셈이다.

1순위는 랭킹에 없던 항목이다. 저장소↔설치본 해시 대조 결과 드리프트가 scripts/harvest_images.py 단 1건인데 하필 그 파일이 랭킹 4위(BUG-1+BUG-2, 85.6점)가 겨냥한 파일이었다 — 저장소는 이미 수정본이고 demo assert 까지 있어 그 항목의 실작업량은 0 이다. 가드 없이 다음 배치를 돌리면 새 방어가 설치본에 없는 채 '막았다' 로 기록된다.

예산: 손대는 스크립트 6개(install/run_ledger/verify_facts/fetch/search/facts_db) + 신규 모듈 0 + assets 2 + 테스트 2 + 정본 문서 2. 제시된 '3~5 파일 + 신규 모듈 1~2' 대비 스크립트 1개 초과인데, 신규 모듈 예산을 쓰지 않았으므로 총량은 범위 안이다. run_ledger 하나에 5개 항목(2~6번)이 몰려 있어 실제 편집 지점은 6곳이 아니라 사실상 4곳이다. 그린이 흔들리면 절단선은 13번 SC-2 → 11번 COV-2 순서로 잘라라(둘 다 additive 라 되돌리기가 싸다).

상위 랭킹 중 EV-1(4위급 impact)·EV-2+EV-3·EV-5·SC-4 를 통째로 defer 한 이유는 하나다 — 넷이 전부 같은 픽스처 부채(_confirm() 헬퍼가 local 없는 evidence 와 4바이트 가짜 PNG 를 만든다)에 걸려 있고, 지금 착수하면 '그린 유지' 가 아니라 '그린 재획득' 이 된다. 그 부채는 한 번만 지불하는 게 총비용이 싸므로 다음 배치를 '픽스처 마이그레이션 + EV 계열' 로 묶어라. 마찬가지로 GS-4+OPS-6·GS-3·OPS-1 은 PEM 대장 마이그레이션 배치로 모아야 마이그레이션을 두 번 하지 않는다.

거절 10건 중 성격이 다른 셋을 짚어둔다. GS-7 의 채널 분리는 이 실행모델에서 원리적으로 재현 불가라 '막았다' 고 쓰는 것 자체가 순증 위험이므로 한계 명문화가 구현의 절반이다. FP-1 의 bozo 강등과 EV-8 의 --allow-change 는 방어처럼 보이지만 실제로는 게이트를 열거나 습관적 우회를 훈련시킨다. 그리고 '기존 조사폴더 호환' 을 이유로 한 예외 경로는 전부 거절했다 — 유일한 실존 조사폴더는 ledger 부재·facts.jsonl 오염 108행·manifest 구스키마로 이미 세 겹 레거시라 보호할 봉인 상태가 없고, 예외 경로는 곧 우회 경로다.
