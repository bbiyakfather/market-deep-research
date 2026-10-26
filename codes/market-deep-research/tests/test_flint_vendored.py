"""내장(vendored) flint-py 가 JS 원본 출력과 같은 Vega-Lite 스펙을 내는지 유형별 1건씩 대조한다."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
FIXTURES = sorted(p for p in (ROOT / "tests" / "fixtures" / "flint").iterdir() if p.is_dir())


def _canon(o):
    """키 순서·float 마지막 비트 차이를 무시하는 정규화(flint-py test_fixtures.py 와 같은 방식)."""
    if isinstance(o, dict):
        return {k: _canon(o[k]) for k in sorted(o)}
    if isinstance(o, list):
        return [_canon(x) for x in o]
    if isinstance(o, float):
        return round(o, 9)
    return o


@pytest.mark.parametrize("fx", FIXTURES, ids=[p.name for p in FIXTURES])
def test_fixture_matches_js_reference(fx):
    from flint.vegalite import assemble_vegalite
    inp = json.loads((fx / "input.json").read_text(encoding="utf-8"))["input"]
    exp = json.loads((fx / "expected.json").read_text(encoding="utf-8"))
    assert _canon(assemble_vegalite(inp)) == _canon(exp)
