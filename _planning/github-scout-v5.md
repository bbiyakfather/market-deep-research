# GitHub 탐색 v5 — 약점 보완 후보 (S2)

작성: 2026-08-06 · 방법: 5개 축(provenance / agent-verify / scraping / ledger-scale / research-agents) 병렬 웹조사 → 중복 병합. 후보 39건.

선정 제약: 새 런타임 의존성 원칙 금지(stdlib + 기존 PyMuPDF/trafilatura/curl_cffi/pandoc/chrome), 오프라인 동작, Windows. 따라서 **라이브러리 도입이 아니라 메커니즘 이식**이 기본이다.

## 약점 → 후보 매핑

| 약점 | 후보 | 근거 |
|---|---|---|
| `EV-1` | in-toto/attestation+DSSE+in-toto, sigstore/model-transparency | 둘 다 해시를 '기록'이 아니라 '검증 시 재계산해 대조하는 대상'으로 정의한다 — 아무 hex나 통과하는 경로가 구조적으로 사라진다. |
| `EV-2` | in-toto/attestation+DSSE+in-toto, contentauth/c2pa-rs, webrecorder/warcio | 캡처↔fact 결박을 세 층으로: subject/predicate 한 덩어리 서명, PNG 청크 내장 binding, 그리고 source_url 대신 payload_sha256 + 본문 내 발견 오프셋. |
| `EV-3` | benhoyt/dhash, contentauth/c2pa-rs, webrecorder/warcio | 이미지 돌려막기를 지각해시(sha256으로는 1픽셀 회피)로 탐지하고, 내장 fact_id binding으로 캡처가 스스로 증언하게 하며, 중복은 침묵 대신 revisit식 refers_to 선언을 강제한다. |
| `EV-5` | dbt-labs/dbt-core, in-toto/attestation+DSSE+in-toto, great-expectations | verify_event by="lead" 한 줄 자기신고를 실행 결과 구조체로 교체 — args/command·returncode·stdout_sha256·항목별 observed_value가 있어야 게이트가 유효하다. |
| `EV-7` | google-deepmind/long-form-factuality(SAFE), nielstron/quantulum3, arXiv 2605.06635 | UNIT 정규식 화이트리스트가 근본 원인 — 화이트리스트를 버리고 '숫자 전부 검출 + denylist로 깎기'(quantulum3 설계) 또는 '원자사실 분해→각각 검증'(SAFE)으로 뒤집어야 새는 방향이 안전해진다. |
| `EV-8` | RFC 6962/rekor, sigstore/model-transparency, theupdateframework/python-tuf | 재봉인=세탁 경로를 3중으로 막는다: append-only 머클 체인 + checkpoint(과거 수정은 consistency proof 불가), 정렬된 canonical manifest의 루트 해시, monotonic version/expires/prev_hash 거부 규칙. wacz-auth는 같은 목적이나 서명키를 요구해 오프라인 제약상 후순위. |
| `EV-9` | Raldir/FEVEROUS, princeton-nlp/ALCE, arXiv 2605.06635 | '값일치 폴백이 태그 귀속을 붕괴'시키는 문제의 3단 해법 — 셀 좌표 주소화로 결박 후보를 같은 행/열로 제한, ablation precision으로 우연 일치 태그를 검출, AST containment로 거리 휴리스틱 자체를 폐기. |
| `GS-1` | Aider/SWE-bench 하네스, dbt-labs/dbt-core, dagster asset checks | '검증도구 실행과 결박 없음'은 verify_cmd를 게이트 정의의 필수 필드로 두고 하네스가 subprocess 실행 → returncode==0에서만 PASS 파생 + 실행 커맨드가 아티팩트(args)에 박혀야 유효, 로 닫힌다. |
| `GS-2` | GitHub required status checks, in-toto verify(fail-closed), dagster asset checks | '증거 부재 = 통과'를 '부재 = 영구 차단'으로 반전. 게이트 id를 사전 등록하고 PASS 아티팩트 부재는 UNKNOWN→FAIL. dagster는 같은 fail-open 실패모드가 프로덕션 엔진에도 있다는 반례 근거로 쓴다. |
| `GS-7` | apache/airflow HITL, temporalio/temporal Signals | 동의는 에이전트가 쓸 수 없는 채널(사용자 전용 입력)에서만 들어와야 하고, consent는 한 줄 필드가 아니라 ts·actor·payload를 가진 불변 이벤트여야 한다. |
| `FP-1` | kurtmckee/feedparser, adbar/trafilatura, feroxbuster | MIME 정확일치 차단을 접미사 규칙 + bozo 강등으로 바꾸고(피드 자체는 통과시키되), 피드/템플릿을 본문으로 오인하는 건 반복 블록 제거와 응답 간 유사도 비교로 잡는다. |
| `FP-2` | charset_normalizer/bs4 EncodingDetector, kurtmckee/feedparser | EUC-KR 모지바케가 '성공'으로 통과하는 이유는 latin-1이 모든 바이트를 예외 없이 디코드하기 때문 — latin-1/cp1252를 성공 근거에서 배제하고 RFC 3023 시도순서 + U+FFFD·한글 음절 비율 후검증을 붙인다. |
| `FP-3` | adbar/trafilatura, feroxbuster, schema.org paywall 규약 | '200 + 장문이면 ok'의 원인은 게이트가 원시 HTML 길이에 걸려 있다는 것 — 게이트를 추출 후 본문 250자로 옮기고, soft-404는 베이스라인 프로브 유사도로, 페이월 티저는 isAccessibleForFree 선언으로 각각 다른 축에서 잡는다. |
| `ROT-1` | searxng/searxng, VeNoMouS/cloudscraper, urllib3 Retry | 429/CAPTCHA는 재시도가 아니라 엔진 격리(1시간/1일 suspend)로 처리하고, 200/403 차단 페이지는 본문 마커 AND 조건으로 '결과 없음'과 분리하며, 남은 일시 오류만 Retry-After 존중 백오프(status_forcelist 명시 필수)로 돌린다. |
| `COV-2` | edgi-govdata-archiving/wayback | requested_ts와 actual_ts를 타입 수준에서 분리하고 허용 오차창을 상수로 박아 초과 시 실패 처리 — closest 스냅샷을 검증 없이 인용하는 경로가 유일한 정답 구조로 대체된다. |
| `OPS-1` | SQLite WAL(stdlib sqlite3), filelock/msvcrt, O_APPEND 원자성 반례 | 동시 쓰기 lost-update를 '검출 가능한 에러'로 바꾸는 세 경로. 윈도우 open('a')는 1KB 초과에서 원자적이지 않다는 실측이 있어 '락 없는 append'는 선택지가 아니고, JSONL을 유지한다면 msvcrt 배타락이 최소 처방이다. |
| `SC-1` | Bazel Skyframe, dbt-core state:modified+, SQLite 인덱스 조회 | 전건 O(N) 재검증은 verify 결과를 key=sha256(fact_sha+verifier_version+rule_set_sha)로 캐싱하면 사라진다 — 단 rule_set_sha를 키에 섞지 않으면 규칙 수정 후에도 옛 판정이 살아남는 침묵 버그가 된다. |
| `SC-2` | rapidfuzz/RapidFuzz (실제 이식은 stdlib difflib) | merge_evidence는 blocking(기존 make_claim_key) + 블록 내부 유사도 + union-find 3단이면 되고, 새 의존성 없이 difflib로 시작해 느려질 때만 rapidfuzz로 교체하는 순서가 맞다. |
| `SC-3` | langchain-ai/open_deep_research | 미수렴의 절반은 하드캡 부재 — 라운드 카운터 상한 + '조사 충분'을 서술형이 아니라 대장의 research_complete 레코드로 이산화하고, 실제 종료는 신규성 포화율로 판정한다. |
| `SC-6` | deepeval/ragas 3값 verdict, stanfordnlp/dspy, open_deep_research | 동결→수리 루프가 안 끝나는 이유는 실패가 전부 같은 무게라서다. no(모순)=하드 블로커, idk(원문에 없음)=소프트로 나누고 idk에만 시도 상한 2를 걸면 루프가 원리적으로 종료된다(dspy: 재시도 시 직전 실패 사유 주입). |
| `SC-7` | SQLite WAL, O_APPEND 원자성 글, pyeventsourcing 스냅샷 | run_ledger._append()가 매번 전 대장을 재직렬화해 O(N²)인 게 병목 — INSERT 또는 1줄 append로 O(1)화하고, 전 대장 재생은 스냅샷 행으로 O(변경분)으로 줄인다. Litestream 같은 사이드카는 명백한 과설계이고 sqlite3.Connection.backup()으로 대체. |
| `SC-8` | Bazel change pruning, dbt-core state:modified+, SQLite | 말단 1건 수정이 전량 재실행되는 건 변경 반경 그래프가 없기 때문 — fact→evidence→섹션→PDF 간선을 기록해 BFS 하위 폐포만 재실행하고, 값이 그대로면 early cutoff로 자른다. 간선 계측이 없으면 추정 그래프가 조용히 틀리므로 '전량 재실행' 폴백을 정직하게 남긴다. |

> confidence 기준: high = 저장소·문서 실재 + 인용된 메커니즘 세부까지 확인 / medium = 저장소는 확실히 실재하나 인용 상수·API 상태가 미확인이거나 폐기됨(이식 전 원문 재확인 필요) / low = URL·실재 미확인. 이번 병합에서 low는 0건 — 유일한 의심 후보였던 arXiv 2605.06635와 notthewizard O_APPEND 글을 직접 fetch해 둘 다 실존 확인했다.

## 후보 상세

### in-toto/attestation + secure-systems-lab/dsse + in-toto/in-toto (3건 병합)

