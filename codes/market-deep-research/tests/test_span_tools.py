"""span_tools(글자 대조) + facts_db span 스키마 + verify_facts.check_spans 최소 케이스."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import span_tools as st
import facts_db
import verify_facts
from skill_paths import WorkPaths

SHA = "a" * 64
SHA12 = SHA[:12]
CLEAN = "머리말\n• 2024년 시장 규모는 12조원이다.\n성장률은\n연 8.5% 로\n추정된다.\n끝"


def _work(tmp_path, text=CLEAN):
    (tmp_path / "_sources").mkdir()
    (tmp_path / "_sources" / f"{SHA12}_clean.txt").write_bytes(text.encode("utf-8"))
    return tmp_path


def test_find_and_normalize(tmp_path):
    lines = st.load_clean(_work(tmp_path), SHA12)
    assert st.find_span(lines, "2024년  시장 규모는 12조원이다.") == (2, 2)      # 불릿·공백 정규화
    assert st.find_span(lines, "성장률은 연 8.5% 로 추정된다.") == (3, 5)        # 행 걸침
    assert st.check_span(lines, "성장률은 연 8.5% 로", 4, 4)                     # ±2 slack


def test_reject_paraphrase_and_typo(tmp_path):
    lines = st.load_clean(_work(tmp_path), SHA12)
    assert st.find_span(lines, "2024년 시장 규모는 12조 원이다.") is None        # 띄어쓰기 한 칸 차이
    assert st.find_span(lines, "시장은 12조원 규모다") is None


def test_ellipsis_order(tmp_path):
    lines = st.load_clean(_work(tmp_path), SHA12)
    assert st.find_span(lines, "2024년 … 12조원이다.") == (2, 2)
    assert st.find_span(lines, "추정된다. … 2024년") is None                    # 순서가 뒤집히면 실패


def test_formfeed_line_count_matches_grep(tmp_path):
    lines = st.load_clean(_work(tmp_path, "a\fb\nc\nd"), SHA12)
    assert len(lines) == 3 and st.find_span(lines, "d") == (3, 3)               # splitlines() 였다면 4행


def test_span_out_of_range(tmp_path):
    lines = st.load_clean(_work(tmp_path), SHA12)
    assert not st.check_span(lines, "2024년 시장 규모는 12조원이다.", 6, 6)       # 적중 행에서 4행 떨어짐
    assert not st.check_span(lines, "머리말", 0, 1) and not st.check_span(lines, "머리말", 1, 99)
    assert "2>" in st.context(lines, 2, 2, n=1)


def _ev(**kw):
    return {"id": "E001", "fact_id": "F001", "type": "text_quote", "source_url": "https://x.test",
            "sha256": SHA, "accessed_at": "2026-10-26", "verbatim": "x", **kw}


def test_schema_optional_span_fields():
    facts_db.validate_evidence(_ev())                                            # 기존 레코드 통과
    facts_db.validate_evidence(_ev(span={"clean": SHA12, "line": 2, "end": 3}, raw_quality="ocr"))
    facts_db.validate_evidence(_ev(span={"clean": SHA12, "t": "01:23"}))          # 영상: 행 없음
    with pytest.raises(facts_db.ValidationError):
        facts_db.validate_evidence(_ev(span={"clean": SHA12, "line": 5, "end": 3}))


def _ledgers(verbatim, **kw):
    return {"F001": {"id": "F001", "status": "confirmed", "evidence_ids": ["E001"]}}, \
           {"E001": _ev(verbatim=verbatim, **kw)}


def test_check_spans_fail_and_warn(tmp_path):
    wp = WorkPaths(_work(tmp_path))
    f, e = _ledgers("2024년 시장 규모는 12조원이다.", span={"clean": SHA12, "line": 2, "end": 2})
    assert verify_facts.check_spans(f, e, wp) == ([], [])
    f, e = _ledgers("2024년 시장 규모는 12조원이다.", span={"clean": SHA12, "line": 6, "end": 6})
    fail, _ = verify_facts.check_spans(f, e, wp)
    assert fail and fail[0].startswith("[span불일치] E001")
    f, e = _ledgers("바꿔 쓴 문장")                                                # span 없음 + 원문에 없음
    fail, warn = verify_facts.check_spans(f, e, wp)
    assert not fail and warn[0].startswith("[원문미포함] E001")
    f, e = _ledgers("성장률은 연 8.5% 로")                                         # span 없음 + 원문에 있음
    assert verify_facts.check_spans(f, e, wp) == ([], [])
    f, e = _ledgers("x", span={"clean": SHA12, "t": "00:10"})                    # 영상 t 만 → 생략
    assert verify_facts.check_spans(f, e, wp) == ([], [])
    f, e = _ledgers("x")
    e["E001"]["sha256"] = "b" * 64                                               # clean 파일 없음
    assert verify_facts.check_spans(f, e, wp)[1][0].startswith("[span없음] E001")


def test_number_boundary():
    assert st.find_span(["매출은 12.57% 증가"], "매출은 12.5") is None
    assert st.find_span(["시장 13조 원"], "3조 원") is None
    assert st.find_span(["매출은 12.5%."], "매출은 12.5") == (1, 1)     # 문장 끝 마침표는 허용
    assert st.find_span(["시장 3조 원"], "3조 원") == (1, 1)


def test_verbatim_sign_not_stripped():
    assert st.find_span(["+ 5% 감소"], "- 5% 감소") is None
    assert st.find_span(["- 5% 감소"], "5% 감소") == (1, 1)             # clean 쪽 불릿은 여전히 제거


def test_span_type_errors_do_not_crash(tmp_path):
    wp = WorkPaths(_work(tmp_path))
    for sp in ({"clean": SHA12, "line": "2", "end": 2}, {"clean": 123, "line": 1, "end": 1}):
        f, e = _ledgers("머리말", span=sp)
        fail, _ = verify_facts.check_spans(f, e, wp)
        assert fail and fail[0].startswith("[span형식] E001")


def test_clean_ref_path_escape_rejected(tmp_path):
    wp = WorkPaths(_work(tmp_path))
    with pytest.raises(ValueError):
        st.clean_path(tmp_path, "../x")
    f, e = _ledgers("머리말", span={"clean": "../../etc/passwd", "line": 1, "end": 1})
    assert verify_facts.check_spans(f, e, wp)[0][0].startswith("[span형식] E001")
    assert st.main(["find", str(tmp_path), "../x", "a"]) == 2
