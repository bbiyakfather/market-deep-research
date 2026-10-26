"""make_chart.py flint 래퍼: 사이드카 생성·fact_ids 일치·overflow FAIL·도판값 대조(check_chart_sidecars)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import make_chart as mc  # noqa: E402
from facts_db import _write_jsonl_atomic  # noqa: E402
from skill_paths import WorkPaths  # noqa: E402
from verify_facts import check_chart_sidecars  # noqa: E402


def _fact(i, raw, entity, status="confirmed", series=None):
    ctx = {"metric": "market_size", "entity": entity, "geography": "KR", "period": "2025"}
    if series:
        ctx["series"] = series
    return {"id": f"F{i:03d}", "claim": f"{entity} {raw}", "context": ctx, "value": {"raw": raw, "unit": "KRW_T"},
            "status": status, "evidence_ids": [f"E{i:03d}"]}


@pytest.fixture
def work(tmp_path):
    wp = WorkPaths(tmp_path / "research_x")
    _write_jsonl_atomic(wp.facts, [_fact(1, "120.5", "삼성전자"), _fact(2, "80", "SK하이닉스"),
                                   _fact(3, "50.2", "마이크론"), _fact(4, "9", "대기", "pending")])
    return wp


def test_hbar_sidecar(work):
    side, svg = mc.make_chart_flint("hbar", work.root, ["F001", "F002", "F003"], "반도체 매출 비교")
    spec = json.loads(side.read_text(encoding="utf-8"))
    assert spec["mdr"]["fact_ids"] == ["F001", "F002", "F003"]
    assert [v["value_raw"] for v in spec["mdr"]["values"]] == ["120.5", "80", "50.2"]
    assert spec["config"]["font"].startswith("Malgun Gothic")
    assert not [k for k in spec if k.startswith("_")]
    if svg is not None:  # vl_convert 가 있을 때만
        assert svg.read_text(encoding="utf-8").startswith("<!-- FACTS: F001,F002,F003 -->")


def test_pending_fact_rejected(work):
    with pytest.raises(mc.ChartError, match="F004=pending"):
        mc.make_chart_flint("hbar", work.root, ["F001", "F004"], "거부")


def test_overflow_fails_unless_top(tmp_path):
    wp = WorkPaths(tmp_path / "research_o")
    _write_jsonl_atomic(wp.facts, [_fact(i, str(i), f"기업{i}") for i in range(1, 23)])
    ids = [f"F{i:03d}" for i in range(1, 23)]
    with pytest.raises(mc.ChartError, match="조용한 절단"):
        mc.make_chart_flint("bar", wp.root, ids, "초과")
    side, _ = mc.make_chart_flint("bar", wp.root, ids, "초과 top", top=5)
    m = json.loads(side.read_text(encoding="utf-8"))["mdr"]
    assert len(m["fact_ids"]) == 5 and len(m["dropped"]) == 17


def test_series_required_and_pie_limit(work, tmp_path):
    with pytest.raises(mc.ChartError, match="series"):
        mc.make_chart_flint("grouped", work.root, ["F001", "F002"], "시리즈 없음")
    wp = WorkPaths(tmp_path / "research_p")
    _write_jsonl_atomic(wp.facts, [_fact(i, str(i), f"기업{i}") for i in range(1, 7)])
    with pytest.raises(mc.ChartError, match="한도"):
        mc.make_chart_flint("pie", wp.root, [f"F{i:03d}" for i in range(1, 7)], "파이 6개")


def test_all_types_return_rows(tmp_path):
    """모든 유형에서 flint 가 data.values 를 돌려줘야 절단 검사가 의미 있다(비면 ChartError)."""
    wp = WorkPaths(tmp_path / "research_a")
    facts = [{**_fact(i + 1, str(10 + i), "e"), "context": {"axis": f"c{i % 3}", "series": ["s1", "s2"][i // 3]}} for i in range(6)]
    _write_jsonl_atomic(wp.facts, facts)
    ids = [f["id"] for f in facts]
    for t in mc.CHART_MAP:
        if t in ("scatter", "pie"):
            continue
        mc.make_chart_flint(t, wp.root, ids, f"전유형 {t}")


def test_empty_data_is_error(work, monkeypatch):
    import flint.vegalite as fv
    monkeypatch.setattr(fv, "assemble_vegalite", lambda i: {"mark": "bar", "encoding": {}, "data": {"values": []}})
    with pytest.raises(mc.ChartError, match="절단"):
        mc.make_chart_flint("hbar", work.root, ["F001", "F002"], "빈 데이터")


def test_no_vl_convert(work, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "vl_convert", None)  # import 실패 모의
    assert mc.main(["hbar", str(work.root), "--facts", "F001,F002", "--title", "무렌더"]) == 2
    assert "vl-convert-python" in capsys.readouterr().err
    assert mc.main(["bar", str(work.root), "--facts", "F001,F002", "--title", "폴백"]) == 0
    assert (work.root / "assets" / "폴백.svg").is_file()
    assert not (work.root / "assets" / "폴백.vl.json").exists()
    assert mc.main(["bar", str(work.root), "--facts", "F001,F002", "--title", "네이티브", "--engine", "native"]) == 0


def test_stale_svg_removed_and_facts_mismatch(work, monkeypatch):
    side, _ = mc.make_chart_flint("hbar", work.root, ["F001", "F002"], "낡음")
    svg = side.with_name("낡음.svg")
    svg.write_text("<!-- FACTS: F001,F003 -->\n<svg/>", encoding="utf-8")
    facts = {f["id"]: f for f in (_fact(1, "120.5", "a"), _fact(2, "80", "b"), _fact(3, "50.2", "c"))}
    rep = "![x](assets/낡음.svg)\n[그림] 제목 (F001)(F002) 출처: 가\n"
    assert any("FACTS 주석" in f for f in check_chart_sidecars(work.root, rep, facts)[0])
    monkeypatch.setitem(sys.modules, "vl_convert", None)
    mc.make_chart_flint("hbar", work.root, ["F001", "F002"], "낡음")  # 렌더 못 해도 낡은 SVG 는 지운다
    assert not svg.exists()


def _report(svg):
    return f"![x](assets/{svg.name})\n[그림] 제목 (F001, F002, F003) 출처: 가\n"


def test_sidecar_check_detects_mismatch(work):
    side, _ = mc.make_chart_flint("hbar", work.root, ["F001", "F002", "F003"], "대조")
    svg = side.with_name(side.name.replace(".vl.json", ".svg"))
    svg.write_text("<!-- FACTS: F001,F002,F003 -->\n<svg/>", encoding="utf-8")
    facts = {f["id"]: f for f in json.loads("[" + ",".join(
        json.dumps(_fact(i, r, e)) for i, r, e in [(1, "120.5", "a"), (2, "80", "b"), (3, "50.2", "c")]) + "]")}
    assert check_chart_sidecars(work.root, _report(svg), facts) == ([], [])
    facts["F002"]["value"]["raw"] = "81"  # 사실대장이 바뀌면 도판이 낡은 것
    fails, _ = check_chart_sidecars(work.root, _report(svg), facts)
    assert any("[도판값불일치]" in f for f in fails)
    facts["F002"]["value"]["raw"] = "80"
    fails, _ = check_chart_sidecars(work.root, _report(svg).replace(", F003", ""), facts)
    assert any("캡션" in f for f in fails)
    side.unlink()
    assert check_chart_sidecars(work.root, _report(svg), facts)[1][0].startswith("[도판사이드카없음]")
