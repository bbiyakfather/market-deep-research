"""search.py 검색 로그 기록 단위 테스트 (네트워크 없음)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from search import log_search  # noqa: E402


def _rows(audit):
    return [json.loads(l) for l in (audit / "search-log.jsonl").read_text(encoding="utf-8").splitlines()]


def test_log_one_line_per_call_with_fields(tmp_path):
    audit = tmp_path / "audit"
    res = [{"url": "https://a.com", "source": "ddgs"}, {"url": "https://a.com", "source": "ddgs"}]
    log_search("고체전지", "web", 5, res, axis="기술요소", audit=audit)
    log_search("빈 검색", "web", 5, [], audit=audit)
    log_search("실패", "web", 5, None, error="timeout", audit=audit)
    a, b, c = _rows(audit)
    assert {"ts", "axis", "tier", "backend", "query", "filters", "n_requested", "n_returned", "n_kept"} <= a.keys()
    assert (a["axis"], a["n_returned"], a["n_kept"], a["tier"]) == ("기술요소", 2, 1, "ddgs")
    assert (b["axis"], b["n_returned"]) == (None, 0)
    assert c["error"] == "timeout" and c["n_returned"] == 0


def test_log_masks_secrets(tmp_path):
    audit = tmp_path / "audit"
    log_search("x api_key=SECRET123 a.b@corp.com mailto=me@x.org ?key=AIzaSECRET &secret=S3 Bearer tok999", "web", 1, [], audit=audit)
    line = (audit / "search-log.jsonl").read_text(encoding="utf-8")
    assert "SECRET123" not in line and "corp.com" not in line and "me@x.org" not in line
    assert not any(k in line for k in ("AIzaSECRET", "S3 ", "tok999"))


def test_search_import_call_logs_to_work_dir(tmp_path, monkeypatch):
    import search as S
    monkeypatch.setattr(S, "_search", lambda q, n, t: [{"url": "https://a.com", "source": "ddgs"}])
    S.search("q", 3, "web", axis="시장", work_dir=tmp_path)
    assert _rows(tmp_path / "audit")[0]["axis"] == "시장"
    monkeypatch.setattr(S, "_search", lambda q, n, t: (_ for _ in ()).throw(ValueError("boom")))
    try:
        S.search("q", 3, "web", work_dir=tmp_path)
    except ValueError:
        pass
    assert _rows(tmp_path / "audit")[1]["error"] == "boom"