- URL: https://github.com/in-toto/attestation , https://github.com/secure-systems-lab/dsse , https://in-toto.readthedocs.io/en/latest/command-line-tools/in-toto-verify.html
- 정체: 산출물(subject)과 주장(predicate)을 한 덩어리로 묶어 서명 가능한 Statement 포맷 + 그 봉투(DSSE) + 단계 실행을 감싸 materials/products/command를 남기는 link 메타데이터. 원본 후보 1번과 12번은 같은 프로젝트 계열이고 이식 규약이 사실상 하나(재해싱 대조 + 실행기록 결박)라 병합.
- 성숙도: CNCF in-toto 공식 스펙 저장소(spec/v1/statement.md 확인), dsse star 111·commit 120, sigstore/cosign/GitHub Actions attest가 실제 채택. in-toto는 SLSA provenance의 기반.
- **훔칠 메커니즘**: Statement: {_type, subject:[{name,digest:{sha256}}], predicateType, predicate}. 규칙 두 개가 핵심 — (1) 아티팩트 매칭은 오직 digest로, (2) 검증자는 name이 가리키는 실물을 재해싱해 subject.digest와 대조한 뒤에야 predicate를 믿는다. 즉 해시가 '기록'이 아니라 '재계산 대조 대상' → 아무 hex나 통과가 구조적으로 불가. subject(캡처)와 predicate(fact·수치·as_of·source_url)가 같은 덩어리라 캡처↔fact 결박이 자동. DSSE는 raw JSON이 아니라 PAE(type,body)='DSSEv1'+SP+LEN(type)+SP+type+SP+LEN(body)+SP+body를 서명해 길이 프리픽스로 경계/타입 혼동을 막고, 검증에 쓴 바이트열을 재파싱 없이 그대로 앱에 넘긴다. link 메타데이터는 {materials(실행 전 해시), products(실행 후 해시), byproducts(stdout/stderr), return value, command}를 남기고, verify는 '해당 step의 link가 존재 + returncode==0 + products 해시가 현재 파일과 일치'를 필수 조건으로 본다 → 증거 파일 부재는 통과 불가(fail-closed).
- 겨냥 약점: `EV-1, EV-2, EV-3, EV-5, GS-1, GS-2` · 이식비용 **low** · confidence **high**
- 이식 노트: 새 의존성 0, 완전 오프라인. evidence.jsonl 한 줄을 Statement 모양으로 바꾸고 verify를 '파일 재해싱 → subject.digest 대조'로 교체. 게이트 실행은 subprocess 래퍼로 감싸 {command, argv, returncode, stdout_sha256, materials, products, started_at}를 남긴다(subprocess+hashlib+json). 서명은 넣지 말 것 — cryptography가 없고 오프라인이라 키 관리가 순비용이다. 서명 없이 Statement 구조 + 재해싱 대조만으로 EV-1/EV-2는 죽는다. PAE가 정말 필요해지면 f-string 3줄, 그마저도 hmac(사용자 보관 키)로 충분.

### sigstore/model-transparency

- URL: https://github.com/sigstore/model-transparency
- 정체: 디렉터리 전체(파일 수천 개)를 하나의 manifest로 직렬화해 서명·검증하는 순수 파이썬 도구. '무엇을 서명 대상 payload로 고정하는가'의 레퍼런스.
- 성숙도: sigstore 공식 org, Python, 활발. DSSE 봉투 + in-toto/json payload 채택 명시.
- **훔칠 메커니즘**: manifest = [(상대경로, 해시알고리즘, digest)]의 정렬된 목록이고 이 목록 자체가 payload다. 검증은 저장된 manifest를 읽어 믿는 게 아니라 현재 디렉터리를 같은 규칙으로 재직렬화 → diff → changed/missing/new 전부를 위반으로 본다. 경로가 payload 안에 있어 파일 이동·개명도 위반. 큰 파일은 고정 크기 샤드 해시를 상위로 접어 부분 재해싱을 허용. 우리 manifest.py의 _scan/verify와 골격은 같은데 차이는 '재해싱 대조가 곧 검증의 정의'라는 점.
- 겨냥 약점: `EV-1, EV-8` · 이식비용 **low** · confidence **high**
- 이식 노트: 새 의존성 0, 오프라인 100%. 현재 manifest.py는 entries 딕트를 그대로 덮어써서 재봉인이 곧 세탁이다. entries를 정렬 리스트로 정규화 → canonical bytes → 그 바이트열의 sha256(manifest_root)을 별도 파일/대장에 남기는 것만으로 절반 회수. 샤드 해싱은 우리 파일 크기에선 YAGNI.

### RFC 6962 Certificate Transparency + sigstore/rekor

- URL: https://www.rfc-editor.org/rfc/rfc6962.html , https://github.com/sigstore/rekor
- 정체: 추가만 가능한 머클 트리 로그. 항목 포함(inclusion)과 새 로그가 옛 로그의 상위집합임(consistency)을 암호학적으로 증명.
- 성숙도: RFC 6962 IETF 표준. rekor star 1.2k·commit 2429, 오프라인 inclusion proof 검증이 명시적 설계 목표.
- **훔칠 메커니즘**: 도메인 분리 해싱: leaf=SHA256(0x00||record), node=SHA256(0x01||left||right) (접두 없으면 leaf를 node로 위장하는 2nd-preimage 성립). 로그 상태 = checkpoint(tree_size, root_hash). inclusion proof = leaf→root 형제 해시 log2(n)개로 로그 전체 없이 대조. consistency proof = (size1,root1)→(size2,root2)가 앞부분을 하나도 안 고쳤음을 증명 → 과거를 고쳐 재봉인한 로그는 옛 checkpoint와의 consistency proof를 절대 만들 수 없다. EV-8 정조준: manifest를 '현재 스냅샷 1개'가 아니라 '(경로,digest,ts,사유) 이벤트 추가 전용 로그 + 게이트 통과마다 찍은 checkpoint 열'로 바꾸면 세탁 시도가 checkpoint 불일치로 드러난다.
- 겨냥 약점: `EV-8` · 이식비용 **low** · confidence **high**
- 이식 노트: hashlib만으로 leaf/node/inclusion/consistency 4개 알고리즘 전부 40~60줄. 새 의존성 0, 완전 오프라인. 이미 run_ledger.py가 있으니 append 지점에 롤링 루트만 물리면 된다. rekor 서버·Trillian은 절대 가져오지 말 것(Go+DB). inclusion proof도 당장은 불필요 — 롤링 루트 + checkpoint 열만으로 EV-8은 닫힌다.

### contentauth/c2pa-rs (C2PA 스펙 hard binding)

- URL: https://github.com/contentauth/c2pa-rs , https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html
- 정체: 파일 바이트에 출처 메타를 암호학적으로 결박하는 산업표준(Content Credentials). 훔칠 건 알고리즘 2개뿐.
- 성숙도: star 377·commit 1748, Rust, beta(0.x), 2개월 주기 릴리스. 'assertions and hard bindings 지원' 명시.
- **훔칠 메커니즘**: (1) hard binding = c2pa.hash.data 어서션 {alg, exclusions:[{start,length}], hash} — 매니페스트가 파일 안에 박히면 해시 순환참조가 생기므로 매니페스트 구간을 exclusion으로 빼고 나머지 전 구간을 해싱한다 → 파일이 자기 해시를 들고 다니면서 해시가 안정적. (2) hashed URI = claim이 각 어서션을 {url, hash}로 참조하고 claim만 서명 → 어서션 하나만 갈아끼워도 즉시 깨짐. 우리 직역: 캡처 PNG에 tEXt/iTXt 청크(keyword 'mdr.binding')로 {fact_id, claim_text, value, unit, source_url, as_of, run_id, sha256_of_source}를 심고, 캡처 해시는 '그 청크 구간을 제외한 PNG 전체'로 계산. 이미지 1장을 다른 fact에 돌려막으면 내장 binding의 fact_id/source_url이 어긋나 잡힌다. PNG 청크: [길이4B BE][타입4B][데이터][CRC32 4B], CRC는 타입+데이터 대상, 텍스트 청크는 IHDR~IEND 사이 순서 제약 없음.
- 겨냥 약점: `EV-2, EV-3` · 이식비용 **low** · confidence **high**
- 이식 노트: c2pa-rs/c2pa-python은 절대 넣지 말 것(Rust 바이너리 휠 + 진짜 서명엔 인증서 필요 = 오프라인·키 없는 환경과 불일치). 청크 삽입/제거/구간계산은 struct + zlib.crc32로 25~40줄, 새 의존성 0. exclusion 구간은 우리가 IEND 직전에 append하므로 (오프셋, 길이)로 자명. PDF 캡처가 섞이면 PyMuPDF metadata로 같은 짓을 하면 된다.

### webrecorder/warcio (WARC/1.1 ISO 28500)

