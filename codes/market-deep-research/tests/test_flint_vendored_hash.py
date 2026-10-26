"""내장 flint 소스가 VENDORED.md 의 sha256 목록과 일치하는지(수정 금지 규칙 고정)."""
import hashlib, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "flint"


def test_vendored_files_unchanged():
    listed = {}
    for line in (ROOT / "VENDORED.md").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and len(parts[0]) == 64:
            listed[parts[1].lstrip("*").lstrip("./")] = parts[0]
    assert listed, "VENDORED.md 에 sha256 목록이 없다"
    actual = {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts}
    assert actual == listed
