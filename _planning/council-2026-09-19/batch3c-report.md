STATUS: complete
CHANGES: codes/market-deep-research/scripts/verify_facts.py — R06 통화배수 별칭·[단위미지원], R07 [수치미인식]·C$ 등 지역달러, R08 접미사 뒤 영숫자 비소비, R09 괄호/링크 내부 분할 보호; codes/market-deep-research/references/verification-gates.md — G3 수치·단위 계약 3줄; codes/market-deep-research/tests/test_batch3c_regressions.py — 표 7행+양성대조+미닫힘 괄호 회귀(신규)
VERIFIED: `cd codes/market-deep-research; python -m pytest -q tests/test_batch3c_regressions.py` → `21 passed in 0.07s`; `python -m pytest -q` → `452 passed in 46.10s`
JUDGMENT CALLS: 대장 `<ISO3>_<K|M|B|T|MN|BN>` 를 (통화, 10^3/10^6/10^9/10^12) 로 정규화하고 T=조=10^12 로 둠. 통화코드 뒤 알 수 없는 접미사(`USD_FOO`)는 USD×1 로 축소하지 않고 `[단위미지원]` FAIL. `mw` 는 SI 대소문자 변환 없이 미지원으로 남겨 `[수치미인식]`(원문 토큰 포함). `C$/A$/HK$/NT$/S$` 는 CAD/AUD/HKD/TWD/SGD 로 인식하고 환율 환산은 하지 않음. 배수 접미사는 소비될 때만 뒤 영숫자 금지를 걸어 `$45 B2B` 는 `$45` 로 남김. 괄호·`[]`·마크다운 링크가 한 세그먼트에서 미닫히면 해당 문단 전체를 기존 `_SENT_SPLIT` 으로 폴백.
GAPS: 없음. 기준선 431 + 신규 21 = 452 passed, 0 failed.
