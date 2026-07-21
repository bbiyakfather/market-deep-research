# tests/fixtures

이 폴더에는 바이너리 fixture를 두지 않는다. 모든 적대적 입력(PDF·캡처 PNG·
facts.jsonl·report.md·리다이렉트 응답)은 `../test_adversarial.py`가 실행 시
`tempfile.TemporaryDirectory()` 안에 **코드로 동적 생성**한다.

이유:
  - 재현성 — fitz 버전/폰트에 의존하는 PDF를 커밋된 바이너리로 고정하면
    환경에 따라 깨진다. 코드 생성은 실행 환경의 fitz로 매번 새로 만든다.
  - 감사 가능 — 무엇이 "공격 입력"인지 코드에 그대로 드러난다.

실행:
    PYTHONUTF8=1 python tests/test_adversarial.py
