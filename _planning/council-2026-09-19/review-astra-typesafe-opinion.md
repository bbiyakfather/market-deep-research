# TypeSafe 접목 의견 2건 적대적 리뷰

## 1. 판정

**의견 2: 부분 타당 — 58/100점. 즉시 도입을 보류할 이유는 있지만, 원문 일치의 기계적 보장·접목 공간의 부재·기존 영수증만으로 가능한 병목 실측을 과장했다.**

점수는 의견의 사실 정확성과 논증에 대한 리뷰어 평가이며 모델 성능 점수가 아니다. 최종 권고는 **실측만**이다. 현재 API를 넣거나 게이트를 바꿀 근거도, 측정 없이 “병목이 아니면 끝”이라고 결론 낼 근거도 부족하다.

### 검토 범위와 전제

- 기준: 2026-09-19 저장소 HEAD `a07a3c73969697887c29efa7e486b6d80aa226cf`. 지정된 두 의견, SKILL·참조문서 5개·스크립트 5개를 대조하고, 호출 경로 확인을 위해 `assets/facts-schema.json`, `scripts/skill_paths.py`, `scripts/manifest.py`도 읽었다.
- 아래 `SKILL.md`, `references/...`, `scripts/...`의 기준 디렉터리는 `F:/Claude/skills/market-deep-research/codes/market-deep-research/`다. `파일:줄`은 검토 당시 실제 줄 번호다.
- 의견 1은 `C:/Users/eicic.AIDEN-DESKTOP/AppData/Local/Temp/claude/F--Claude-claude-sync/35fe124d-3ca7-4696-ad63-57730cf47986/scratchpad/typesafe-opinion-for-mdr.md`, 의견 2는 `C:/Users/eicic.AIDEN-DESKTOP/AppData/Local/Temp/claude/F--Claude-skills-market-deep-research/d0ecd565-6078-4a7f-948a-44f8689ac9e3/scratchpad/mdr-opinion-on-typesafe.md`다. 표의 의견 줄 번호는 이 파일들을 뜻한다.
- TypeSafe 사양·가격·한국어 성능 경고·데이터 보존 정책은 의견 1의 전제를 그대로 사용했다. 웹·외부 API·TypeSafe 호출·패키지 설치를 하지 않았으므로 제품의 실제 성능, 지연, 결정론, 이미지 입력 지원은 **미검증**이다.
- 정적 독해와 별도로 기존 Python 함수에 합성 입력을 넣어 9가지 경계 동작을 확인했다. `python -B`와 자동 정리되는 임시폴더를 사용했으며 저장소 코드·문서는 수정하지 않았다. 이 보고서가 유일한 의도된 영구 산출물이다.
- 접근 가능한 저장소에서 실제 조사 산출물인 `audit/gates.jsonl`과 `audit/verification-economics.md`를 발견하지 못했다. 따라서 아래 시간·비용 평가는 **계측 설계의 타당성 검토**이며 실제 조사 병목 실측 결과가 아니다. 접근 거부된 pytest 캐시는 조사 원장 탐색 근거에 포함하지 않았다.

## 2. 발견 표

심각도는 의견을 설계 판단에 그대로 사용할 때의 영향이다. 치명은 증거 검증 보장에 관한 핵심 오판, 중대는 도입·측정·신뢰 경계 판단을 바꿀 오류, 경미는 범위 한정이나 근거 보강이 필요한 주장이다.

