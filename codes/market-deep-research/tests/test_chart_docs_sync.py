"""문서 ↔ 코드 동기화: visual-first §1a 유형명, CHART_MAP, 내장 flint 템플릿, 캡션 정규식 단일 출처."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import make_chart as mc  # noqa: E402
import render_pdf  # noqa: E402
import verify_facts  # noqa: E402
import visual_audit  # noqa: E402
from flint.vegalite.templates import vl_get_template_def  # noqa: E402


def _doc_types() -> set[str]:
    text = (ROOT / "references" / "visual-first.md").read_text(encoding="utf-8")
    sec = text.split("## 1a.", 1)[1].split("## 1b.", 1)[0]
    types: set[str] = set()
    for row in sec.splitlines():
        cols = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cols) >= 2 and row.startswith("|") and "`" in cols[1]:
            types |= set(re.findall(r"`([a-z0-9]+)`", cols[1])) - {"type"}
    return types


def test_doc_types_subset_of_chart_map():
    doc = _doc_types()
    assert doc and doc <= set(mc.CHART_MAP), doc - set(mc.CHART_MAP)
    assert set(mc.CHART_MAP) <= doc, "CHART_MAP 유형이 문서 §1a 에 빠짐: " + str(set(mc.CHART_MAP) - doc)


def test_chart_map_matches_vendored_templates():
    for name, (flint_type, channels, _need, _props) in mc.CHART_MAP.items():
        tpl = vl_get_template_def(flint_type)
        assert tpl, f"{name}: 내장 flint 에 템플릿 없음 {flint_type}"
        assert set(channels) <= set(tpl["channels"]), f"{name}: 지원하지 않는 채널 {set(channels) - set(tpl['channels'])}"


def test_caption_regex_single_source():
    # [그림] 캡션·도판 참조 정규식은 verify_facts 에만 있다. 사이드카 검사는 그것을 재사용하고, 다른 스크립트에 복제본이 없어야 한다.
    import inspect
    src = inspect.getsource(verify_facts.check_chart_sidecars)
    assert "_caption_within_two_lines" in src and "_figure_refs" in src
    for mod in (mc, render_pdf, visual_audit):
        assert r"\[그림\]" not in inspect.getsource(mod), f"{mod.__name__} 에 [그림] 캡션 정규식 복제본"
