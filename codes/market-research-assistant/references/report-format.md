# report-format — 고객용 report.md 양식 · 내부 audit 번들 양식

산출물은 **두 종류로 분리**한다: 고객용 `report.md`→`report.pdf`(GitHub 스타일)와 내부 `audit/` 번들. 고객용에는 폐기목록·실패URL·미확인의혹을 **넣지 않는다**. 검증 흔적은 전부 audit로 간다.

---

## 1. 고객용 report.md — 3중 구조 (섹션마다 반복)

각 주제 섹션은 아래 세 층을 순서대로 갖는다.

### ① 서술 본문
흐름 고정: **배경 → 메커니즘 → 수치 → 의의 → ⚠ 주의점**
- **수치는 반드시 `(Fxxx)` 태그**를 단다. 태그 없는 수치·비율·통화·날짜는 G3에서 무태그로 차단된다(verification-gates §G3).
- 태그가 가리키는 fact는 `status:"confirmed"`여야 한다. pending/disputed는 본문 단정에 쓰지 않는다(disputed는 "출처에 따라 X~Y로 갈린다"처럼 상충을 드러내 서술).
- ⚠ 주의점: 정의 차이·기준일·표본 한계 등 그 수치를 오해하지 않도록 하는 단서.

### ② 근거표
| 사실 | 수치 | 출처(링크) | 등급(4차원) | 증빙 |
|---|---|---|---|---|
| 요지 | value.raw (단위) | source_url | authority/independence/directness/recency = A~D | `_captures/Exxx.png` |
- 등급은 4차원을 모두 표기(예: `A/B/A/A`). 척도 정의는 verification-gates §4.
- 증빙 열은 **source_capture만**(reconstructed_excerpt는 넣지 않는다).
- 하나의 fact에 evidence가 여럿이면 독립 출처 수를 함께 표기(같은 보도자료 재전재는 1로 합산 — source_role).

### ③ source_capture + 캡션
- confirmed 핵심 수치의 캡처 이미지를 싣고, 캡션으로 **수치 ↔ 원문 위치**를 매핑("사업보고서 p.112 손익계산서 매출 행").
- 캡션은 캡처가 fact의 어느 값을 가리키는지 한 줄로 못 박는다.

---

## 2. 고객용 말미 (보고서 끝)

1. **한눈에 요약표** — 핵심 confirmed fact를 한 표로(주제·수치·기간·등급·F-ID).
2. **조사팀 인사이트** — 에이전트별 코멘트 + 팀리드 종합 코멘트. 각 문장에 **[사실]/[추론] 구분**과 근거 F-ID(agent-briefs §5와 동일 규약). 조사원 insights.md의 TF-ID는 팀리드가 F-ID로 치환해 싣는다.
3. **한계와 반론** — **개수 고정 없음. 근거가 있을 때만 쓴다.** 데이터의 한계(표본·정의·시점)와 상반 견해를 근거(F-ID/출처)와 함께. 채우기용 문장 금지.

### 고객용에서 제외 (절대 미포함)
- 폐기목록(discarded facts)
- 실패 URL·fetch 실패 사유코드
- 미확인 의혹(근거 없이 남은 단서)

이들은 전부 audit로 간다. 고객 PDF는 "확정된 것"만 보여준다.

---

## 3. 내부 audit/ 번들

`audit/` 아래에 검증 전 과정을 남긴다(재현·감사용).

```
audit/
  facts_all.md|.csv        # facts.jsonl 전수표 (confirmed 외 pending/disputed/superseded/discarded 포함)
  discarded.md             # 폐기목록 + 사유 (무출처/추정/딜규모혼동/fetch실패 등)
  failed_sources.md        # 실패 소스 URL + 사유코드(source-ladder §3)
  verify_log.md            # 검증 이력 (verify_events 전개: 누가·언제·reread·match/mismatch)
  raw_agent_output/        # 조사원 원자료 (_research/<agent>/ 복사; 무수정 보존)
  manifest.json            # source/capture/report/PDF SHA-256 (manifest.py)
```

- `discarded.md`·`failed_sources.md`는 고객용에서 빠진 것들의 **집합소**다. 폐기 사유를 명시해 "왜 안 썼는지"를 감사 가능하게 한다.
- `manifest.json`은 G3에서 고정하고 G5에서 재확인(파일 변경 시 G3 복귀 트리거).

---

## 4. 렌더 (style.html)

- `style.html`: GitHub markdown 스타일 + Malgun Gothic + A4 + 증빙박스 CSS.
- 파이프라인: `pandoc`(gfm, `--embed-resources`)로 자기완결 HTML → HeadlessChrome(`--print-to-pdf`, 절대경로, 한글경로 퍼센트 인코딩)로 **오프라인 렌더**(네트워크 접근 없음).
- 캡처 이미지는 `--embed-resources`로 HTML에 인라인 임베드되어 PDF에 포함된다(외부 참조 없음).

---

## 5. 무태그 방지 요약 (본문 작성자용)

본문에 숫자를 쓸 때:
- confirmed fact가 있으면 → `(Fxxx)` 태그.
- confirmed fact가 없으면 → 그 숫자를 **본문에 쓰지 않는다**(정성 서술로 대체하거나 조사 보강).
- 부록(근거표·요약표)의 F-ID는 "본문 사용"으로 계산되지 않는다(G3가 본문/부록을 분리 파싱). 즉 본문에서 실제로 태그를 달아야 한다.
