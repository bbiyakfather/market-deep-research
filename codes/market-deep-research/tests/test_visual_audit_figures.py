"""visual_audit.audit_figures: 도판(SVG) 린트 6항목 — 위반마다 FAIL, 정상 PASS."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import visual_audit as va  # noqa: E402

GOOD = ('<!-- FACTS: F001,F002 -->\n<svg xmlns="http://www.w3.org/2000/svg"><title>제목</title><desc>설명</desc>'
        '<text font-family="Malgun Gothic, sans-serif" font-size="12px">가</text>'
        '<g class="mark-rect role-mark marks"><path d="M0"/><path d="M1"/></g></svg>')


def _put(tmp_path, svg=GOOD, fact_ids=("F001", "F002"), chart_type="hbar"):
    (tmp_path / "assets").mkdir(exist_ok=True)
    (tmp_path / "assets" / "a.svg").write_text(svg, encoding="utf-8")
    if fact_ids is not None:
        (tmp_path / "assets" / "a.vl.json").write_text(
            json.dumps({"mdr": {"fact_ids": list(fact_ids), "chart_type": chart_type}}), encoding="utf-8")
    return tmp_path


def test_pass(tmp_path):
    assert va.audit_figures(_put(tmp_path)) == []
    assert va.main(["--figures", str(tmp_path)]) == 0


@pytest.mark.parametrize("name,svg,kw,mark", [
    ("글자", GOOD.replace('font-size="12px"', 'font-size="11px"'), {}, "①"),
    ("title", GOOD.replace("<title>제목</title>", ""), {}, "②"),
    ("desc", GOOD.replace("<desc>설명</desc>", ""), {}, "②"),
    ("facts", GOOD, {"fact_ids": ("F001", "F003")}, "③"),
    ("url", GOOD.replace("<text", '<image xlink:href="https://x.com/a.png"/><text'), {}, "④"),
    ("font", GOOD.replace("Malgun Gothic", "Arial"), {}, "⑤"),
    ("bars", GOOD.replace('<path d="M1"/>', '<path d="M1"/>' * 21), {}, "⑥"),
])
def test_each_violation_fails(tmp_path, name, svg, kw, mark, capsys):
    bad = va.audit_figures(_put(tmp_path, svg, **kw))
    assert len(bad) == 1 and mark in bad[0], bad
    assert va.main(["--figures", str(tmp_path)]) == 1
    assert mark in capsys.readouterr().out


def test_series_chart_skips_bar_count(tmp_path):
    many = GOOD.replace('<path d="M1"/>', '<path d="M1"/>' * 40)
    assert va.audit_figures(_put(tmp_path, many, chart_type="grouped")) == []


def test_no_sidecar_needs_facts_comment(tmp_path):
    assert va.audit_figures(_put(tmp_path, fact_ids=None)) == []
    bad = va.audit_figures(_put(tmp_path, GOOD.split("\n", 1)[1], fact_ids=None))
    assert len(bad) == 1 and "③" in bad[0]


@pytest.mark.parametrize("size,ok", [("9pt", True), ("8.9pt", False), ("12px", True), ("11px", False), ("0.7em", False),
                                     ("1em", True), ("12", True), ("10", False)])
def test_font_size_units(tmp_path, size, ok):
    svg = GOOD.replace('font-size="12px"', f'font-size="{size}"')
    assert (va.audit_figures(_put(tmp_path, svg)) == []) is ok


@pytest.mark.parametrize("body", ["[1, 2]", '{"mdr": [1]}', "not json"])
def test_bad_sidecar_shape_is_violation(tmp_path, body):
    _put(tmp_path)
    (tmp_path / "assets" / "a.vl.json").write_text(body, encoding="utf-8")
    bad = va.audit_figures(tmp_path)
    assert len(bad) == 1 and "[도판사이드카형식]" in bad[0]


def test_native_svg_passes_lint(tmp_path):
    import make_chart as mc
    from facts_db import _write_jsonl_atomic
    from skill_paths import WorkPaths
    wp = WorkPaths(tmp_path / "research_n")
    _write_jsonl_atomic(wp.facts, [{"id": f"F00{i}", "claim": "x", "context": {"entity": f"기관{i}"},
                                    "value": {"raw": str(i), "unit": "건"}, "status": "confirmed", "evidence_ids": []}
                                   for i in (1, 2)])
    mc.make_chart("bar", wp.root, ["F001", "F002"], "네이티브")
    assert va.audit_figures(wp.root) == []
