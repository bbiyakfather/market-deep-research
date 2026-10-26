# 학술 API — `search.py --type academic` 어댑터와 함정

`python scripts/search.py "쿼리" --type academic --n 5 --axis 기술요소 --work <work_dir>`
순서는 OpenAlex → Crossref → Europe PMC → Semantic Scholar → arXiv 이고, 첫 번째로 결과가 나온 백엔드의 건만 쓴다. 실패·429·0건이면 다음으로 넘어간다. 백엔드마다 `audit/search-log.jsonl` 에 1줄이 남는다(`backend` = `academic:<이름>`). 반환 필드는 `title, url, source, year, doi, authors, abstract`.

## 백엔드 (검증 2026-10-26, 실호출은 transformer 질의)
| 백엔드 | 키 | 한도 | 함정 |
|---|---|---|---|
| OpenAlex | 없이 가능 | 예산제: 키 없이 하루 $0.10, 무료 키 $1 (2026-10-26 기재값, 약관 재확인). 검색 호출이 가장 비싸다 | 목록 조회는 `page*per_page` ≤ 10,000, 그 이상은 `cursor`. `meta.count` 로 총건수 확인 |
| Crossref | 없이 가능 | `mailto` 를 붙이면 polite pool(목록 3 req/s), 없으면 1 req/s | 429 는 빈 결과가 아니라 스로틀. `message.total-results` 와 `items` 대조 |
| Europe PMC | 없이 가능 | 공개 한도 없음, 합리적 사용 | 오류가 **HTTP 200 + `resultList` 없음 + `errCode`** 로 온다. 생의학 전용. bioRxiv·medRxiv 는 키워드 검색 API 가 없어 여기서 찾는다 |
| Semantic Scholar | 선택(`SEMANTIC_SCHOLAR_API_KEY`) | 키 없이는 공유 풀이라 429 가 잦다 | 1회 재시도 후 포기하고 로그에 남긴다 |
| arXiv | 없음 | 요청 간 3초 권장 | 잘못된 질의가 `<title>Error</title>` **항목**으로 200 응답한다. 이를 논문으로 읽으면 안 된다. 스로틀은 XML 이 아니라 `Rate exceeded.` 평문 |

폴라이트 규약: 환경변수 `MDR_CONTACT_EMAIL` 이 있으면 OpenAlex·Crossref 에 `mailto` 로 붙고 User-Agent 에도 들어간다. 없으면 생략한다. 로그에는 이메일·키가 마스킹된다.
Unpaywall 은 **실제 이메일**이 필수라 어댑터에 넣지 않았다. OA 전문 위치가 필요할 때 사람이 따로 조회한다.

## 원칙
- **Never present metadata as full text.** 어댑터 결과는 제목·초록·서지일 뿐이다. 수치와 인용은 원문을 다시 열어 확인하고 `_sources/` 에 스냅샷을 남긴다(`source-ladder.md` 학술 출처 취급).
- **HTTP 200 은 성공이 아니다.** 어댑터는 오류 본문(`error`·`errCode`·arXiv Error 항목)이거나, 총건수가 0 인데 결과가 있거나 총건수가 양수인데 결과가 0건이면 실패로 처리한다. 요청 건수 대비 회수 차이는 실패가 아니며 `search-log` 의 `n_requested`/`n_returned` 로 남는다.

## 검색 완전성 4단계 (문헌 건수·곡선을 보고서에 쓸 때)
1. 총건수를 먼저 센다. 백엔드의 총건수 필드를 검색식·일자와 함께 기록한다.
2. 안정 정렬(예: 출판일 또는 ID)로 페이지를 넘긴다. 관련도 정렬은 호출마다 순서가 바뀔 수 있다.
3. 기대 건수 · 회수 건수 · 필터 후 건수를 대조한다. 어긋나면 이유를 적는다.
4. **Fail visible, not plausible.** 모자라거나 실패한 부분은 숨기지 말고 "완전성 미보장"과 함께 보고서에 드러낸다.

참고: K-Dense-AI/scientific-agent-skills paper-lookup (MIT) 번안
