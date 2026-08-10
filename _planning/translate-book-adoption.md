# translate-book 하네싱 차용 분석 — 채택 1 · 기각 8 · 부활 조건 (v1.0)

> 작성 2026-08-10 · 출처 벤치마크: `deusyu/translate-book` — 책(PDF/DOCX/EPUB)을 chunk 분할해
> **1 chunk = 1 fresh 서브에이전트**로 병렬 번역하는 스킬. SKILL.md + scripts 8종
> (convert/glossary/chunk_context/meta/merge_meta/run_state/manifest/merge_and_build) 전문 정독.
> 분석 방법: 병렬 리더 4기(tb scripts / mdr references / mdr scripts / mdr \_planning·lessons)
> → 아키텍트 1기 후보 도출(C1~C9) → **후보별 회의적 검증자 9기**(기존 동등물 grep·게이트 충돌·YAGNI
> 기각 시도, file:line 결박). 총 14 에이전트.
> 동기: "장문 산출물 전달을 위한 fresh 에이전트 투입 하네싱"을 [3] 보고서 작성 단계에 이식할 수
> 있는지 검증.

## 한 줄 요약

translate-book의 골자(섹션 분할 fresh-writer 하네스)는 **mdr 자체 채택 원칙("실측 약점 표에 없는
항목은 원칙적으로 채택하지 않는다", gajae-code-adoption.md:23)에 걸려 전량 기각** — 유일한 생존자는
merge_meta.py의 **content-hash 멱등 join** 패턴이며, 독립 항목이 아니라 gajae-code R3·R4 스펙 제약
2건으로 흡수했다(v1.3). 기각된 8후보의 설계는 부활 조건과 함께 본 문서 §4에 보존한다.

## 1. translate-book 하네스 요약 (참조용)

"공유 상태는 해시로 버전링, LLM 판단은 열거된 선택지로 제약, 모든 쓰기는 원자적, 모든 병합은
게이트 통과 후"가 관철된 장문 멀티에이전트 하네스의 완성형 참고 구현.

| 장치 | 역할 | 핵심 불변식 |
|---|---|---|
| `glossary.json` + print-terms-for-chunk | fresh 컨텍스트 간 공유 정본 상태(용어집)를 chunk별 표로 선별 주입 | 로컬 히트 + 전역 top-N 이원 선별(max 50, 로컬 슬롯 보호) · surface form은 정확히 1 term 소속 |
| `chunk_context.py` | 이웃 chunk 꼬리/머리 300자 read-only 발췌로 경계 문맥 연결 | 빈 이웃 블록은 프롬프트에서 생략 · "번역 대상 아님" 라벨 명시 |
| `meta.py` + `output_chunk*.meta.json` | 워커 관찰(신규 개체·alias·충돌)의 유일한 상향 채널 | 닫힌 스키마(미지 키 거부) · evidence ≤200자 · **chunk_id는 파일명에서만 유도**(payload에 있으면 환각 구멍으로 거부) |
| `merge_meta.py` | meta→glossary 병합: 만장일치는 auto_apply, 나머지는 열거형 choice의 decisions_needed | **content-hash 멱등**(applied_meta_hashes) · **전부-아니면-전무 apply**(실패 시 hash 미기록→결정 보존) · 불량 meta는 quarantine 비차단 |
| `run_state.py` | 선택적 재실행 planner: 원문·출력·**"그 chunk에 주입된 term 부분집합"** 해시로 stale 판정 | 전체 glossary가 아니라 주입 부분집합 해시 비교 → 용어 1건 수정 시 영향 chunk만 재번역 |
| `manifest.py` + `source_fingerprint.json` | 병합 전 전건 검사(소스 존재·해시 일치·비공백·UTF-8) + 소스 바이트 지문으로 캐시 오염 차단 | 다른 원본 바이트의 temp 재사용은 즉시 중단 |
| `merge_and_build.py` | 병합 게이트 + 원본 대비 이미지 구조 diff + 수리 지시문 일괄 출력 | 실패 chunk 전건의 수리 지시를 한 번에 출력 → 재파견 1회로 다건 수리 |

## 2. 판정 결과 (9후보)

| ID | 후보 | 판정 | 핵심 근거 |
|---|---|---|---|
| C1 | 1 부(部) = 1 fresh writer 하네스 | **기각** | 실측 근거 0건 + R7a HANDOFF가 선행 해법 + "종합=메인 세션" 설계 역행(SKILL.md:164) + 비수치 날조 방어([2] 수행 리드의 직접 작성)를 내줌 |
| C2 | fact→섹션 라우팅(section-map.json) | 기각 | C1 전제 부재 · [미사용]/축커버리지 검사 기존재(verify_facts.py:378-380, :555-560) |
| C3 | 이웃 섹션 read-only 발췌 주입 | 기각 | C1 전제 부재 · 부 간 경계 규칙(report-format.md:22-25)은 단일 작성자가 집행 중 |
| C4 | canonical 표기 사전 + 표기 lint | 기각 | 섹션 분할이 없으면 드리프트 없음 · 실해 부분은 N4(canonical name 규칙 1줄)가 더 싸게 커버(gajae-code-adoption.md:179) |
| C5 | 섹션 stale 플래너(run_state 이식) | 기각 | 본문 (Fxxx) 태그 자체가 영속 의존성 지도(grep 1줄) · fact stale은 R2b 기계획 · STATE.json 삭제 판례와 동류(:241) |
| C6 | 섹션 병합 스크립트 + 병합 게이트 | 기각 | check_toc([목차이탈]/[빈챕터]/[축누락])가 이미 전건 차단 · gates summary 본문 미저장이라 "섹션 계보" 편익 자체가 미성립 |
| C7 | verify_facts 섹션 린트 모드 | 기각 | verify()는 라이브러리 호출 시 영수증 미기록(CLI \_\_main\_\_ 전용) — 부분 초안 린트는 **코드 0줄**(verify() 호출 + 접두어 필터)로 이미 가능 |
| C8 | writer meta 피드백 채널 | 기각 | gap 신고는 `## EXPAND` + [E] 루프가 동등물 · used_fact_ids 자기신고 정본화는 "자기신고 불신" 원칙(:13)과 정면 충돌 |
| C9 | 워커 EVIDENCE 파일 반환 + **멱등 join** + quarantine | **채택(수정)** | 4구성 중 3.5개는 R9a·R4·facts_db 기구현과 중복 — 순수 신규분 2건만 스펙 제약으로 흡수(§3) |

기각 공통 뿌리: C1~C8은 상호 의존 묶음이고, 뿌리인 C1이 (a) 실측 통증 기록 0건, (b) 기존 계획
(R7a 세션 재개·R6b 분할 재파견)의 선행, (c) 의도된 설계 결정(재검증·종합=메인 세션)과의 충돌로
기각되면서 연쇄 소멸. **판정은 "패턴이 나쁘다"가 아니라 "mdr의 현 통증이 아니다"이다.**

## 3. 채택분 — gajae-code-adoption.md v1.3에 반영 완료

독립 워크스트림 없이 기존 T-DAG 태스크의 스펙 제약으로 흡수(검증자 권고안 그대로). **스펙
본문은 `gajae-code-adoption.md`가 유일 정본** — R4(→T6)에 G1 join 멱등·전부-아니면-전무 제약
추가, R3(→T4)에 그 멱등을 전제조건으로 결박. 출처 패턴: translate-book `merge_meta.py`의
content-hash 멱등 + 사전 전건검증 트랜잭션.

## 4. 부수 발견 — APPENDIX 마커 중복 우회 (수리 완료)

`split_body_appendix`의 첫 마커 절단 특성상, 본문 앞쪽의 중복(실수·위조) 마커가 그 뒤 본문
전체를 결박 검사에서 면제시키는 우회 → `[부록마커중복]` FAIL 로 수리(verify_facts.py, 회귀:
`duplicate_appendix_marker_blocked`). 잔여 천장: 마커가 1개여도 문서 최상단에 있으면 body가
비어 무태그 검사가 통째로 침묵한다(별개 불변식 "본문 공백 FAIL" 필요 — 미착수).

## 5. 부활 조건 + 부활 시 설계 재료

**트리거**: 실전 조사에서 [3] 보고서 작성 단계의 컨텍스트 초과·후반부 품질저하·재작성 범위 특정
비용이 **audit 저널에 실측 기록**되면, R6b(분할 재파견)의 연장으로 C1 묶음을 재심사한다. 그 전
선행 해법은 R7a HANDOFF(게이트 경계 세션 재개)다.

부활 시 검증자들이 남긴 올바른 형태(요지):

- writer 브리프는 R9a 계약(파일 스필 + 경로·sha 반환)을 그대로 따른다. 신규 반환 형식 발명 금지.
- gap 신고(missing_facts)는 새 meta 파일이 아니라 **기존 4마커에 블록 1개 추가**로 흡수, R4
  parse_markers 검증 범위에 편입.
- used_fact_ids는 자기신고 필드로 만들지 않는다 — 병합된 본문에서 verify_facts가 기계 추출(정본 유지).
- 섹션 md는 `_research/sections/`에 착지(manifest TRACKED 밖 — 봉인 무충돌)하고 **G3 전에
  report.md로 병합**해 단일파일 전제(verify_facts·manifest TRACKED·render_pdf)를 건드리지 않는다.
- 섹션 린트는 verify() 라이브러리 직접 호출 + 실패 접두어 필터([무태그]/[값불일치])로 구현 —
  CLI 경유 금지(G3 영수증 오염 방지). G3 영수증은 병합본 전량 검증에서만.
- 섹션 stale 판정이 필요해지면 상태 파일 신설이 아니라 report.md 헤딩+TAG에서 질의 시점에
  파생하는 read-only 헬퍼(~20줄)로.
- 표기 통일은 N4(canonical name 마커 규칙) 우선, 사전(style-glossary) 신설은 그 후 실측 드리프트
  발생 시.
- [무태그] FAIL은 단위 결합 수치만 잡는다(METRIC_NUM, verify_facts.py:54-61) — writer의 연도
  단독·개수·정성 날조는 못 잡으므로, writer 도입 시 비수치 날조 방어(예: R6a 크리틱 범위 확장)를
  함께 설계해야 한다.
- 전역 종합 성격의 부(1부 KPI·10부 인사이트)는 위임하지 않고 팀리드 직접 작성으로 남긴다.

## 6. 재제안 금지 (이번 검증으로 확정)

§2 표의 기각 근거 외 추가 확정 1건: **merge_meta식 트랜잭션 결정 엔진 전체 이식 금지** —
mdr의 결정 주체는 팀리드 수동 판단으로 충분하다. (사이드카 상태 파일·CLI 서브셋 스위치·
used_fact_ids 자기신고의 금지 근거는 §2 C2/C5/C7/C8 행이 정본)
