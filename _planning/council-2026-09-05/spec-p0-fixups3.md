# SPEC — P0 fixup 3차: 출고 판정을 영수증 신뢰에서 실검증 재계산으로 전환

REASONING: xhigh

## 배경 (필독)

`scratchpad/review-astra-rereview.md` 전문을 먼저 읽어라. 요지: 정상 진입점
(verify_and_record / render_and_record)은 올바르나, `gates._record_script_result` 직접
호출로 성공 영수증을 위조하면 `finalize_report` 가 그것을 신뢰해 "최종" 을 승인한다
(재현 코드·실행 결과 포함). 같은 프로세스에서는 어떤 기록 함수도 흉내낼 수 있으므로
**기록 함수를 더 잠그는 방식으로는 닫히지 않는다.**

설계 결정(변경 불가): 원 수정 제안서 §10.2 "출고 판정에 단일 검증 경로" 원칙대로,
**최종 판정이 영수증 존재가 아니라 현재 입력의 실제 검증 결과를 스스로 계산**하게 바꾼다.
영수증 원장은 이력·순서·드리프트 진단용으로 유지하되, 성공 영수증만으로는 어떤 최종
판정도 나지 않는다.

저장소: `F:/Claude/skills/market-deep-research/codes/market-deep-research/` (워킹트리 =
fixup 2차 반영본, 미커밋). 기존 스펙 제약(`spec-p0-fixes.md` §4) 유효.

## 수정 내용

### 1. finalize(=`manifest.py verify` CLI 포함) 가 실검증을 재실행
`manifest.finalize_report` / `manifest.py verify` 가 성공을 선언하기 전에 **스스로** 실행:
1. 정규 report.md 에 `verify_facts.verify()` 재실행 — **검사 전용 모드**(manifest 재봉인·
   영수증 기록 등 부작용 없이 판정만 돌려주는 플래그/경로를 추가하되 기존 구현 재사용,
   이중구현 금지). FAIL 이면 최종 판정 실패.
2. 기존 G5 검사(봉인 diff·PDF 내 F태그/링크/캡처 수 재검사 등 현행 검사 항목) 실행 —
   19바이트 가짜 PDF 는 여기서 걸린다.
3. 영수증 체인 검사는 유지하되 역할 축소: 순서·드리프트 진단과 감사 이력. 영수증이
   완벽해도 1·2 가 실패하면 실패, 영수증이 위조돼도 1·2 를 통과할 수 없으면 실패.
- 최종 판정 결과는 지금처럼 G5 자기기록(성공·실패 모두 이력 보존).
- 성능: verify 재실행 비용은 허용(출고는 1회성). 단 KERI 규모(대장 수백 건)에서 수 분을
  넘기지 않게 불필요한 중복 I/O 는 피한다.

### 2. `publication_state`/`status` 도 같은 원칙
G5 성공 영수증 존재만으로 "최종" 을 표시하지 않는다 — finalize 실행 결과(1·2 포함) 가
현재 상태와 일치할 때만. 최소 구현: status 는 "최종(판정시점)" + 판정 영수증의 결박 해시가
현재 파일과 일치하는지 표시. (전면 재검증을 status 마다 돌리라는 뜻이 아님 — 출고 판정
CLI 한 곳만 무겁게.)

### 3. 부정 회귀 테스트 (재리뷰 재현 그대로)
`review-astra-rereview.md` 의 재현 코드(A: `_record_script_result` 로 G3 성공 위조,
B: 정상 G3 후 렌더 생략 + 가짜 PDF + [4b] 위조)를 테스트로 추가:
`finalize_report()["ok"] == False` 와 publication_state ≠ "최종" 을 assert.
기존 테스트 123개 + 데모 3종은 계속 통과(정상 경로가 새 finalize 를 쓰도록 필요한
최소 수정 허용).

### 4. 문서 1곳
`references/verification-gates.md` G5 절에 신뢰 모델 2줄: "영수증은 이력·진단용이다.
최종 출고 판정은 finalize 가 현재 입력을 재검증해 스스로 계산하며, 같은 프로세스 권한의
원장·기록 위조로는 판정을 바꿀 수 없다."

## 검증 (완료 전 전부, out 파일에 기록)
```
cd F:/Claude/skills/market-deep-research/codes/market-deep-research
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
PYTHONIOENCODING=utf-8 python scripts/gates.py demo
PYTHONIOENCODING=utf-8 python scripts/verify_calculations.py --demo
PYTHONIOENCODING=utf-8 python scripts/verify_claims.py --demo
```
+ 재리뷰의 재현 코드 A·B 를 직접 실행해 이제 `final_ok: false` 가 됨을 stdout 으로 보여라.

## 완료 보고
out 파일에: 변경 파일 / 재현 A·B 차단 실행 결과 / 테스트 결과 / 요약 10줄.
질문하지 말고 가정을 적고 진행, 막히면 막힌 곳을 적고 종료. stdout 은 요약만. 커밋 금지.