| ID | 심각도 | 의견의 어느 문장 | 반증 근거(`파일:줄`) | 고쳐 쓸 문장 |
|---|---|---|---|---|
| A01 | 치명 | 의견 2:18 “인용문이 원문에 있는지는 … text_quote verbatim 검사가 기계적으로 막는다.” | `scripts/verify_facts.py:657`은 verbatim의 **존재**만 검사한다. `scripts/verify_facts.py:662`는 선택적 local 파일의 바이트 해시를 대조하며, 본문을 추출해 인용문 포함 여부를 검사하지 않는다. `scripts/verify_facts.py:709`의 재열람 대조는 evidence.sha256·verbatim 자체 해시·local 파일 해시의 집합과 이벤트 해시가 겹치는지 보는 것뿐이고 불일치도 WARN이다(`:720`). `scripts/facts_db.py:275`도 필수 여부만 검사한다. 실제 원문에 없는 인용문으로 이 검사에서 FAIL 0/WARN 0을 재현했다. | “verbatim 누락과 일부 파일 무결성은 기계 검사하지만, 인용문이 원문에 존재하는지는 팀리드의 실제 원문 대조에 의존한다. 출처 포함 여부와 의미 지원 여부 모두 별도의 검토 과제다.” |
| A02 | 중대 | 의견 2:20–22 “서술 필드를 요구한다. 생성을 안 하는 모델은 못 채운다 … 들어갈 자리는 팀리드 읽기 전 … 뿐.” | 필드 필수는 맞지만 `references/claim-review.md:31`은 빈 배열·빈 문자열을 허용한다. `scripts/verify_claims.py:35`, `:37`이 이를 구현하며 supported 행의 unsupported_terms는 오히려 비어야 한다(`:117`). sentence_text는 복사하고 해시·ID는 코드로 채울 수 있다. 나머지 정책상 의미 판단의 책임과 모델의 출력 형식은 다른 문제다. | “판정 모델 단독으로 충분한 의미 검토를 보장할 수는 없다. 다만 필드 형태가 접목을 막지는 않으며, 분류·지원 수준 제안·후보 표현 선택에 쓰고 실제 한계 서술과 최종 검토는 팀리드가 맡을 수 있다.” |
| A03 | 경미 | 의견 2:21 “[2]는 by='lead'+reread_sha256을 요구하고 verifier 단독 confirm을 금지”의 강제 수준 | 이 문장 자체는 데이터 규칙으로 **맞다**. `scripts/facts_db.py:208`, `:212`, `:451`과 `scripts/gates.py:235`에서 강제한다. 다만 `[2]`가 검사하는 대상은 confirmed 집합(`gates.py:242`)이며, by는 호출자 인증이 아닌 문자열이다. 해시의 형식은 강제해도 재열람 수행·원문 일치·시간적 최신성 전체를 증명하지 않는다(`verify_facts.py:706`). | “verifier로만 표시된 기록은 confirm할 수 없다. lead 재열람 이벤트와 64hex 해시는 필요조건이며, 실제 팀리드가 원문을 읽었다는 증명 또는 모든 수집 후보의 검토 완료 증명은 아니다.” |
| A04 | 중대 | 의견 2:11 “RAG passage 분류: 해당 단계 없음 … 맞는 자리가 없다.” | 별도 RAG 모듈 부재와 분류 수요 부재를 혼동했다. 워커는 원문에서 evidence를 구조화한다(`references/agent-briefs.md:12`). EXPAND를 축별 집계·dedup하고 후속 워커를 고른다(`SKILL.md:73`). 미분류 축 재분류도 존재한다(`references/agent-briefs.md:48`). `scripts/join_workers.py:161`, `:185`는 문자열·URL 지문에 의한 중복 후보만 찾는다. | “전용 RAG 단계는 없지만 검색·수집 후보의 관련성, 축 분류, EXPAND 의미 중복과 조사 순서에는 사전 판정 공간이 있다. 그 이득은 아직 검증하지 않았다.” |
| A05 | 경미 | 의견 2:12 “관련도 재순위 ≠ 출처 권위 판정”을 접목 여지 축소의 근거로 사용 | 구분 자체는 맞다. 그러나 4차원 등급은 권위·독립성·직접성·최신성이다(`references/verification-gates.md:3`); 승인 조사질문과의 관련성은 별도다(`references/research-plan.md:19`). 검색 후보 여러 개를 처리하고 검색 완전성도 보장하지 않는다(`references/source-ladder.md:4`, `:7`). | “관련도 점수로 권위 등급을 대체할 수는 없다. 같은 출처 제약을 충족하는 후보 안에서 조사질문 관련성과 누락 축 기여도를 기준으로 읽을 순서를 제안하는 것은 별개의 후보 기능이다.” |
| A06 | 중대 | 의견 2:13,15 “Self-consistency … 이미 규칙으로 구현”, “위험도별 임계값 원칙 … verification-economics.md에 이미” | high-risk의 추가 요건은 실제 코드다(`scripts/verify_facts.py:559`). 그러나 confidence 교정·분포·임계값에 따른 분기는 이 코드에 없다. 위험 태그 누락은 WARN뿐이다(`:555`). economics 파일은 기록 지침(`SKILL.md:86`, `references/verification-gates.md:42`)과 범용 경로 함수의 예시(`scripts/skill_paths.py:95`)로만 등장한다. 지정 코드와 참조문서에서 생성·필수 검증·오류비용 계산·확률 임계값 구현은 찾지 못했다. | “위험도별 검증 깊이 원칙은 high/normal의 규칙으로 일부 구현됐다. verification-economics는 수동 감사 기록 지침이며, confidence 기반 기권·사람 검토 임계값이 구현됐다는 뜻은 아니다.” |
| A07 | 경미 | 의견 2:23 “사실은 수십~수백 건이라 판정 토큰 비용은 애초에 작다. 비용은 수집·캡처와 팀리드 주의력에 있다.” | 의견에 실제 N건·토큰·소요시간 표본이 없다. 조사계획의 3회/12명은 확장 깊이·워커 수 상한이지 fact나 입력 토큰 상한이 아니다(`references/research-plan.md:23`). 판정 입력은 짧은 fact뿐 아니라 원문·조건·표 주변 문맥이다(`references/claim-review.md:3`, `:10`). 영수증에도 입력 토큰·주의 시간 필드는 없다(`scripts/gates.py:450`, `:568`). | “비용 중심이 수집·캡처·주의력이라는 가설은 합리적이지만 미측정이다. 실제 문맥 토큰, 배치 재사용, 재시도, 재검토 시간과 누락 오류비용까지 합쳐 비교해야 한다.” |
| A08 | 중대 | 의견 2:30 “기존 워커(codex luna)로도 가능 → TypeSafe 도입 이유는 아님.” | 문서상 조사 워커는 sonnet, 기계적 후속 작업은 haiku다(`SKILL.md:43`, `references/agent-briefs.md:3`). luna로 같은 분류가 가능하다는 추론과 정확도·교정·응답 일관성·비용의 동등성은 별개다. 제공된 코드·계약에 luna 판정용 고정 프롬프트·비교 측정은 없다. 개발에 luna를 썼다는 별도 기록은 조사 판정기의 동등성 증거가 아니다. | “기존 워커도 비교 기준에 반드시 넣는다. 기능 수행 가능성만으로 동등하거나 더 싸다고 결론 내릴 수 없고, TypeSafe의 우위도 현재 입증되지 않았다.” |
| A09 | 중대 | 의견 2:34 “새 계측 없이 … gates.jsonl 영수증 시각 간격([2]→G3)으로.” | ts는 **있다**: 수동 영수증 `scripts/gates.py:453`, 스크립트 영수증 `:571`. 그러나 `[2]` 영수증은 재열람 후 선언(`SKILL.md:80`, `:83`)이다. 그 뒤에는 반박·캡처·보고서 작성이 온다(`SKILL.md:85`, `:90`, `:93`). 따라서 이 차이는 [2] 재열람 소요시간을 포함하지 않으며 다른 작업·대기를 섞는다. ts는 시간대 없는 초 단위 시각이다(`scripts/gates.py:63`). | “기존 ts는 완료 시점 사이 경과시간의 탐색 자료다. 재열람·판정의 병목을 재려면 작업 시작/종료, 능동 작업시간, 건수·토큰·재시도를 별도 표본 기록해야 한다.” |
| A10 | 경미 | 의견 2:25 “유료 API 무의존 코어 원칙 … 과 부딪힌다.” | `SKILL.md:7`은 유료 API 무의존 **수집 스택 코어**다. 선택 계층 없이 기존 기능이 실패하도록 만들면 충돌하지만 선택적 보조 판정이 곧 코어 원칙 위반은 아니다. `references/source-ladder.md:19`도 외부 도구의 기회적 사용과 자체 스택 유지를 구분한다. 의견 2:26의 SOFT 제안은 이 범위에서는 타당하다. | “유료 판정 API를 필수 의존성으로 만들지 않는다. 선택 계층의 추가는 원칙과 양립할 수 있지만 별도로 비용·기밀·실패 시 동작을 검증해야 한다.” |
| A11 | 중대 | 의견 2:25–26 “code_sha256으로 코드를 결박하는 재현성 … 모델 버전 audit 기록.” | `scripts/gates.py:155`의 code_sha256 대상은 scripts/*.py와 facts-schema.json이다. 모델 가중치·요청·응답·문서 프롬프트·추론 설정을 묶지 않는다. 기존 의미 판정도 검토자 판단이다(`scripts/verify_claims.py:5`). 더구나 일반 audit 파일은 일괄 봉인하지 않는다(`scripts/manifest.py:33`, `references/verification-gates.md:139`). 버전 이름을 audit에 적는 것만으로 입력 결박이나 재실행 동일성이 생기지 않는다. | “현재 보장은 파일·코드 출처 추적과 변경 탐지다. 확률 모델에는 원입력·전처리·프롬프트·선택지·설정·버전·원응답을 보존하고 해당 판정 입력 해시를 결박해야 한다. 저장 응답을 다시 적용하는 재현성과 모델을 다시 호출하는 재현성은 구분한다.” |
| A12 | 중대 | 의견 1:35 및 의견 2:33 “병목 아니면 종료”, 의견 2:28 “실제로 빈 곳 … 한 군데” | 자동 전건성은 태그 문장에 한정된다(`scripts/verify_claims.py:24`); 독립성 계산도 입력된 역할·그룹을 신뢰한다(`scripts/verify_facts.py:473`); EXPAND 지문은 의미 동등성을 판정하지 않는다(`scripts/join_workers.py:7`). 즉 소요시간 외에 검토 누락·허위 독립성·중복 조사라는 품질·비용 기회가 여러 곳 있다. | “성능 병목과 품질 누락을 함께 측정한다. 병목이 없어도 누락 탐지의 품질 이득이 총비용을 넘으면 보조 판정 검토를 계속할 수 있다.” |
| A13 | 중대 | 공통 누락: 의견 2:20–22의 claim-review, :25–26의 영수증 설명에 근거 최신성의 실제 경계가 빠짐 | `scripts/verify_claims.py:62`는 evidence_revision을 **facts만**의 confirmed_digest로 계산한다. `scripts/facts_db.py:483`은 evidence 내용·해시·연결 ID·claim-graph를 포함하지 않는다. 같은 F/E-ID에서 evidence.verbatim만 바꾸면 기존 claim-review가 그대로 PASS하는 사례를 재현했다. 다만 G3 영수증은 evidence.jsonl 전체 해시를 refs에 묶는다(`scripts/gates.py:576`): **옛 G3 영수증의 변경 탐지까지 뚫렸다는 주장은 아니다.** | “근거 파일 변경은 기존 G3 영수증을 낡게 만들지만, G3를 다시 실행할 때 오래된 의미 판정의 재사용을 claim-review의 evidence_revision만으로 막지는 못한다. 보조 모델의 캐시·판정 결박에는 실제 증거 바이트와 연결 관계를 포함해야 한다.” |
| A14 | 경미 | 의견 2:11 “G1은 스키마 검증 + 무출처 즉시 discarded”의 코드·운영 구분 누락 | 무출처 폐기는 문서상 팀리드 처리 지침이다(`SKILL.md:77`, `references/verification-gates.md:22`). `scripts/join_workers.py:107`은 워커 fact를 pending으로 요구하고, `:194`는 등재를 팀리드에게 맡긴다. 실제로 evidence=[]인 pending fact를 반환한 raw도 join 검사 verdict=ok, status=pending이었다. `scripts/facts_db.py:212`의 무출처 차단은 confirmed 상태에 적용된다. | “G1은 스키마 검증 후 팀리드가 무출처 항목을 discarded로 처리하는 단계다. join 코드가 무출처를 자동 폐기한다고 해석해서는 안 된다.” |

### 반박 대상이 아닌 부분과 한정

- **[2] 대체 불가라는 정책 결론은 타당하다.** 팀리드 전건 재열람은 명시적 원칙이다(`SKILL.md:21`). verifier 단독 confirm과 해시 없는 lead 이벤트도 실제 거부된다. 이를 “아무 강제도 없다”로 뒤집는 것은 잘못이다. A01·A03은 그 강제가 원문 진실성이나 호출자 인증까지 확장되지 않는다는 지적이다.
- **5가지 support와 검토 대장 필수 필드는 실제다.** 다만 observed/derived의 supported 강제와 supported+unsupported_terms의 모순 차단이 핵심이며(`scripts/verify_claims.py:114`), “항상 새로운 설명문을 생성해야 한다”는 요건은 아니다. 새로운 문장 검토 문제는 v4 FAIL/v3 WARN이므로 버전도 밝혀야 한다(`:124`, `references/claim-review.md:52`).
- **숫자도 태그도 없는 사실 문장 구멍은 맞다.** `tagged_sentences()`가 태그를 기준으로만 수집한다(`scripts/verify_claims.py:24`). 숫자 검사도 특정 수치·단위 패턴을 사용한다(`scripts/verify_facts.py:67`, `:84`). 이 공백을 찾는 분류기는 가능한 후보지만 정확도 향상은 아직 가설이다.
- **공개 출처만 보내면 안전하다는 의견 1의 단정에 대한 의견 2의 반론은 타당하다.** 조사 문장·질문·후보 조합이 의뢰 범위를 노출할 수 있다는 추론이다. 실제 제약은 조사계획의 인용·기밀 조건으로 확인해야 한다(`references/research-plan.md:25`). 검토 범위의 문서만으로 조직 전체의 “기본 대외비” 정책이나 벤더 보존 조건을 추가 확정하지는 않았다.
- **한국어 검증 필요는 유지하되 “모델의 최약점”은 과장이다.** 의견 1이 전달한 일반적 CJK 경고는 한국어 원문·단위·표·조건 판정의 실제 오류율을 알려주지 않는다. 어려운 한국어 추론을 전면 위임하지 말아야 한다는 경계와, 쉬운 문장 유형 분류까지 이득이 없다는 결론은 구분해야 한다.

### 실행으로 확인한 반례

아래는 기존 함수의 동작을 분리해 확인한 결과다. 실제 고객 보고서를 출고했거나 전체 G3/G5가 통과했다는 뜻은 아니다. 모든 값은 합성 사례이며 네트워크를 사용하지 않았다.

| 검사 | 구성 | 실제 결과 | 의미 |
|---|---|---|---|
| 원문에 없는 인용문 | local에는 “project was rejected”, verbatim에는 “project was approved”; evidence.sha256와 lead 해시는 실제 local의 SHA-256 | validate_fact·validate_evidence 성공, check_evidence_chain FAIL 0/WARN 0 | 해시가 일치해도 인용문 포함 여부는 검사하지 않음 |
| verifier 단독 | confirmed의 유일한 이벤트를 by=verifier로 변경 | validate_fact 거부 | 역할 문자열 조건은 실제 강제 |
| lead 해시 누락 | by=lead/action=reread, reread_sha256 생략 | validate_fact 거부 | 64hex 해시 필수는 실제 강제 |
| 무관한 lead 해시 | 형식은 유효하지만 원문·verbatim 어느 것과도 다른 해시 | validate_fact 성공, 증거체인 FAIL 0/WARN 1 | 해시 형식·내용 결박의 강제 수준이 다름 |
| evidence 변경 후 옛 검토 재사용 | F/E-ID·fact·문장·검토 행은 유지하고 evidence.verbatim만 반대로 변경 | verify_claims(check_only=True) 변경 전후 ok=True, evidence_revision 동일 | 의미 판정 캐시 키에 실제 evidence 내용이 없음 |
| 무태그 비수치 사실 추가 | 검토된 태그 문장 뒤에 사실형 무태그 문장 추가 | verify_claims ok=True, 대상 문장 수 1 | 자동 전건성 누락 |
| 가정으로 표시한 partial | 동일 문장을 claim_type=hypothesis/support=partial, required_qualification=""로 기록 | verify_claims ok=True | 실제 조건 명시와 claim_type 적합성은 검토자 신뢰 경계 |
| 동일 인용, 다른 그룹·URL·해시 | 같은 verbatim을 source_role=원출처로 각각 신고하고 그룹·URL·sha를 다르게 지정 | _independent_observers=2 | 동일 내용 여부나 전재 관계를 의미적으로 확인하지 않음 |
| 출처 없는 워커 반환 | v4 pending fact에 evidence=[]와 정상 반환 마커를 제공 | validate_worker verdict=ok, status=pending | G1의 즉시 discarded는 자동 상태 전환이 아닌 운영 지침 |

핵심 두 반례를 재실행하려면 저장소 루트에서 아래 Python을 `python -B -`의 표준입력으로 실행한다. 임시폴더의 합성 파일만 만들고 정리하며, 기존 검증 함수에 손대지 않는다. 첫 assert 묶음은 A01, 마지막 assert는 A13을 검증한다.

```python
import hashlib, json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path("codes/market-deep-research/scripts").resolve()))
import facts_db, gates, verify_claims, verify_facts
from skill_paths import WorkPaths

def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")

with tempfile.TemporaryDirectory(prefix="mdr-typesafe-review-") as tmp:
    root = Path(tmp).resolve()
    root.relative_to(Path(tempfile.gettempdir()).resolve())
    wp = WorkPaths(root)
    source = root / "source.txt"
    source.write_text("The project was rejected.", encoding="utf-8")
    sha = gates.sha256_file(source)
    quote = "The project was approved."
    context = {"metric": "status", "entity": "Example", "geography": "KR", "period": "2026"}
    fact = {
        "schema_version": 4, "claim_type": "observed", "id": "F001",
        "claim_key": facts_db.make_claim_key(context), "claim": quote,
        "context": context, "value": {"raw": "approved", "unit": "status"},
        "grade": {k: "A" for k in ("authority", "independence", "directness", "recency")},
        "risk": "normal", "status": "confirmed", "evidence_ids": ["E001"],
        "verify_events": [{"by": "lead", "action": "reread", "at": "2026-09-19T18:00:00",
                           "note": "", "reread_sha256": sha}],
    }
    evidence = {
        "schema_version": 4, "id": "E001", "fact_id": "F001", "type": "text_quote",
        "source_url": "https://example.test/source", "sha256": sha,
        "accessed_at": "2026-09-19T18:00:00", "local": "source.txt", "verbatim": quote,
    }
    facts_db.validate_fact(fact)
    facts_db.validate_evidence(evidence, work=wp)
    assert quote not in source.read_text(encoding="utf-8")
    assert verify_facts.check_evidence_chain({"F001": fact}, {"E001": evidence}, wp, {"F001"}) == ([], [])
    write_rows(wp.facts, [fact])
    write_rows(wp.evidence, [evidence])
    sentence = "The project was approved (F001)."
    wp.report_md.write_text(sentence, encoding="utf-8")
    row = {
        "sentence_id": "S001", "claim_type": "observed", "fact_ids": ["F001"],
        "evidence_ids": ["E001"], "support": "supported", "unsupported_terms": [],
        "required_qualification": "", "sentence_text": sentence,
        "reviewed_text_sha256": hashlib.sha256(sentence.encode()).hexdigest(),
        "evidence_revision": facts_db.confirmed_digest([fact]),
    }
    write_rows(wp.audit / "claim-review.jsonl", [row])
    before = verify_claims.verify(wp.report_md, wp, check_only=True)
    evidence["verbatim"] = "The project was rejected."
    write_rows(wp.evidence, [evidence])
    after = verify_claims.verify(wp.report_md, wp, check_only=True)
    assert before["ok"] and after["ok"]
    assert before["evidence_revision"] == after["evidence_revision"]
print("A01 and A13 reproduced; no source code changed")
```

## 3. 놓친 기회·놓친 위험

### 놓친 기회: 판정 공간은 하나가 아니다

아래는 코드가 비워 둔 의미 판단의 **후보**다. TypeSafe가 기존 워커보다 낫다는 실증 결과가 아니며, 현재 필수 재열람을 생략할 명분도 아니다.

| 자리 | 왜 도움이 될 수 있는가 | 실제 접점과 한계 |
|---|---|---|
| 무태그 사실 문장 탐지 | “관측 사실/가정/권고/구조 문장” 분류로 숫자 없는 사실 후보를 찾아 수동 검토 목록에 올릴 수 있다. 확률은 검토 순서 제안에 쓸 수 있다. | `scripts/verify_claims.py:24`. 탐지하지 못한 문장도 정답으로 간주하면 안 된다. 놓친 사실의 재현율, 추가 오탐 검토시간을 함께 측정한다. 첫 비교 대상으로 가장 작고 명확하다. |
| 전재·독립 관찰그룹 제안 | 제목·문장 일부가 바뀐 보도자료 복제는 URL·해시가 달라져도 같은 관찰일 수 있다. pair 분류로 팀리드가 관계를 확인할 후보를 제시할 수 있다. | `scripts/verify_facts.py:478`, `:482`는 역할·그룹·URL·해시를 입력으로 쓴다. 최종 그룹의 사실 적합성은 사람이 확인한다(`references/verification-gates.md:39`). “독립일 확률”로 관찰그룹 수를 자동 늘려서는 안 된다. |
| 워커 raw·EXPAND 의미 중복 및 축 분류 | 이름·표현·기간 표기가 달라 정확 지문에 걸리지 않는 중복을 찾아 재조사 비용을 줄일 수 있다. 미분류 축을 승인 축에 매핑할 후보도 만들 수 있다. | `scripts/join_workers.py:28`, `:161`, `:185`, `references/agent-briefs.md:48`. 비슷해도 정의·기간·범위가 다른 fact를 자동 병합하지 않는다. 드롭·수렴 판정은 팀리드 책임으로 남기고 후보를 보존한다. |
| 수집·후속 워커 우선순위 | source-ladder가 확보한 검색 후보에서 승인 질문에 답할 가능성을 순위화하면 읽기·fetch·팬아웃 순서를 개선할 수 있다. | `references/source-ladder.md:3`, `SKILL.md:73`. 출처 등급과 관련성은 독립 축이다. direct 우선 fetch·보안 경계는 유지한다(`references/source-ladder.md:28`, `:52`). 낮은 점수를 근거로 소수 반론을 삭제하지 않는다. |
| capture_review 전의 실패 의심 선별 | 로그인·차단 문구와 문맥 누락 후보를 먼저 보여주면 불량 캡처의 육안 확인 순서를 개선할 수 있다. 기존 단색 비율은 의미를 판정하지 못한다. | `scripts/verify_facts.py:607`, `:618`, `:624`. **의견 1에는 이미지 입력 지원이 없다.** 따라서 이미지 직접 판정은 미검증이며, OCR/DOM 텍스트가 있다면 대리 입력 실험 정도만 후보로 삼는다. 텍스트 판정으로 claim_visible/context_visible 또는 최종 accept를 채우지 않는다. |

Noul의 OX를 `supported`의 동의어로 쓰는 것도 잘못이다. 현재 support는 partial·contradicted·unresolved를 구분한다. 후보 실험에서는 Choice의 라벨 매핑이나 질문 분해를 평가할 수 있지만, 그 설계 자체가 한국어 의미 경계를 보존하는지 확인해야 한다. 의견 1의 제품 설명만으로 이 보존이 입증되지는 않는다.

### 놓친 위험: 점수의 품질보다 먼저 지켜야 할 경계

1. **모델 confidence는 원문의 진실일 확률로 확인된 값이 아니다.** 라벨 빈도·한국어 장문·표 각주·숫자 단위별 교정이 필요하다. 같은 모델을 반복 호출해 의견이 같아도 독립 출처가 늘지 않는다. 현재 claim-graph의 관찰 독립성(`scripts/verify_facts.py:473`)과 모델 응답의 self-consistency를 혼동하면 안 된다.
2. **판정기를 게이트 필드의 작성자로 삼으면 신뢰 경계가 이동한다.** support, claim_type, observer_group, source_role, risk, capture_review는 기계검사가 신뢰하는 입력이다. 잘못된 내용을 형식에 맞게 채우면 통과할 여지가 있다. risk 누락은 WARN(`scripts/verify_facts.py:555`), 가정·권고의 조건 보존은 검토자 책임(`references/claim-review.md:47`), 캡처 accept는 검토 필드의 일관성을 검사한다(`scripts/facts_db.py:159`). 보조 결과는 별도 제안으로 기록하고, confidence가 높다는 이유로 이 필드를 최종 승인값으로 승격하지 않아야 한다.
3. **원문은 판정 모델에도 불신뢰 입력이다.** 수집 문서의 명령형 문구·광고·전재 설명·잘린 각주가 판정을 오염시킬 수 있다. 기존 수집 정책도 원문을 불신뢰로 규정한다(`references/source-ladder.md:32`). 모델에게 게이트·대장 쓰기 권한을 주지 않고, 문서 텍스트와 판정 지시의 경계를 고정하며, 오염된 예제도 평가해야 한다. 이는 현재 취약성이 실증됐다는 뜻이 아니라 도입 시의 위험 가정이다.
4. **모델 버전 이름만 남긴 영수증은 충분하지 않다.** 요청 원문·문장·선택지 순서·프롬프트·전처리/절단·설정·모델 식별자·원응답·확률·재시도·최종 팀리드 처분을 한 입력 리비전에 묶어야 한다. 일반 audit 파일은 자동 봉인 대상이 아니다(`scripts/manifest.py:33`). 원응답을 저장하지 않고 나중에 다시 호출하면 동일 판단을 얻는다는 보장은 의견 1에 없다. A13 때문에 기존 evidence_revision만을 캐시 키로 재사용해서도 안 된다.
5. **선별 오류가 수집 표본 자체를 바꾼다.** 누락 축·소수 반론을 낮은 관련도로 떨어뜨리면 이후 게이트는 수집된 fact만 검사하여 사라진 근거를 복구하지 못한다. 특히 EXPAND의 연속 무신규 판단을 보조 모델의 “중복” 판정으로 대체하면 조기 수렴할 수 있다(`SKILL.md:73`, `scripts/join_workers.py:198`). 초기 실험은 탈락 후보도 보존하고 결과에 영향을 주지 않는 병행 비교로 해야 한다.
6. **형식 제한, 결정론, 감사 재현성, 비용은 다른 속성이다.** Choice/Score/Noul이라는 작은 출력 공간은 파싱·검증을 쉽게 할 수 있지만 동일 입력의 동일 응답이나 정확성을 자동 보장하지 않는다. 기존 워커도 고정 프롬프트·제약된 응답·검증·재시도로 형식을 맞출 수 있으나 그 추가 토큰·지연·실패 비용이 있다. 어느 쪽이 유리한지는 아직 미측정이다. “가능하니 동등”, “전용 모델이니 결정론적” 모두 근거 부족이다.
7. **30~50개는 탐색 표본이지 게이트 자동화의 보증 표본이 아니다.** 독립·동일분포의 이항 오류라는 단순 가정에서도 30/50개에 오류가 0개이면 오류율의 단측 95% 상한은 각각 약 9.50%/5.82%다(`1 - 0.05**(1/n)`로 계산). 같은 보도자료 재전재가 표본에 겹치면 이 가정도 약해진다. 의견 1:36의 표본은 실패 유형을 찾는 시작점으로는 적절하지만 낮은 치명 오류율이나 confidence 임계값을 승인하기에는 부족하다.
8. **공개 문서 조각에도 비공개 요청이 섞일 수 있다.** 공개 URL만으로도 조사 대상 조합이 드러날 수 있으며 프롬프트·보고서 문장이 더해지면 범위가 커진다. 오류·지연·재시도 시 다른 외부 모델로 넘기는 동작 역시 별도 전송이다. 기밀 범위를 고정하지 않은 상태에서는 외부 비교 실험을 시작하지 않는다. 현재 리뷰에서는 어떤 조사 입력도 외부로 보내지 않았다.

## 4. 최종 권고와 조건

**지금 선택할 것은 “실측만”이다.** 즉시 TypeSafe를 도입하지 않는다. 기존 규칙이 의미 판정까지 이미 해결했다는 주장을 정정하고, 시간·비용과 품질의 기준선을 함께 만든 뒤 작은 사전 선별 실험의 가치 여부를 결정한다. 아래는 향후 작업의 권고이며 이번 리뷰에서 구현·외부 호출을 수행하지 않았다.

### 먼저 측정할 것

- **대상별 기준선:** fact 수만 세지 말고 재열람 건수·실제 원문 토큰/길이·검토 문장 수·무태그 사실 누락·전재 후보·중복 리드·실패 캡처 수를 나눈다. 손으로 정답을 만든 표본에는 한국어 비수치 사실, 부정, 조건·기간·주체 전환, 표·각주, 전재, 어려운 단위, 정상 캡처의 빈 여백을 포함한다. “현재 파이프라인 PASS”를 의미적 정답으로 쓰지 않는다.
- **시간 구간:** 재열람 시작/끝, 판정·설명 작성, 캡처 획득/검토, 재시도, 원고 수정을 구분해 능동 작업시간과 대기시간을 기록한다. `[2]→G3`는 재검증 뒤의 경과시간이라는 보조 지표로만 둔다. G1→[2]도 시작 시각을 정확히 알 수 없으면 재열람 순수 시간으로 간주하지 않는다.
- **기존 원장의 재사용:** 비교할 G3가 실제로 참조한 `[2]` 영수증을 `prerequisite_receipts`로 찾고, revision·supersedes·실패 재시도를 확인한다(`scripts/gates.py:126`, `:131`, `:288`). `run_id`는 `_append()`마다 새 UUID이므로 동일 조사 전 과정이 같은 run_id라는 가정을 두지 않는다(`:126`). 시간대·중단·수동 지연 기록이 없으면 오차를 밝힌다.
- **경제성:** 입력 단가 외에 배치·전처리·응답 검증·실패·재검토·추가 오탐·누락 오류비용을 포함한다. 주장 수만으로 토큰 비용이 작다거나, 주의력 비용이 크다는 추정만으로 도입 가치가 없다고 판정하지 않는다.

### 사전 선별로 넘어갈 조건

첫 후보는 **무태그 사실 문장 탐지의 병행 비교**가 적절하다. 입력·정답·출력의 단위가 작고, 기존 `tagged_sentences()`의 누락 경계가 분명하며, 탐지 결과를 팀리드의 추가 검토 목록에만 넣을 수 있기 때문이다. 수집 단계의 의미 중복·관련성 선별은 그다음 후보이고, 최종 의미 승인·독립 관찰그룹 자동 인정·캡처 자동 accept는 이 권고에 포함하지 않는다.

| 조건 | 통과해야 할 내용 |
|---|---|
| 비교 기준 | 동일한 고정 한국어 표본에서 기존 워커의 사전 선별과 규칙 기반 기준선을 포함한다. luna를 쓰려면 모델·프롬프트·설정·예산부터 명시한다. TypeSafe 우위를 전제하지 않는다. |
| 품질 | 미탐과 오탐을 별도로 보고, 위험한 사례의 미탐을 전체 정확도로 가리지 않는다. confidence별 실제 오류·기권율을 평가하며 목표치는 실험 전에 정한다. 반복 실행의 라벨 안정성과 실패 응답도 측정한다. |
| 가치 | 시간 절감 또는 현재 놓치는 사실의 발견이라는 이득이 추가 검토·운영 비용을 상쇄해야 한다. 병목이 없다는 이유만으로 품질 개선 기회를 자동 종료하지 않는다. |
| 정책·기밀 | 실제 입력 전체의 외부 전송 조건을 충족하고 선택 계층을 제거해도 기존 코어가 작동해야 한다. 현재 task의 외부 API 금지는 그대로 지킨다. |
| 신뢰·감사 | 제안값과 최종 승인값을 분리하고 lead 전건 재열람을 유지한다. 요청/응답 원본과 입력 해시를 보존하며 A13의 evidence_revision만으로 검토의 최신성을 판단하지 않는다. |
| 실패 처리 | timeout·스키마 오류·버전 변경·미지원 입력은 기존 검토로 돌린다. 불확실한 판정 때문에 후보를 영구 삭제하거나 자동 confirmed로 올리지 않는다. |

이 조건을 충족하지 못하면 도입하지 않는다. 단, A01·A13 등은 TypeSafe의 필요성을 증명하는 결함이 아니라 **현재 검증 보장을 정확히 설명하고 어떤 판정기를 붙여도 같은 구멍을 확대하지 않기 위해 알아야 할 사실**이다.

### 진행 제약 기록

Orca 스킬의 절차에 따라 지정 CLI로 후속 메시지 조회와 5분 heartbeat를 시도했으나 `runtime_unavailable`이 반복됐다. 정확한 오류는 `Could not read Orca runtime metadata at C:\Users\eicic.AIDEN-DESKTOP\AppData\Roaming\orca\orca-runtime.json. Start the Orca app first.`이며, 별도로 Crashpad의 `CreateFile: 액세스가 거부되었습니다. (0x5)`가 출력됐다. 파일 기반 리뷰·로컬 반례 검증·보고서 작성은 가능했지만 코디네이터의 추가 지시와 heartbeat 전달 여부를 확인할 수 없었다. 권한 확대·다른 통신 채널·별도 에이전트는 사용하지 않았다.
