"""references/*.md · SKILL.md 가 언급한 references/xxx.md · scripts/xxx.py 가 실제 파일인지 (의존성 0)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 앞이 경로 문자(다른 스킬의 mdr-hwpx/references/… 등)면 이 스킬의 파일이 아니므로 제외
LINK = re.compile(r"(?<![\w/.~-])((?:references|scripts)/[\w\-]+\.(?:md|py))")


def test_mentioned_references_and_scripts_exist():
    docs = [ROOT / "SKILL.md", *sorted((ROOT / "references").glob("*.md"))]
    broken = [f"{d.name}: {m}" for d in docs
              for m in sorted(set(LINK.findall(d.read_text(encoding="utf-8")))) if not (ROOT / m).is_file()]
    assert not broken, broken