- URL: https://github.com/webrecorder/warcio
- 정체: WARC 리더/라이터. 훔칠 건 라이브러리가 아니라 헤더 어휘와 그 의미론.
- 성숙도: star 466, Apache-2.0, 순수 파이썬(의존성 사실상 six 하나). WARC 1.0/1.1 ISO 표준 지원.
- **훔칠 메커니즘**: WARC-Block-Digest(레코드 블록 전체) vs WARC-Payload-Digest(HTTP 본문만) → '어느 바이트열에서 이 사실을 뽑았는가'가 URL이 아니라 바이트 다이제스트로 고정된다. request/response는 WARC-Concurrent-To로 짝지어지고, 같은 페이로드를 다시 만나면 본문을 재저장하지 않고 revisit 레코드에 WARC-Refers-To로 '이건 아까 그것과 동일'을 1급 시민으로 선언한다. 우리 직역: evidence에 source_url만 두지 말고 payload_sha256(=_sources에 저장된 원문 바이트 해시) + '그 원문 안에서 claim_text가 발견된 오프셋/문자열'을 함께 박고, verify는 원문을 다시 열어 그 문자열이 그 다이제스트의 바이트열 안에 있는지 확인. 캡처 중복은 침묵 재사용이 아니라 명시적 refers_to=E001 선언을 강제.
- 겨냥 약점: `EV-2, EV-3` · 이식비용 **low** · confidence **high**
- 이식 노트: warcio 설치 불필요(원문 바이트는 이미 fetch.py가 _sources에 저장 중). 필드 4개(payload_digest, block_digest, concurrent_to, refers_to) + revisit 의미론만. 새 의존성 0. 참고로 warcio는 transfer-encoding 응답에서 payload digest가 부정확한 알려진 결함(issue #74/#93/#162)이 있어 라이브러리를 쓰는 쪽이 오히려 손해.

### benhoyt/dhash (참고: JohannesBuchner/imagehash)

- URL: https://github.com/benhoyt/dhash , https://github.com/JohannesBuchner/imagehash
- 정체: 지각 해시. 픽셀이 조금 달라도 비슷한 이미지면 비슷한 해시가 나와 캡처 재사용을 해밍거리로 잡는다.
- 성숙도: dhash = Ben Hoyt, MIT, 코드 극소량, PyPI. imagehash = star 3.9k·commit 347.
- **훔칠 메커니즘**: 그레이스케일 → (size+1)×size 축소 → 가로 이웃 픽셀 밝기 비교로 '증가면 1' 비트를 쌓아 64비트 row hash → 세로로 반복해 64비트 column hash → 합쳐 128비트. 비교는 해밍거리. EV-3 직역: 모든 _captures/*.png의 dhash를 evidence에 기록하고, 서로 다른 fact_id의 캡처 쌍 해밍거리가 임계(128비트에서 대략 <10) 이하면 게이트 실패 — 단 evidence에 refers_to(같은 화면임을 명시 선언)가 있으면 통과. sha256만으로는 1픽셀만 바꿔도 회피되므로 지각해시가 필수.
- 겨냥 약점: `EV-3` · 이식비용 **low** · confidence **high**
- 이식 노트: 두 라이브러리 다 설치 금지 — imagehash는 numpy+scipy, dhash는 순수파이썬이지만 이미지 로딩에 PIL/wand를 요구한다. 이미 HARD 의존성인 PyMuPDF로 대체: fitz.Pixmap(png) → .samples에서 최근접 샘플링으로 9×8 그레이 그리드를 뽑아 비트를 쌓으면 30줄. 새 의존성 0, 오프라인 100%. 임계값은 실제 캡처 몇 쌍으로 튜닝해야 하는 knob이니 상수 하드코딩 말고 gates.json에 노출할 것.

### dagster-io/dagster — asset checks (blocking)

- URL: https://docs.dagster.io/api/dagster/asset-checks
- 정체: 파이프라인 자산에 '검사'를 1급 객체로 붙여 결과 객체가 통과/실패를 기계 판정하고 실패 시 하류 실행 자체를 막는다.
- 성숙도: star 1.3만+ 최상위 OSS 오케스트레이터, asset check는 1.4~1.8에서 실험→정식화.
- **훔칠 메커니즘**: (1) @asset_check(asset=X, blocking=True)로 검사를 자산에 결박 — 검사는 선언이 아니라 실행 가능한 함수. (2) 반환값이 자유문자열이 아니라 타입 객체 AssetCheckResult(passed: bool, severity: ERROR|WARN, metadata). (3) blocking+ERROR+passed=False면 하류 미실행, WARN이면 통과 → 심각도 축이 게이트 강도와 직결. (4) 중요한 함정: 결과가 아예 emit되지 않으면 게이트가 열리고 경고만 로그된다(fail-open). 우리 GS-2(watch 파일 부재=fresh)와 정확히 같은 실패모드가 프로덕션 엔진에도 존재 → '결과 없음 = FAIL'로 뒤집어야 한다는 반례 근거.
- 겨냥 약점: `GS-1, GS-2` · 이식비용 **low** · confidence **high**
- 이식 노트: 개념만 이식. 게이트 반환 타입을 자유문자열에서 CheckResult(passed: bool, severity: str, evidence: dict) dataclass로 바꾸고 판정은 dataclass 필드에서만 읽게 강제. dataclasses/enum만, 새 의존성 0. Dagster 도입 불필요.

### dbt-labs/dbt-core — run_results.json + state:modified+ (2건 병합)

- URL: https://docs.getdbt.com/reference/artifacts/run-results-json , https://docs.getdbt.com/reference/node-selection/methods
- 정체: 실행 판정을 스키마 버전 붙은 단일 아티팩트로 남기는 규약(run_results.json) + 이전 실행 manifest를 기준선으로 '바뀐 노드 + 하위 폐포'만 재실행하는 선택 문법(state:modified+). 같은 저장소·같은 아티팩트 계보라 병합.
- 성숙도: star 1만+, 데이터 업계 사실상 표준. run_results 스키마 v6, CI/CD에서 state:modified+ 광범위 사용.
- **훔칠 메커니즘**: (A) 판정의 자료구조화: results[] 각 원소가 unique_id(manifest 노드와의 조인 키), status(pass/fail/error/skipped), failures(정수), execution_time, timing[], message, compiled_code. 상단에 metadata(schema version, invocation_id) + args(실행에 쓰인 인자 전체) → 호출 명령까지 아티팩트에 박힌다. 후속 도구는 이 파일만 읽고 상태를 재구성. (B) 증분: 이전/현재 manifest 해시 diff로 modified 집합 산출 → 그래프 연산자 '+'로 하위 폐포까지 확장 → 상위 실패 시 하류는 '통과'가 아니라 'skipped'로 남는다(미실행이 조용히 PASS로 계상되는 것을 차단).
- 겨냥 약점: `GS-1, EV-5, SC-8, SC-1` · 이식비용 **low** · confidence **high**
- 이식 노트: 새 의존성 0. gate_results.json(schema_version, invocation_id, args=실제 커맨드라인, results=[{gate_id, status, failures, started_at, completed_at, command, stdout_sha256}])을 json+dataclasses로 생성 — args를 필수로 두면 GS-1이 구조적으로 해결(명령이 없으면 게이트 무효). 증분 쪽은 인접리스트 dict + BFS 20줄. 진짜 비용은 코드가 아니라 '간선을 어디서 얻나' — fact→섹션 의존을 보고서 생성기가 기록하도록 한 줄 계측이 필요하고, 그게 없으면 그래프가 추정이 되므로 '전량 재실행' 폴백을 정직하게 남길 것.

### great-expectations/great_expectations

- URL: https://docs.greatexpectations.io/docs/0.18/reference/learn/terms/checkpoint/
- 정체: 기대(Expectation) Suite를 데이터에 실행(Checkpoint)하고 결과를 JSON으로 Store에 영속화. 후속 액션은 그 결과 객체를 입력으로 받는다.
- 성숙도: star 1만+, 데이터 품질 OSS 대표. 0.18 문서에서 Checkpoint/Store 개념 안정 문서화.
- **훔칠 메커니즘**: 3층 분리가 핵심 — (a) 기대 정의(선언, 재사용 가능) / (b) 실행(Checkpoint) / (c) 결과 저장(Store). Checkpoint의 action_list에 StoreValidationResultAction이 있을 때만 결과가 기록된다 → '검증했다'와 '검증 증거가 남았다'가 별개 단계로 명시. 결과 JSON은 기대 하나하나에 success + 관측된 실제값(observed_value)까지 담아 왜 통과/실패인지 재현 가능한 수치를 남긴다.
- 겨냥 약점: `GS-1, EV-5` · 이식비용 **low** · confidence **high**
- 이식 노트: GE 도입은 과함(무거운 의존성 트리) — 원본 평가의 medium을 low로 내린다. 훔칠 건 규약뿐: 게이트마다 기대 목록을 선언 파일(json)로 두고 실행기가 각 기대에 {expectation, success, observed_value}를 남긴다. EV-5의 verify_event by="lead" 한 줄 자기신고를 이 배열로 교체. 순수 stdlib.

### apache/airflow — HITL operators (3.1+)

- URL: https://airflow.apache.org/docs/apache-airflow/stable/tutorial/hitl.html
- 정체: 워크플로 중간의 '사람의 응답'을 태스크로 모델링. 응답 값이 하류 실행 여부를 결정한다.
- 성숙도: 직접 확인(2026-08): Airflow 3.1 정식 기능(AIP-90), 3.3 문서 유지 중이며 3.3에서 triggerer 대신 scheduler 관리 awaiting_input 상태로 개선. HITLEntry/HITL/Approval/HITLBranch 4종 확인.
- **훔칠 메커니즘**: GS-7의 정면 해법. (1) 사람의 응답은 에이전트가 접근할 수 없는 별도 채널로만 들어온다 — Airflow UI의 'Required Actions' 탭 또는 REST API PATCH .../hitlDetails. 태스크 코드가 스스로 자기 응답을 쓸 수 없는 구조. (2) ApprovalOperator는 선택지를 Approve/Reject로 고정하고 Reject 시 태스크는 성공 처리하되 하류 전체를 skip — 거부가 '에러'가 아니라 '경로 차단'으로 표현된다. (3) 응답은 태스크 인스턴스 상태(3.3부터 awaiting_input 전용 상태)로 영속화돼 감사 가능.
- 겨냥 약점: `GS-7` · 이식비용 **low** · confidence **high**
- 이식 노트: 핵심은 '동의는 에이전트가 쓸 수 없는 경로에서만 들어온다'는 채널 분리 하나. consent를 에이전트 세션 밖 입력(사용자만 편집하는 consent 파일, 또는 대화 원문의 사용자 발화 매칭)에서만 읽고 에이전트 도구로 쓴 값은 무효 처리. deferrable/awaiting_input 구현은 우리 세션 단위 실행엔 불필요 → 원본 medium을 low로 조정. stdlib만.

### temporalio/temporal — Signals + Event History

- URL: https://docs.temporal.io/workflow-execution
- 정체: 워크플로 실행 전체가 append-only 이벤트 히스토리로 기록되고 사람/외부 결정은 Signal로 주입된다. 상태는 히스토리 재생으로 복원하며 재생 결과가 달라지면 즉시 실패.
- 성숙도: star 1.4만+ CNCF 생태계, 상용 뒷받침. HITL 승인 패턴 공식 문서화.
- **훔칠 메커니즘**: (a) 결정론 강제 — 상태는 '에이전트가 요약한 문장'이 아니라 이벤트 히스토리에서 재생 가능한 값. 같은 히스토리 재생에서 다른 커맨드가 나오면 NondeterminismError → 자기신고와 기록의 불일치를 런타임이 잡는다. (b) 승인의 이벤트화 — 외부 액터가 Signal을 보내고 결정·리마인더·에스컬레이션·타이머가 전부 히스토리 항목으로 남아 크래시 후에도 승인 사실이 소실되지 않는다. consent가 '한 줄 필드'가 아니라 타임스탬프·발신자·페이로드를 가진 불변 이벤트.
- 겨냥 약점: `GS-7, EV-5` · 이식비용 **low** · confidence **high**
- 이식 노트: Temporal 서버 도입은 과잉 — 원본 medium을 low로 조정(이식분이 dict 수준). 대장을 append-only JSONL 이벤트 로그로 두고 verify_event를 {ts, actor, actor_channel, gate_id, verdict, evidence_ref}로 기록, 상태는 로그를 재생해 계산하고 파생 상태를 직접 쓰지 않는다. 재생값≠신고값이면 FAIL. json+datetime만.

### GitHub required status checks (+ pre-commit / lefthook)

- URL: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks
- 정체: 특정 이름의 체크가 '성공으로 보고됨' 상태일 때만 머지를 허용. 체크가 아예 보고되지 않으면 PR은 'Expected — Waiting for status to be reported'로 영원히 막힌다.
- 성숙도: GitHub 플랫폼 기본 기능(문서 확인). pre-commit star 1.3만+, lefthook 6천+.
- **훔칠 메커니즘**: GS-2에 대한 가장 순수한 교훈 — '증거 부재'가 통과가 아니라 영구 차단으로 매핑된다. 게이트 이름 목록이 브랜치 보호 규칙에 사전 등록되고 실행 주체는 PR 작성자가 아니라 CI. '경로 필터나 이름 변경으로 required check가 트리거되지 않으면 영원히 막힌다'는 현상은 버그가 아니라 fail-closed의 정상 동작(문서에 명시). 훅 러너 쪽은 다른 축 — 검증 실행을 행위(커밋)에 자동 결박해 '실행을 깜빡함'을 불가능하게 만든다.
- 겨냥 약점: `GS-1, GS-2` · 이식비용 **low** · confidence **high**
- 이식 노트: 두 줄 규약. (1) 필요한 게이트 id 목록을 워크플로 정의에 사전 등록하고 종료 시 '등록된 id 전부에 PASS 아티팩트 존재'를 확인 — 아티팩트 없음은 UNKNOWN→FAIL(현재 fresh 기본값을 반전). (2) 단계 전환 지점에 검증 실행을 자동 결박. 순수 stdlib. lefthook/pre-commit 실제 도입 불필요(트리거가 커밋이 아니라 단계 전환).

### kurtmckee/feedparser (encodings.py + http.py)

- URL: https://github.com/kurtmckee/feedparser
- 정체: RSS/Atom/RDF/JSON Feed 파서. 20년 넘게 망가진 실물 피드를 상대해온 관용 파싱 규약(RFC 3023 해석 + bozo 플래그).
- 성숙도: develop 브랜치 api.py·http.py·encodings.py 현재 소스 직접 확인(2026-08).
- **훔칠 메커니즘**: (1) MIME 정확일치를 버리고 접미사 규칙: application/*이면서 endswith('+xml') 또는 {application/xml, xml-dtd, xml-external-parsed-entity}면 XML, text/*이면서 +xml 또는 {text/xml,...}면 XML, {application/json, application/feed+json}이면 JSON 피드 → rss+xml/atom+xml/rdf+xml이 자동 통과. (2) 그 외 타입은 거부가 아니라 NonXMLContentType을 bozo_exception에 담고 파싱은 계속 — MIME은 신뢰도 강등 신호이지 차단 게이트가 아니다. (3) 파싱 실패 시 strict XML → loose XML → JSON 폴백. (4) 인코딩은 RFC 3023 우선순위를 타입별로 다르게: application/*는 http_encoding or xml_encoding or 'utf-8', text/*는 http_encoding or 'us-ascii', Content-Type 부재면 xml_encoding or 'iso-8859-1'. (5) XML 선언 스니핑 rb'^<\?.*encoding=[\'\"](.*?)[\'\"].*\?>'. (6) 디코드 시도 순서: rfc3023 → xml_encoding → bom → chardet → utf-8 → windows-1252 → iso-8859-2. 선언≠실제면 CharacterEncodingOverride, 전부 실패면 CharacterEncodingUnknown.
- 겨냥 약점: `FP-1, FP-2` · 이식비용 **low** · confidence **high**
- 이식 노트: MIME 판정은 순수 문자열 로직 5줄, 인코딩 시도순서도 stdlib codecs만으로 복제 가능 — feedparser를 의존성으로 넣지 말고 규칙만 베낀다(순수 파이썬이라 넣어도 감점은 작지만 이득이 없다). FP-1의 핵심 교체점은 'MIME 불일치 = 차단'을 'MIME 불일치 = bozo 플래그'로 바꾸는 것 하나.

### jawah/charset_normalizer + psf/requests(apparent_encoding) + bs4 EncodingDetector

- URL: https://charset-normalizer.readthedocs.io/en/latest/api.html
- 정체: 바이트열에서 실제 인코딩을 추정하는 세 층위. 성공 판정을 '예외 유무'가 아니라 chaos/coherence 점수로 바꾸는 설계.
- 성숙도: charset_normalizer 공식 API 문서에서 from_bytes 기본값 직접 확인, requests 2.26.0(2021-08) chardet→charset_normalizer 전환 확인, bs4 4.14.3 EncodingDetector 확인.
- **훔칠 메커니즘**: (1) from_bytes(data, steps=5, chunk_size=512, threshold=0.2, ...) — threshold는 허용 가능한 mess 최대 비율이고 초과 후보는 매치에서 탈락. .best()가 None이면 '어떤 인코딩으로도 깨끗하게 안 읽힘' = 실패 신호. 5×512바이트만 샘플링해 장문에도 싸다. (2) 함정: Content-Type이 text/*인데 charset이 없으면 requests의 r.encoding이 ISO-8859-1로 고정된다(RFC 2616 유산). EUC-KR 한국 사이트가 정확히 이 경로로 모지바케가 되고, latin-1은 모든 바이트를 성공 디코드하므로 예외가 안 나서 '성공'으로 통과한다. (3) bs4 EncodingDetector.find_declared_encoding으로 <meta charset>을 바이트 단계에서 뽑고 BOM·HTTP헤더 → meta → 검출기 순 우선순위, exclude_encodings=['ISO-8859-1']로 latin-1 '항상 성공' 함정 배제.
- 겨냥 약점: `FP-2` · 이식비용 **low** · confidence **high**
- 이식 노트: 주의 — '이미 설치되어 있다'는 전제는 requests 기준이다. 우리 스택은 curl_cffi라 charset_normalizer/bs4 존재는 미확인이니 라이브러리 호출이 아니라 규칙만 이식하는 게 안전하다: ①헤더에 charset 명시 없으면 응답 객체의 encoding을 무시 ②codecs로 후보 인코딩(utf-8, euc-kr, cp949)을 순서대로 시도하되 latin-1/cp1252는 절대 '성공'의 근거로 쓰지 않음 ③디코드 결과의 U+FFFD 개수와 한글 음절(AC00–D7A3) 비율을 후검증 게이트로 추가(stdlib 3줄, 한국 소스 특화라 chaos 점수보다 우리에겐 더 정확). 새 의존성 0.

### VeNoMouS/cloudscraper (cloudflare.py)

- URL: https://github.com/VeNoMouS/cloudscraper
- 정체: Cloudflare 안티봇 우회 모듈. 우회보다 '지금 받은 200/403/503이 진짜 콘텐츠인가 차단 페이지인가'를 판정하는 시그니처 목록이 가치.
- 성숙도: master 브랜치 cloudflare.py 소스 직접 확인, v1/v2/v3/Turnstile 핸들러로 분리 유지보수 중.
- **훔칠 메커니즘**: 판정은 전부 (Server 헤더 + 상태코드 + 본문 정규식) 3중 AND로 오탐을 극히 낮췄다. (a) IUAM = Server startswith 'cloudflare' AND status in [429,503] AND 본문에 '/cdn-cgi/images/trace/jsch/' AND '<form .*?="challenge-form" action="/\S+__cf_chl_f_tk='. (b) Captcha = ... status==403 AND '/cdn-cgi/images/trace/(captcha|managed)/'. (c) Firewall = ... status==403 AND '<span class="cf-error-code">1020</span>'. 신형은 '/cdn-cgi/challenge-platform/' 경로가 마커. 세 메서드 모두 AttributeError를 잡아 False 반환(시그널 판독 실패는 '차단 아님'으로 안전측). 핵심 전제 — 상태코드만으로는 판별 불가(403/429/503 모두 정상 응답일 수 있음)라서 본문 마커를 필수 조건으로 둔다.
- 겨냥 약점: `ROT-1, FP-3` · 이식비용 **low** · confidence **high**
- 이식 노트: cloudscraper 설치 금지(JS 엔진까지 딸려온다). 정규식 4개 + 헤더/상태코드 조건을 fetch 결과 검증 함수에 붙이면 끝, 새 의존성 0. 우리 상황용 시그널 2개 추가: 본문이 <3KB인데 <noscript>와 'Enable JavaScript and cookies' 문구가 있으면 차단, Server가 cloudflare가 아니어도 <title>'Just a moment...'는 강한 마커.

### urllib3 Retry (urllib3.util.retry) + jd/tenacity

- URL: https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html
- 정체: 표준 재시도 엔진. Retry-After 존중, 지수 백오프, 지터, 상한까지 규약이 확정돼 있다.
- 성숙도: urllib3 stable 공식 레퍼런스에서 상수·기본값 직접 확인.
- **훔칠 메커니즘**: 베낄 상수와 공식: (1) RETRY_AFTER_STATUS_CODES = {413, 429, 503} — 이 세 코드에서만 Retry-After 존중. (2) 백오프 = backoff_factor * 2**(이전 재시도 횟수), 두 번째 시도부터 적용. (3) DEFAULT_BACKOFF_MAX = 120초. (4) backoff_jitter로 0~jitter 균등난수를 더해 thundering herd 방지. (5) Retry-After는 초(정수)와 HTTP-date 두 형식 → 'int 시도 → 실패 시 email.utils.parsedate_tz로 날짜 파싱 후 현재시각 차감' 2단. (6) status_forcelist 기본값은 None(=상태코드 재시도 꺼짐) — '기본값이 알아서 429를 재시도해 주겠지'는 틀렸고 이게 백오프 코드가 죽어 있는 흔한 원인.
- 겨냥 약점: `ROT-1` · 이식비용 **low** · confidence **high**
- 이식 노트: 'requests를 쓰면 urllib3는 이미 있다'는 전제는 우리 스택(curl_cffi)에선 미확인이다. 확인되면 HTTPAdapter(max_retries=Retry(...)) mount가 가장 짧고, 아니면 위 상수 6개를 stdlib(time/random/email.utils)로 15줄 재현 — 어느 쪽이든 새 의존성 0. tenacity는 새 의존성인 데다 HTTP 규약(Retry-After·413/429/503)을 스스로 모르므로 이 용도에선 열위. 단 searxng의 '엔진 격리'가 상위 정책이고 이건 그 아래 계층이라는 순서를 지킬 것.

### edgi-govdata-archiving/wayback + Wayback CDX Server API / Memento

- URL: https://wayback.readthedocs.io/en/stable/usage.html
- 정체: Internet Archive 클라이언트. '요청한 시점'과 '실제로 받은 스냅샷 시점'을 타입 수준에서 분리해 다루는 API 설계.
- 성숙도: 공식 문서 stable(0.5.x)에서 Memento/CdxRecord 필드와 exact/target_window 확인, CDX·Availability·Memento 프로토콜 준수 확인.
- **훔칠 메커니즘**: COV-2의 정답 구조가 API에 그대로 있다. (1) Memento.timestamp는 실제 캡처 시각(UTC)이고 요청 시각과 별개 필드 — 우리도 requested_ts와 actual_ts를 반드시 분리 저장. (2) get_memento(exact=True)가 기본값: 정확히 일치하지 않으면 조용히 근사값을 주는 게 아니라 에러. 근사 허용은 exact=False를 명시할 때만 열리고 그때도 target_window(기본 86400초) 안의 것만 — 허용 오차 창을 상수로 박고 넘으면 실패. (3) 응답의 Memento-Datetime 헤더가 실제 캡처 시각, X-Archive-Orig-*에 원본 서버 헤더 보존. Availability API의 archived_snapshots.closest를 검증 없이 쓰면 몇 년 떨어진 스냅샷을 인용하게 된다. (4) CDX API는 timestamp·statuscode·mimetype·digest·length를 함께 줘서 digest로 동일 콘텐츠 판정, statuscode로 200 아닌 캡처 사전 배제가 가능. (5) 스냅샷 URL에 id_ 접미사(/web/<ts>id_/<url>)를 붙이면 배너·리라이팅 없는 원본 바이트.
- 겨냥 약점: `COV-2` · 이식비용 **low** · confidence **high**
- 이식 노트: 라이브러리 도입 없이 규칙만 이식(stdlib datetime만). ①CDX API로 statuscode=200 필터 + timestamp·digest 확보 ②abs(actual_ts - requested_ts) > 허용창(조사 대상 기간 기준, 예 30일)이면 인용 불가로 강등하고 실제 시점을 증거에 병기 ③본문은 id_ URL로 ④응답 Memento-Datetime으로 재확인(CDX와 불일치 시 실패). 허용창은 gates.json knob.

### adbar/trafilatura (settings.cfg, favor_precision)

- URL: https://github.com/adbar/trafilatura
- 정체: 웹 본문 추출기(이미 우리 HARD 의존성). '추출은 됐는데 그게 본문인가'를 숫자 임계값으로 판정하는 설정이 파일 하나에 모여 있다.
- 성숙도: master 브랜치 settings.cfg 직접 확인(값 그대로 인용), 활발히 유지보수 중.
- **훔칠 메커니즘**: 임계값 세트: MIN_EXTRACTED_SIZE=250(추출 본문 250자 미만이면 실패 — 쿠키 동의창·페이월 티저가 여기서 걸린다), MIN_DUPLCHECK_SIZE=100 + MAX_REPETITIONS=2(100자 이상 블록을 LRU로 세어 2회 초과 반복이면 보일러플레이트로 폐기 → site-wide 템플릿/피드 반복 텍스트를 걷어내며 FP-1에 직접 대응), DOWNLOAD_TIMEOUT=30, MAX_REDIRECTS=2. 모드 선택 favor_precision(보일러플레이트를 공격적으로 제거 — '가짜 본문 통과'가 치명적인 우리 쪽) vs favor_recall. 임계 미달이면 None을 돌려주는 계약이라 성공/실패가 호출부에서 명확.
- 겨냥 약점: `FP-3, FP-1` · 이식비용 **low** · confidence **high**
- 이식 노트: 이미 쓰고 있으므로 extract(..., favor_precision=True) 스위치 하나 + 반환 None을 실패로 취급 = 사실상 0코드. 새 의존성 0. 가장 중요한 지적: 현재 '장문이면 ok' 판정이 원시 HTML 길이 기준이라 무력하다 — 게이트를 반드시 '추출 후 본문 길이'로 옮길 것. 이 한 줄이 FP-3 수정의 8할이다.

### schema.org isAccessibleForFree / hasPart+cssSelector (Google 페이월 구조화데이터 규약)

- URL: https://developers.google.com/search/docs/appearance/structured-data/paywalled-content
- 정체: 페이월 사업자가 '여기부터 유료'를 선언하는 표준 마크업. 추측이 아니라 사이트의 선언을 읽는 판정.
- 성숙도: Google Search Central 공식 현행 규약, NewsArticle·CreativeWork 양쪽 지원, JSON-LD·microdata 허용.
- **훔칠 메커니즘**: (a) JSON-LD를 파싱해 isAccessibleForFree가 false면 유료 문서. (b) hasPart 배열의 WebPageElement 중 isAccessibleForFree:false 항목의 cssSelector가 우리가 추출한 본문 영역과 겹치면 우리가 받은 건 티저. 규약상 둘은 쌍으로 있어야 유효하므로 함께 확인하면 오탐이 거의 없다. 실무 함정도 문서화됨 — cssSelector가 실제 class와 어긋나는 게 가장 흔한 구현 오류라 선택자 매칭 실패를 '페이월 아님'으로 해석하면 안 되고 isAccessibleForFree:false 단독으로도 강등 신호로 써야 한다. 보조 신호: article:content_tier, 본문 말미 절단 패턴(마침표 없이 끊김 + '구독'/'Subscribe'/'로그인하고 계속' 근접).
- 겨냥 약점: `FP-3` · 이식비용 **low** · confidence **high**
- 이식 노트: 새 의존성 0 — json + 기존 파서로 <script type="application/ld+json">를 긁어 파싱, 20줄 이내. @graph로 감싸는 사이트가 많아 재귀 탐색 필요. 판정은 '즉시 폐기'보다 '유료-티저' 라벨링 + 인용 시 경고가 낫다(제목·발행일 메타데이터는 여전히 유효). 한국 언론사는 채택률이 낮을 수 있으니 trafilatura 250자 게이트와 병행해야 커버된다.

### pyeventsourcing/eventsourcing

- URL: https://github.com/pyeventsourcing/eventsourcing
- 정체: 파이썬 이벤트소싱 라이브러리. 훔칠 건 라이브러리가 아니라 규약 두 개.
- 성숙도: star 1,682, 최근 푸시 2026-07-27, 9.x 장기 유지.
- **훔칠 메커니즘**: (1) 낙관적 동시성 제어 — 이벤트마다 (originator_id, originator_version)을 붙이고 저장소에 UNIQUE 제약. 동시 두 라이터가 같은 버전을 쓰면 IntegrityError로 '충돌'이 되고 재읽기 후 재시도한다(잠금 없이 lost-update 소멸, 우리 대장은 gate별 시퀀스가 자연스러운 originator). (2) 스냅샷 — 현재 status()/_gate_states()/_update_metadata()는 매 호출마다 전 대장을 재생한다. N 이벤트마다 파생상태(게이트별 최신 checkpoint, fact_hashes)를 스냅샷 행으로 굳히고 이후 이벤트만 재생하면 O(N)→O(변경분).
- 겨냥 약점: `OPS-1, SC-7, SC-1` · 이식비용 **low** · confidence **high**
- 이식 노트: 규약만 이식하면 새 의존성 0 — 컬럼 2개 + UNIQUE 제약 + 스냅샷 레코드 kind 1개. 라이브러리 도입은 애그리게이트/애플리케이션 클래스 구조를 강요해 이 스킬 규모엔 과함. 윈도우 특이사항 없음. 위 SQLite 후보를 채택하면 UNIQUE 제약이 그 위에 그대로 얹힌다.

### tox-dev/filelock (대안: wolph/portalocker, 최종 대안: stdlib msvcrt)

- URL: https://github.com/tox-dev/filelock
- 정체: 플랫폼 독립 프로세스 간 파일 잠금. 대장을 JSONL로 유지할 경우의 최소 처방.
- 성숙도: filelock star 973 최근 푸시 2026-08-05, portalocker star 326. 둘 다 활발.
- **훔칠 메커니즘**: 락 대상은 대장 파일이 아니라 사이드카 .lock 파일이고, 프로세스가 죽으면 OS가 핸들을 닫으며 자동 해제된다 — 디렉터리/마커 파일 방식의 stale lock 문제가 없다. 윈도우는 msvcrt.locking(또는 LockFileEx)이라 유닉스의 권고적 락과 달리 강제 락이다(락을 모르는 제3의 프로세스도 막힌다). 적용점은 _append() 전체(읽기+병합+쓰기)를 한 락 안에 넣어 read-modify-write를 원자화하는 것.
- 겨냥 약점: `OPS-1` · 이식비용 **low** · confidence **high**
- 이식 노트: 새 의존성 추가는 '유닉스에서도 같은 코드로 돌려야 한다'가 확정될 때만 — 우리는 Windows 단일이므로 라이터가 배타락 하나만 필요하다면 msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1) 15줄로 stdlib에서 끝난다(권장). 윈도우 함정 기록: msvcrt 백엔드에는 공유(read) 락이 사실상 없고(_LK_NBRLCK == _LK_NBLCK), msvcrt 락은 shutil.copyfile 같은 외부 읽기까지 막는다(LockFileEx 공유락은 안 막음). 진짜 공유락이 필요해지면 그때 pywin32/filelock 재검토.

### O_APPEND 원자성의 실제 조건 (+ os.replace의 윈도우 함정)

- URL: https://www.notthewizard.com/2014/06/17/are-files-appends-really-atomic/
- 정체: 'append는 원자적이니 잠금 없이 여러 프로세스가 한 줄씩 써도 된다'는 통념의 실측 반례. 결론은 '윈도우에서는 그 전제가 깨진다'.
- 성숙도: 직접 확인(2026-08): 페이지 실존, Oz Solomon 2014-06-17, 윈도우 1024바이트 한계와 1025바이트에서 406건 손상 실측, 코멘트에 Win32 vs MS CRT 차이 정리. 다루는 계약은 이후 변하지 않음.
- **훔칠 메커니즘**: POSIX는 O_APPEND fd의 '오프셋 이동+write'가 원자적 단계라고만 보장하고 실측상 리눅스는 4096바이트까지 안전(4097에서 손상). 윈도우는 네이티브 CreateFile+FILE_APPEND_DATA만 이 보장을 주고, MS CRT의 POSIX open(O_APPEND)(=파이썬 open(path,'a')가 타는 경로)은 seek-후-write라 원자적이지 않다 — 실측 손상이 1025바이트부터 시작(1024까지는 무손상). 규칙: (a) 대장 레코드는 JSON 한 줄로 한 번의 write, 절대 전량 재작성 금지(O(N²) 제거), (b) 윈도우에서는 이 append를 반드시 락으로 감쌀 것 — 우리 레코드는 1KB를 쉽게 넘는다, (c) 리더는 마지막 줄이 잘려 있을 수 있다고 가정하고 JSONDecodeError면 그 줄만 버린다(JSONL의 crash 반경은 최대 1줄).
- 겨냥 약점: `SC-7, OPS-1` · 이식비용 **low** · confidence **high**
- 이식 노트: 새 의존성 0. 함께 반드시 손볼 것: 현 코드의 temp+os.replace 패턴(run_ledger.py:115 _write_json_atomic, facts_db _write_jsonl_atomic)은 윈도우에서 MoveFileEx로 내려가는데 대상 파일을 Defender나 다른 리더가 열고 있으면 PermissionError로 실패한다 → 지수 백오프 3~5회 재시도 래퍼 필요. 윈도우엔 디렉터리 fsync가 없으므로 '리네임 자체의 내구성'은 파일 fsync로만 근사된다는 점을 주석으로 남길 것.

### Bazel Skyframe — change pruning + action key(Merkle)

- URL: https://bazel.build/reference/skyframe
- 정체: 빌드 그래프의 각 노드를 '입력 다이제스트 + 커맨드'의 해시로 키잉하고, 재계산 결과가 이전과 같으면 하위 무효화를 되돌리는 증분 평가 엔진.
- 성숙도: Bazel 코어, 구글 내부 수년 실전. 개념 재구현 대상이지 도입 대상 아님.
- **훔칠 메커니즘**: (1) action key = (선언된 입력들의 content digest + 실행 커맨드 + salt)의 해시 — mtime이 아니라 내용 해시라 '파일을 건드렸지만 바이트가 그대로'면 하위가 무효화되지 않는다. (2) change pruning(early cutoff) — 무효화돼 재계산했는데 새 값이 옛 값과 같으면 그 노드 때문에 무효화됐던 하위를 되살린다. 우리 적용: run_ledger.py가 이미 fact 단위 content-hash(_fact_hashes, _canon_sha)를 갖고 있어 절반은 되어 있고, 빠진 것은 '검증 결과 노드'다 — verify 결과를 key = sha256(fact_sha + verifier_version + rule_set_sha)로 캐싱하면 fact가 안 변했으면 재검증 자체를 건너뛴다. fact의 서술만 바뀌고 수치·출처 다이제스트가 그대로면 보고서 섹션 재생성을 early cutoff로 잘라낸다.
- 겨냥 약점: `SC-1, SC-8` · 이식비용 **low** · confidence **high**
- 이식 노트: 순수 stdlib(hashlib + dict), 새 의존성 0. 캐시는 SQLite 테이블 한 개(verify_cache(key PRIMARY KEY, verdict, evidence_ids, at))면 충분. 주의 — 캐시 키에 검증 규칙 버전(rule_set_sha)을 반드시 섞을 것. 빠지면 '규칙을 고쳤는데 옛 판정이 살아있는' 최악의 침묵 버그가 된다.

### rapidfuzz/RapidFuzz (+ 결정적 blocking key)

- URL: https://github.com/rapidfuzz/RapidFuzz
- 정체: 고속 퍼지 문자열 매칭. merge_evidence(사실 병합)를 blocking + 유사도 2단으로 짜는 설계 참조.
- 성숙도: star 4,054, 최근 푸시 2026-08-03, BSD, 윈도우 사전 빌드 휠 제공.
- **훔칠 메커니즘**: (1) blocking — 결정적 키로 후보를 자른다. 우리는 이미 make_claim_key(context)가 있으므로 (정규화 대상명 + 지표 + 단위 + 기간)을 블록 키로 쓰면 비교쌍이 O(N²)→블록 내부로 줄어든다. (2) 블록 안에서만 유사도 스코어링(token_set_ratio 계열)으로 같은 사실의 표기 흔들림을 찾고, 임계 이상 쌍을 union-find로 클러스터링해 대표 fact 1건으로 병합 — 병합 규칙은 '출처 등급 최상위를 값으로 채택, evidence_ids는 합집합, 상충 시 conflict 레코드 append'. RapidFuzz는 레코드 링키지 시스템이 아니라 blocking을 해주지 않는다는 점이 핵심 — blocking은 우리가 claim_key로 공급한다.
- 겨냥 약점: `SC-2` · 이식비용 **low** · confidence **high**
- 이식 노트: 새 의존성 추가 금지 원칙에 따라 라이브러리는 넣지 않는다 → 조사 1건의 fact가 수백~수천이면 stdlib difflib.SequenceMatcher + 같은 blocking으로 충분(의존성 0). 느려지면 그때 rapidfuzz(휠이라 윈도우 설치는 무난)로 교체. dedupe/splink는 pandas/numpy/DuckDB를 끌고 오고 라벨링 데이터도 없어 확률모델 학습이 불가능 — 탈락. 병합 규칙(대표값 선택·conflict append)이 코드보다 중요한 부분이다.

### princeton-nlp/ALCE

- URL: https://github.com/princeton-nlp/ALCE
- 정체: 인용 품질을 citation recall / citation precision 두 지표로 자동 채점하는 EMNLP 2023 벤치마크+코드.
- 성숙도: EMNLP 2023, princeton-nlp 공식, arXiv 2305.14627. 후속 연구(VeriCite, CiteEval, ExpertQA)가 전부 이 지표를 기준선으로 인용 — 사실상 표준.
- **훔칠 메커니즘**: 두 지표 정의가 훔칠 알고리즘 그 자체. citation recall: 문장 s와 그 문장이 단 인용들의 합집합을 premise로 두고 s를 hypothesis로 함의 판정. citation precision: 각 인용 ci에 대해 ablation(제거) 테스트 — (a) ci 단독이 s를 함의하지 않고 (b) ci를 뺀 나머지가 여전히 s를 함의하면 ci는 불필요한 인용(=오탐)으로 감점. 즉 '인용이 붙어 있다'가 아니라 '인용이 필요하고 충분한가'를 기계적으로 가른다.
- 겨냥 약점: `EV-9 (+ 팀리드 전건 재검증의 채점 축)` · 이식비용 **low** · confidence **high**
- 이식 노트: 판정기 TRUE(T5-11B)는 들여올 수 없지만 ablation 프로토콜은 모델 무관이다. 팀리드가 이미 원문을 재열람하므로 판정기를 팀리드 LLM 호출로 치환하면 그대로 성립: 사실 f에 대해 (1) 인용 전체 → 지지?(recall), (2) 각 인용 하나씩 빼고 → 여전히 지지?(precision). EV-9의 '값일치 폴백이 태그 귀속을 붕괴시킨다'는 문제는 precision으로 정확히 잡힌다 — 우연히 값이 일치해 붙은 태그는 ablation에서 '빼도 나머지가 지지'로 드러난다. 새 의존성 0, 비용은 LLM 호출 수가 인용 개수 배로 늘어나는 것뿐이라 '분쟁 사실'에만 선택 적용 권장.

### explodinggradients/ragas + confident-ai/deepeval — Faithfulness (2건 병합)

- URL: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/ , https://deepeval.com/docs/metrics-faithfulness
- 정체: 응답을 statement/claim 단위로 쪼개 각각이 context에서 추론 가능한지 판정하는 같은 계열의 두 구현. ragas는 '판정기 교체 가능성', deepeval은 '3값 verdict'를 기여 — 프로토콜이 동일해 병합.
- 성숙도: ragas = RAG 평가 사실상 표준, 문서 안정판 유지. deepeval = 오픈소스 평가 프레임워크, faithfulness.py + template.py 구현 공개. HHEM-2.1-Open은 Vectara 공개 모델.
- **훔칠 메커니즘**: 공통 3단계: 분해 → 각 항목 판정 → 집계. (a) ragas: 같은 프로토콜에서 판정기만 LLM ↔ HHEM-2.1-Open(T5 크로스인코더)로 스왑된다 — '분해 규약'과 '판정기'가 인터페이스로 분리 설계돼 있다는 게 요점. (b) deepeval: 판정이 이진이 아니라 yes(지지)/no(모순)/idk(문맥에 언급 없음) 3값이고 점수 = (yes+idk)/total. 프롬프트 규약상 'no'는 컨텍스트가 직접 모순될 때만 쓰고 사전지식은 절대 동원 금지 → '모순됨'과 '확인 불가'를 구조적으로 분리한다.
- 겨냥 약점: `SC-6 (+ 팀리드 전건 재검증의 비용 구조)` · 이식비용 **low** · confidence **high**
- 이식 노트: 두 라이브러리 다 도입 금지 — HHEM 로컬 구동은 torch+transformers라는 무거운 새 의존성이고 무의존 코어 원칙과 정면 충돌한다. 훔칠 건 3값 심각도 분류 하나: 지금 수리 루프가 안 끝나는 이유는 실패가 전부 같은 무게이기 때문이다. no(모순) = 하드 블로커, 사실 폐기 또는 재수집 필수 / idk(원문에 없음) = 소프트, 출처 교체 1회 시도 후 미해결이면 보고서에서 드롭 / yes = 통과. 이러면 무한 반복 가능한 클래스가 idk 하나로 줄고 거기에만 시도 상한 1~2를 걸면 루프가 원리적으로 종료된다. 아키텍처만 훔치는 쪽(분해 규약 ↔ 판정기 인터페이스 분리)도 함께 채택하되 판정기는 당분간 팀리드 LLM 하나만.

### Raldir/FEVEROUS (+ Raldir/TabVer)

- URL: https://github.com/Raldir/FEVEROUS
- 정체: 증거 단위를 '문장'뿐 아니라 '표의 개별 셀'로 정의한 팩트검증 데이터셋/베이스라인(87,026 claims). TabVer는 표 위 숫자·산술까지 다루는 후속.
- 성숙도: NeurIPS 2021 Datasets&Benchmarks, EMNLP2021 FEVER 워크숍 공유과제. 베이스라인의 증거+판정 동시 정답률 18%(이 문제 자체가 어렵다는 증거).
- **훔칠 메커니즘**: 표를 텍스트로 평탄화하지 않고 셀 좌표를 증거 ID로 승격한다 — 표는 셀 c_{i,j} + caption q로 모델링되고 증거 하나가 '이 문서의 이 표의 이 셀'로 지정된다. 결정적인 건 셀 컨텍스트 규칙: 셀의 문맥 = 가장 가까운 행 헤더 + 열 헤더, 그 헤더 바로 앞도 헤더면 그것까지 포함. 통계상 샘플당 평균 문장 1.4개 + 셀 3.3개가 증거로 필요 — 표 증거가 소수가 아니라 다수다.
- 겨냥 약점: `EV-9` · 이식비용 **low** · confidence **high**
- 이식 노트: 모델·데이터 불필요, 표현(representation)만 훔친다. 우리 문제는 표에서 직접 결박이 막히자('|' 건너뛰기 금지) 세그먼트 전체 값일치 폴백으로 도망쳐 태그 귀속이 무너지는 것(verify_facts.py line 291). 해법: GFM 표를 파싱해 각 숫자를 (표 idx, 행 idx, 열 idx)로 주소화하고 결박 후보를 같은 행 또는 같은 열의 태그 셀로만 제한 + 판정 문맥에 행헤더·열헤더를 자동 첨부 → '세그먼트 내 아무 값이나 일치'라는 붕괴 경로가 사라진다. GFM 표 파싱은 stdlib re 20줄. TabVer 쪽은 '합계=부분합, 비율=분자/분모' 산술 정합성 검사를 시사 — _vals()/_qty() 단위 정규화(line 133~220)에 붙이면 값일치 폴백보다 훨씬 강한 신호.

### theupdateframework/python-tuf

- URL: https://github.com/theupdateframework/python-tuf
- 정체: TUF 레퍼런스 구현. 메타데이터가 메타데이터를 가리키는 구조에서 롤백·프리즈 공격을 막는 규약.
- 성숙도: star 1.7k, CNCF 졸업 프로젝트 TUF의 레퍼런스 구현. 다만 원 조사에서 snapshot/timestamp 세부는 스펙 원문 미확인(통설 기준) — 이식 전 TUF 스펙 §5 확인 권장.
- **훔칠 메커니즘**: targets ← snapshot ← timestamp 역할 분리. 각 메타는 정수 version과 expires를 갖고 클라이언트 규칙은 두 줄 — (1) 새 메타의 version이 신뢰 중인 version보다 작으면 무조건 거부(롤백 방지), (2) expires 지났으면 거부(프리즈 방지). 우리 직역: manifest.json에 monotonic version + built_at/expires + prev_manifest_sha256를 넣고 verify는 대장의 last_seen_version 이하 매니페스트를 거부. 진짜 교훈은 '자기참조 스냅샷 파일 하나는 원리상 자기를 못 지킨다 — 바깥 앵커(서명키/외부 checkpoint/추가전용 대장)가 반드시 하나 필요'.
- 겨냥 약점: `EV-8` · 이식비용 **low** · confidence **medium**
- 이식 노트: python-tuf 자체는 절대 넣지 말 것(securesystemslib+cryptography를 끌고 옴). version+expires+prev_hash 필드 3개와 거부 규칙 2줄만 이식, 앵커는 기존 run_ledger에 last_seen_version append-only. 오프라인 100%, 새 의존성 0.

### Aider-AI/aider (--auto-test/--lint-cmd) + SWE-bench / Terminal-Bench 하네스

- URL: https://aider.chat/docs/usage/lint-test.html
- 정체: 에이전트가 편집할 때마다 하네스가 린터/테스트를 직접 실행하고 종료 상태를 되먹인다. 벤치마크는 에이전트 주장 대신 verifier 실행 결과로 성공을 판정한다.
- 성숙도: aider star 3만+, --auto-test/--test-cmd/--lint-cmd 공식 옵션(기본 auto-test=False). SWE-bench/Terminal-Bench는 표준 평가 하네스이나 인용된 '89개 태스크' 등 세부 수치는 미확인.
- **훔칠 메커니즘**: 에이전트 하네스판 proof-of-work. (1) 검증 커맨드가 설정으로 미리 고정되고(에이전트가 그때그때 고르지 않음) 편집 이벤트에 자동 결박. (2) 판정은 하네스가 소유 — 에이전트가 성공을 보고해도 상태를 관측하는 건 하네스. (3) 벤치마크 쪽은 더 엄격: patch를 격리 컨테이너에 적용하고 에이전트가 볼 수 없는 테스트로 이진 신호를 얻는다(테스트를 고쳐 통과시키는 보상 해킹 차단).
- 겨냥 약점: `GS-1, GS-2` · 이식비용 **low** · confidence **medium**
- 이식 노트: 게이트 정의에 verify_cmd를 필수 필드로 두고 하네스가 subprocess로 직접 실행, PASS는 returncode==0에서만 파생(에이전트 문자열 무시). '에이전트가 볼 수 없는 검사'는 검증 스크립트를 수정 금지 경로에 두고 실행 전 해시 대조로 근사. subprocess/hashlib만, 새 의존성 0.

### epi052/feroxbuster (--filter-similar-to) + OJ/gobuster (wildcard detection)

- URL: https://epi052.github.io/feroxbuster-docs/docs/examples/filter-similar/
- 정체: 디렉터리 브루트포서. soft-404/wildcard 판정 로직이 가장 실전적으로 정제된 도구들.
- 성숙도: feroxbuster 공식 문서에서 --filter-similar-to 동작 확인. 다만 'SSDeep→2.8.0 Simhash 교체, 컷 95%'라는 세부는 원 조사에서 미확인 — 컷 값은 우리가 실측 튜닝할 knob이라 실질 영향은 없음.
- **훔칠 메커니즘**: 베이스라인 프로브 + 퍼지 해시 비교 2단. (1) 대상과 같은 오리진/디렉터리 아래 존재할 리 없는 랜덤 경로(/<32자 난수>)를 1회 GET → 200이 오면 soft-404 사이트로 확정하고 그 본문을 '없음 템플릿'으로 저장. (2) 실제 응답 본문을 같은 방식으로 해시해 베이스라인과 비교, 유사도 ≥95%면 soft-404로 폐기. (3) 보조 필터: 상태코드·본문 길이·단어 수가 베이스라인과 같으면 즉시 탈락. (4) 200인데 본문에 'Not Found'류 문구가 있으면 탈락. FP-1의 site-wide 피드 오인도 같은 도구로 잡힌다 — 기사 URL 응답과 피드/템플릿 응답의 유사도가 높으면 본문이 아니다.
- 겨냥 약점: `FP-3, FP-1` · 이식비용 **low** · confidence **medium**
- 이식 노트: 새 의존성 0. simhash 자작(hashlib.blake2b + 단어 shingle, 20줄)보다 더 게으른 정답은 stdlib difflib.SequenceMatcher(a,b).quick_ratio() ≥0.95이고 본문을 앞 4KB로 자르면 비용도 무시할 만하다 → 원본 medium을 low로 조정. 진짜 비용은 코드가 아니라 '요청 1회 추가(베이스라인 프로브)'이며 오리진당 1회 캐시로 상각. 유사도 컷은 gates.json 노출 knob으로.

### searxng/searxng (searx/exceptions.py, engines/duckduckgo.py)

- URL: https://docs.searxng.org/src/searx.exceptions.html
- 정체: 메타서치 엔진. 수십 개 엔진의 429·CAPTCHA·봇차단을 상시로 맞으며 운영하는 엔진별 정지(suspend) 정책.
- 성숙도: 공식 문서 활발히 유지보수(2026.8 빌드), duckduckgo.py 소스 직접 확인. suspended_times 기본값 세부는 settings.yml 원문 재확인 권장.
- **훔칠 메커니즘**: (1) 차단을 '결과 없음'과 분리하는 타입 체계: SearxEngineCaptchaException(기본 suspended_time 86400초), SearxEngineTooManyRequestsException(기본 3600초). 즉 429/CAPTCHA는 재시도가 아니라 '엔진 격리'로 처리하고 그 사이 다른 소스로 라우팅한다 — ROT-1 백오프 데드코드 자리에 그대로 들어갈 정책. (2) DDG 200-차단 판별: 본문에 //form[@id='challenge-form']이 있으면 CAPTCHA. DDG는 CAPTCHA로 리다이렉트하지 않고 200 본문에 다이얼로그를 넣기 때문에 본문 검사로만 잡힌다 — 이게 '200인데 결과 0건' 오인의 원인. 추가 마커 'DDG.deep.anomalyDetectionBlock'. (3) vqd 토큰 부재 자체를 CAPTCHA 예외로 승격.
- 겨냥 약점: `ROT-1` · 이식비용 **low** · confidence **medium**
- 이식 노트: 새 의존성 0. 두 가지만 — ①검색 결과 파싱 전에 차단 마커 검사를 게이트로 두고(challenge-form id, anomalyDetectionBlock) 걸리면 0건이 아니라 blocked 예외 ②엔진별 suspend 타임스탬프 dict를 프로세스 메모리에 두고 429=1시간·CAPTCHA=1일 스킵. 지수 백오프를 '고치는' 게 아니라 '엔진 격리'로 바꾸는 게 요점(재시도해도 안 풀린다). 정지 시간은 상수 하드코딩 말고 설정으로.

### Cited but Not Verified: Parsing and Evaluating Source Attribution in LLM Deep Research Agents (arXiv 2605.06635)

- URL: https://arxiv.org/abs/2605.06635
- 정체: 딥리서치 보고서에서 (주장 span ↔ 인용 id) 쌍을 LLM 없이 결정론적으로 뽑고 3단계(링크 생존/주제 관련성/팩트체크)로 채점하는 파이프라인. 우리 verify_facts.py와 정확히 같은 자리를 다루되 결박 방식이 다르다.
- 성숙도: 직접 확인(2026-08): arXiv 2605.06635 실존, 2026-05-07 제출, 제목 일치, 저자 6인. 다만 프리프린트이고 공개 코드 저장소는 확인 안 됨 — 알고리즘 설명만 보고 우리가 구현해야 한다.
- **훔칠 메커니즘**: Algorithm 1 = 4단계: (1) canonicalization(공백/개행 정규화) → (2) fenced code block 제거(오탐 차단) → (3) Markdown AST 구축, 인용 노드를 [1] / [^note] / [text](url) / <url> / [1-3] 범위표기까지 다형식 인식 → (4) backward attribution: 문단 끝에 인용이 오면 그 앞의 '인용 없는 문장 전부'에 소급 적용. 산출물은 중복제거된 URL 목록 + citation id가 붙은 text span 리스트. 발견된 실패모드가 우리에게 직결 — 링크 생존 94%+, 관련성 80%+인데 팩트체크는 39~77%(표층 지표가 사실오류를 가린다), 툴콜을 2→150으로 늘리면 Fact Check 정확도가 평균 42% 하락.
- 겨냥 약점: `EV-7, EV-9` · 이식비용 **low** · confidence **medium**
- 이식 노트: 핵심인 AST 파서는 순수 파이썬으로 이식 가능. 현재 verify_facts.py의 _bind_pairs()는 '숫자↔태그 gap ≤20자'라는 평문 거리 휴리스틱으로 결박하고(line 222~234) 표에서는 행 단위 값일치 폴백으로 도망친다(line 291). AST로 바꾸면 결박이 거리가 아니라 구조(node containment)가 된다 — 문단 노드/표 셀 노드 안에서만 결박, 셀 경계가 노드 경계라 애초에 새지 않음. markdown-it-py/mistune은 넣지 말 것: 우리는 GFM 표만 다루므로 기존 split_segments를 노드 트리로 승격시키면 stdlib re로 무의존 가능. backward attribution 규칙은 '앞뒤 20자'를 대체할 명시 규약으로 그대로 채택.

### stanfordnlp/dspy — Assertions (dspy.Assert / dspy.Suggest)

- URL: https://dspy.ai/learn/programming/7-assertions/
- 정체: LLM 파이프라인 제약 위반 시 해당 모듈로 되돌아가 오류 메시지를 프롬프트에 주입해 재시도하되 재시도 횟수에 명시 상한을 두는 메커니즘.
- 성숙도: 직접 확인(2026-08): 해당 문서 페이지에 'Assertions are deprecated and NOT supported. Please use dspy.Refine instead' 명시. 규약(하드/소프트 + max_backtracks=2 + 실패 컨텍스트 주입) 자체는 여전히 유효하지만 API 인용은 폐기된 것이므로 '개념만 참조'로 취급할 것.
- **훔칠 메커니즘**: 제약을 두 종류로 나눈다. dspy.Assert = max_backtracks를 넘겨도 못 고치면 AssertionError로 파이프라인 정지(하드 게이트). dspy.Suggest = 같은 백트래킹을 쓰되 상한 초과 시 '지속 실패'로 로깅만 하고 실행은 계속(소프트 게이트). 기본 max_backtracks=2. 재시도 시 직전 실패 출력 + 오류 메시지를 프롬프트에 주입해 같은 실수를 반복하지 않게 한다(맹목 재시도가 아님).
- 겨냥 약점: `SC-6` · 이식비용 **low** · confidence **medium**
- 이식 노트: DSPy 도입 불필요 — 훔칠 건 규약 3개뿐: (1) 검증 실패를 하드/소프트 두 등급으로 선언, (2) 공통 상한 max_backtracks 기본 2, (3) 재시도 프롬프트에 '직전 실패 출력 + 실패 사유'를 반드시 실어 보낼 것. verify_facts.py는 이미 blockers/warnings로 등급을 구분하므로 없는 건 시도 카운터와 상한, 그리고 상한 초과 시의 정의된 종착 상태(하드=중단, 소프트=경고 달고 진행)다. dict 하나(fact_id → attempt_count)로 끝.

### langchain-ai/open_deep_research (+ local-deep-researcher, gpt-researcher)

- URL: https://github.com/langchain-ai/open_deep_research
- 정체: supervisor/researcher 2계층 딥리서치 에이전트. 종료 조건을 '에이전트 자기선언 + 하드캡 + 무동작' 3중으로 걸어 수렴 미달을 원리적으로 막는다.
- 성숙도: LangChain 공식 저장소, 전용 강좌·벤치마크 동봉. 3개 독립 구현이 같은 패턴에 수렴한 게 신뢰 근거이나 인용된 상수(기본 6, 0.42 등)는 버전별로 바뀔 수 있어 원문 재확인 권장.
- **훔칠 메커니즘**: supervisor 루프 종료: if exceeded_allowed_iterations or no_tool_calls or research_complete_tool_call. 각각 (a) research_iterations > max_researcher_iterations(기본 6) = 하드캡, (b) supervisor가 툴콜 없이 응답 = 암묵 종료, (c) ResearchComplete 전용 툴 명시 호출 = 자기선언 종료. 즉 '충분한가?' 판단을 자연어 자기평가가 아니라 툴 호출이라는 이산 이벤트로 만들었다. 그 외 예산: max_concurrent_research_units=5, max_react_tool_calls=10, max_content_length=50k자. 자매 구현이 같은 결론에 수렴 — local-deep-researcher는 단일 하드캡 + 소스 중복 제거, gpt-researcher는 MAX_ITERATIONS=3/DEPTH=2/SIMILARITY_THRESHOLD=0.42, dzhng/deep-research는 depth가 0이면 무조건 종료.
- 겨냥 약점: `SC-3, SC-6` · 이식비용 **low** · confidence **medium**
- 이식 노트: 규약 이식만. (1) 확장 라운드마다 카운터를 올리고 상한 초과 시 무조건 종료 — SC-3 미수렴은 하드캡 부재가 절반이다. (2) '조사 충분' 판정을 서술형 자기평가가 아니라 명시 신호로 이산화(서브에이전트가 대장에 research_complete 레코드를 쓴다). (3) 수동 dedup은 임베딩 없이 stdlib difflib.SequenceMatcher + 정규화된 (metric, 단위, 값, 기준연도) 키 완전일치 2단계로 충분 — 새 의존성 0. 실제 수렴 판정은 '이번 라운드 신규 unique 사실 수 / 전체 수집 수'가 임계 이하면 종료(신규성 포화)로 두고 하드캡은 안전망으로만 남길 것.

### webrecorder/wacz-auth-spec + webrecorder/py-wacz

- URL: https://github.com/webrecorder/wacz-auth-spec/blob/main/spec.md , https://github.com/webrecorder/py-wacz
- 정체: 웹아카이브 번들에 '무엇을 봉인했나'와 '누가 언제 봉인했나'를 분리해 서명하는 규격. 우리 manifest.json이 하려다 만 것의 완성형.
- 성숙도: webrecorder 공식 스펙(specs.webrecorder.net/wacz-auth/0.1.0 퍼블리시), py-wacz는 순수 파이썬. 버전 0.1.0으로 스펙 자체는 초기 단계.
- **훔칠 메커니즘**: 2단 구조. datapackage.json = 번들 내 모든 리소스의 {path, hash, bytes} 목록. datapackage-digest.json = 그 목록의 hash + signedData{hash, signature, publicKey/도메인 인증서, created, (선택) RFC3161 타임스탬프}. 검증 순서 ①리소스 재해싱→목록 대조 ②목록 재해싱→digest 대조 ③서명 검증 ④created를 타임스탬프 토큰으로 교차확인. 핵심 설계는 '봉인 목록'과 '봉인 증서'를 다른 파일로 갈라놓은 것 — 목록은 자주 바뀌지만 증서는 키 없이 재발급 불가라 재봉인=세탁 경로가 끊긴다.
- 겨냥 약점: `EV-8` · 이식비용 **medium** · confidence **high**
- 이식 노트: 구조 이식(manifest.json + manifest.sig.json 분리)만 하면 low, 진짜 비용은 서명이다. 현재 HARD 의존성에 cryptography가 없다 → 권장안은 (a) 키 없는 변조증거만 채택 = RFC6962 후보의 append-only 체인으로 대체(새 의존성 0). Ed25519 순수파이썬 내장(~60줄)은 가능하지만 EV-8이 체인으로 이미 닫히면 YAGNI. RFC3161은 네트워크 필요라 오프라인 제약상 탈락. 즉 이 후보는 '분리 구조'만 참고하고 서명은 도입하지 않는 게 맞다.

### SQLite (stdlib sqlite3) WAL 모드를 대장 저장소로

- URL: https://www.sqlite.org/wal.html
- 정체: 저널모드 WAL SQLite를 append-only 이벤트 테이블로 사용. 이벤트 1건 = INSERT 1행, 상태 조회는 SELECT. 표준라이브러리만.
- 성숙도: SQLite는 파이썬 표준 동봉, WAL은 2010년부터 안정. 별도 설치 0.
- **훔칠 메커니즘**: (1) 커널이 강제하는 단일 라이터 직렬화 — BEGIN IMMEDIATE로 쓰기 트랜잭션을 열면 두 번째 프로세스는 조용히 덮어쓰는 대신 SQLITE_BUSY를 받는다. 지금의 lost-update가 '검출 가능한 에러'로 바뀐다. (2) O(1) append — 현재 run_ledger.py:441 _append()는 ledger.append(rec) 후 전 대장을 재직렬화한다(N번 append = O(N²) I/O). (3) 2파일 비원자성 해소 — run-ledger.jsonl과 run-metadata.json 사이가 비원자라 그 틈에 죽으면 불일치. 한 트랜잭션에서 events INSERT + meta UPSERT를 함께 커밋하면 창이 사라진다. 부수효과로 claim_key 인덱스 조회가 되어 fact 단위 재검증 대상 추출이 전건 스캔이 아니게 된다.
- 겨냥 약점: `OPS-1, SC-7 (부수: SC-1, SC-8)` · 이식비용 **medium** · confidence **high**
- 이식 노트: 새 의존성 0(stdlib). 비용은 코드가 아니라 포맷 변경 — audit 번들의 사람이 읽는 JSONL이 사라지면 안 되므로 정본은 .db, 게이트 통과 시점에 SELECT * ORDER BY seq → run-ledger.jsonl 덤프 뷰를 남기는 절충. 윈도우 필수 반영 2건: (a) WAL은 -shm 공유메모리를 써서 네트워크 드라이브/OneDrive·Dropbox 동기화 폴더에서 깨진다 — 작업폴더가 F:\ 로컬 NTFS인지 확인(확인됨: F:\Claude\projects). (b) 읽기 전용 접속도 빈 WAL 개폐 시 순간 배타락을 요구하니 모든 connect에 busy_timeout(5000ms) 설정. 쓰기가 드물면 DELETE 저널도 선택지.

### google-deepmind/long-form-factuality (SAFE)

- URL: https://github.com/google-deepmind/long-form-factuality
- 정체: 긴 응답을 원자사실로 분해한 뒤 각 사실을 검색으로 supported/irrelevant/not-supported 판정하는 자동 사실성 평가기.
- 성숙도: Google DeepMind 공식, arXiv 2403.18802. 크라우드 어노테이터와 72% 일치, 불일치 100건 재판정에서 SAFE가 76% 승, 인간 대비 20배 이상 저렴.
- **훔칠 메커니즘**: 4단계: (1) 응답 → 원자사실 리스트 분해, (2) 문맥 의존 표현 해소(대명사/생략 복원 = self-contained화), (3) relevance 필터로 질문에 무관한 사실을 'irrelevant'로 분모에서 제외(과잉 페널티 방지), (4) 남은 각 사실에 검색 쿼리를 상한 내에서 발행해 supported/not-supported 판정. 점수 F1@K — 재현율을 '인간이 선호하는 길이 K'로 나눠 무한히 사실을 늘려도 포화한다.
- 겨냥 약점: `EV-7 (+ SC-3 수렴 판정에 F1@K 전용 가능)` · 이식비용 **medium** · confidence **high**
- 이식 노트: 파이썬 + 외부 검색 API 의존이지만 검색부는 우리 fetch.py/search.py로 갈아끼우면 된다(새 런타임 의존성 0). EV-7의 핵심 이득: 현재 verify_facts.py는 UNIT 정규식 화이트리스트(line 61: TWh|GWh|조원|억원|Nm³/h…)에 걸리는 숫자만 무태그 후보로 잡아 화이트리스트 밖 단위(건, 명, 개사, ppm, bp, x배, 순위)는 통째로 검출 불가다. SAFE는 화이트리스트를 버리고 분해→각각 검증이라 단위 열거가 원리적으로 불필요. 현실적 이식은 하이브리드 — 정규식은 1차 스크리너로 남기고 화이트리스트 밖 잔여 숫자 토큰만 LLM 원자사실 분해로 2차 처리. relevance 필터는 페이지번호·조항번호·연도 오탐을 죽이는 데 그대로 써서 _plausible()의 수동 예외(line 76~81)를 대체.

### nielstron/quantulum3

- URL: https://github.com/nielstron/quantulum3
- 정체: 비정형 텍스트에서 수량·단위를 추출하는 파이썬 라이브러리. 290+ 단위, 75 엔티티 내장, 철자 숫자·범위·오차 파싱.
- 성숙도: marcolagi/quantulum의 python3 포크, PyPI + conda-forge 배포, 유지보수 중.
- **훔칠 메커니즘**: 우리가 하는 것의 정반대 설계 — 단위 목록을 정규식에 하드코딩하지 않고 단위 온톨로지(entity/unit DB)를 데이터로 들고 표면형→정규 단위로 해석한다. 범위(10-20 kg)와 불확실성(5±1 m)을 1급 개념으로 다루는 점도 우리에게 직접 필요하다. 동명이의 단위(pound=통화/질량)는 벡터+kNN 분류기로 처리.
- 겨냥 약점: `EV-7` · 이식비용 **medium** · confidence **high**
- 이식 노트: 정직한 평가: 그대로 못 쓴다. (a) 한국어 미지원 — 우리 화이트리스트의 알맹이인 조원/억원/톤/Nm³/h를 못 잡는다. (b) 완전 기능엔 numpy+scipy+sklearn 필요. 라이브러리가 아니라 설계를 훔치는 쪽이 맞다: verify_facts.py line 61 UNIT 정규식과 line 137 UNIT_SCALE dict를 하나의 단위 테이블(JSON)로 통합하고, 검출을 '테이블에 있는 단위'가 아니라 '숫자 토큰 전부를 잡은 뒤 날짜/조항번호/페이지/버전 같은 부정 패턴(denylist)으로 깎는' 방향으로 뒤집는다 — 화이트리스트는 새 단위가 나올 때마다 조용히 새지만 denylist는 새면 오탐(=사람이 본다)으로 드러나므로 실패 방향이 안전하다. 범위/오차 파싱 규칙은 코드를 보고 규칙만 베껴 stdlib로 재현.

### Litestream (평가 결과: 채택 비추천)

- URL: https://litestream.io/how-it-works/
- 정체: SQLite WAL을 사이드카 프로세스가 오브젝트 스토리지로 연속 복제하고 시점 복구를 제공하는 Go 도구. 결론은 '쓰지 말 것'.
- 성숙도: Fly.io 유지, v0.5.0 활발. 다만 Go 바이너리라 파이썬 스킬에 넣을 물건이 아님.
- **훔칠 메커니즘**: 개념적으로 훔칠 것은 'generation'뿐 — 스냅샷 + 이후 연속 WAL 변경분을 한 세대로 묶고 연속성이 끊기면 새 세대 시작. 이미 run_ledger.py의 generation 카운터와 같은 발상이라 새로 얻을 게 없다. 반대로 채택 불가 이유는 명확: 별도 프로세스 상주, 복제 대상 1개 제한, Litestream이 체크포인트를 독점하려 DB에 읽기 락을 유지한다.
- 겨냥 약점: `OPS-1, SC-7 (내구성·복구 축 — 대체안 권장)` · 이식비용 **high** · confidence **high**
- 이식 노트: stdlib로 끝난다: sqlite3.Connection.backup(dst)는 라이터가 돌고 있어도 일관된 온라인 스냅샷을 뜬다 → 게이트 통과 시점마다 audit/ledger-snapshot.db로 1줄. 시점 복구가 정말 필요해지면 그때 재검토. Go 사이드카 프로세스 수명 관리를 스킬이 떠안는 건 명백한 과설계이고 오프라인·Windows 제약과도 상충.
