"""source_index.py — `_sources` 스냅샷을 `sources.md` 출처목록으로 묶는다.

검색만 모드(mdr-search) 산출물. 사실대장·게이트·캡처·PDF 는 다루지 않는다.

CLI:
  python source_index.py demo
  python source_index.py <work_dir> [--topic "..."] [--out sources.md]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from skill_paths import WorkPaths


EXCERPT_MAX = 280


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _md_cell(value: object) -> str:
    text = str(value if value is not None else "").strip()
    if not text:
        return "—"
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _excerpt(text: str, limit: int = EXCERPT_MAX) -> str:
    norm = re.sub(r"\s+", " ", text or "").strip()
    if len(norm) <= limit:
        return norm
    return norm[:limit].rstrip()


def _host(url: str | None) -> str:
    if not url:
        return ""
    return (urlparse(url).hostname or "").lower()


def _filename(value: object) -> str | None:
    if not value:
        return None
    return Path(str(value)).name


def _read_clean(src: Path, clean_name: str | None) -> str:
    name = _filename(clean_name)
    if not name:
        return ""
    path = src / name
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _row_from_meta(sha12: str, meta: dict, src: Path) -> dict:
    raw_name = _filename(meta.get("raw")) or f"{sha12}_raw.html"
    clean_name = _filename(meta.get("clean"))
    final_url = meta.get("final_url") or meta.get("url")
    sha = meta.get("sha256") or sha12
    return {
        "title": meta.get("title"),
        "publisher": _host(final_url),
        "accessed_at": meta.get("accessed_at"),
        "url": meta.get("url"),
        "final_url": final_url,
        "sha12": str(sha)[:12],
        "sha256": sha,
        "local": f"_sources/{raw_name}",
        "excerpt": _excerpt(_read_clean(src, clean_name)),
        "status": meta.get("status"),
    }


def _row_from_files(sha12: str, raw_path: Path, src: Path) -> dict:
    clean_name = f"{sha12}_clean.txt"
    return {
        "title": None,
        "publisher": "",
        "accessed_at": None,
        "url": None,
        "final_url": None,
        "sha12": sha12,
        "sha256": sha12,
        "local": f"_sources/{raw_path.name}",
        "excerpt": _excerpt(_read_clean(src, clean_name)),
        "status": None,
    }


def build_index(work_dir: Path | str) -> list[dict]:
    """`_sources/*.meta.json` 을 읽고, 없으면 raw/clean 파일명으로 폴백한다."""
    src = WorkPaths(work_dir).sources
    if not src.is_dir():
        return []
    rows_by_sha: dict[str, dict] = {}
    for meta_path in sorted(src.glob("*.meta.json")):
        sha12 = meta_path.name.removesuffix(".meta.json")
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        if isinstance(meta, dict):
            rows_by_sha[sha12] = _row_from_meta(sha12, meta, src)
    for raw_path in sorted(src.glob("*_raw.*")):
        sha12 = raw_path.name.split("_raw.", 1)[0]
        if not sha12 or sha12 in rows_by_sha:
            continue
        rows_by_sha[sha12] = _row_from_files(sha12, raw_path, src)
    rows = list(rows_by_sha.values())
    rows.sort(key=lambda r: (r.get("accessed_at") or "", r.get("sha12") or ""))
    for i, row in enumerate(rows, 1):
        row["n"] = i
    return rows


def _fetch_counts(work_dir: Path | str) -> dict:
    """실제 생산 로그에서 시도 실패와 URL별 마지막 호출의 확보 상태를 구분한다."""
    path = Path(work_dir) / "audit" / "fetch-log.jsonl"
    latest = {}
    attempt_failures = 0
    if not path.is_file():
        return {"attempt_failures": 0, "final_failures": 0}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if not isinstance(row, dict) or not row.get("url"):
                continue
            status = row.get("status")
            if status not in ("ok", "partial", "fail"):
                # 구 로그는 transport 성공만 기록했다. snapshot을 원문 ok로 추정하지 않는다.
                status = "fail" if row.get("failure_reason") or not row.get("snapshot_path") else "partial"
            if row.get("kind") != "final" and status == "fail":
                attempt_failures += 1
            latest[row["url"]] = status
    except OSError:
        pass
    return {"attempt_failures": attempt_failures,
            "final_failures": sum(status == "fail" for status in latest.values())}


def _failure_count(work_dir: Path | str) -> int:
    return _fetch_counts(work_dir)["final_failures"]


def write_markdown(rows: list[dict], out_path: Path | str, topic: str | None = None,
                   work_dir: Path | str | None = None) -> Path:
    """머리말 + 표 + 발췌 블록. 링크는 최종 URL. 실패 URL 은 건수만."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 출처목록",
        "",
        f"- 주제: {topic or '(미지정)'}",
        f"- 생성시각: {_now()}",
        f"- 건수: {len(rows)}",
        "",
        "| 번호 | 제목 | 발행처 | 접근일 | URL | sha256 | 로컬 | 상태 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        final = row.get("final_url") or row.get("url") or ""
        url_cell = f"[{_md_cell(final)}]({final})" if final else "—"
        accessed = (row.get("accessed_at") or "")[:10]
        lines.append(
            f"| {row['n']} | {_md_cell(row.get('title'))} | {_md_cell(row.get('publisher'))} | "
            f"{_md_cell(accessed)} | {url_cell} | `{row.get('sha12') or ''}` | "
            f"{_md_cell(row.get('local'))} | {_md_cell(row.get('status'))} |"
        )
    lines.append("")
    for row in rows:
        heading = row.get("title") or row.get("final_url") or row.get("url") or f"출처 {row['n']}"
        lines += [f"## {row['n']}. {heading}", ""]
        if row.get("final_url"):
            lines += [f"- URL: {row['final_url']}", ""]
        lines += [row.get("excerpt") or "(발췌 없음)", ""]
    counts = _fetch_counts(work_dir if work_dir is not None else out.parent)
    if counts["final_failures"] or counts["attempt_failures"]:
        lines += ["## 부록: 확보 실패", "",
                  f"최종 실패 URL {counts['final_failures']}건 · 시도 실패 {counts['attempt_failures']}회 "
                  "(`audit/fetch-log.jsonl`, partial은 최종 실패에서 제외).", ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def demo() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        wd = Path(td)
        src = wd / "_sources"
        src.mkdir()
        sha = "a" * 64
        sha12 = sha[:12]
        clean = "PEM 수전해는\n  물과 전기를 쓴다.  " + ("본문 " * 80)
        (src / f"{sha12}_raw.html").write_text(
            "<html><title>PEM 수전해</title></html>", encoding="utf-8")
        (src / f"{sha12}_clean.txt").write_text(clean, encoding="utf-8")
        meta = {
            "url": "https://example.com/pem?q=1",
            "final_url": "https://example.com/pem",
            "http_status": 200,
            "mime": "text/html",
            "is_pdf": False,
            "sha256": sha,
            "accessed_at": "2026-08-22T12:00:00",
            "title": "PEM 수전해",
            "raw": f"{sha12}_raw.html",
            "clean": f"{sha12}_clean.txt",
            "status": "ok",
            "fetch_ref": "ref1",
        }
        (src / f"{sha12}.meta.json").write_text(
            json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        sha2 = "b" * 12
        (src / f"{sha2}_raw.txt").write_text("raw fallback", encoding="utf-8")
        (src / f"{sha2}_clean.txt").write_text("폴백 발췌 본문입니다.", encoding="utf-8")
        audit = wd / "audit"
        audit.mkdir()
        (audit / "fetch-log.jsonl").write_text(
            json.dumps({"url": "https://blocked.example/x", "failure_reason": "http 403"}, ensure_ascii=False) + "\n",
            encoding="utf-8")

        rows = build_index(wd)
        assert len(rows) == 2, rows
        pem = next(r for r in rows if r["sha12"] == sha12)
        fb = next(r for r in rows if r["sha12"] == sha2)
        assert pem["title"] == "PEM 수전해"
        assert pem["publisher"] == "example.com"
        assert pem["final_url"] == "https://example.com/pem"
        assert "\n" not in pem["excerpt"] and "  " not in pem["excerpt"]
        assert pem["excerpt"].startswith("PEM 수전해는 물과 전기를 쓴다.")
        assert 200 <= len(pem["excerpt"]) <= 280, len(pem["excerpt"])
        assert fb["title"] is None and fb["excerpt"] == "폴백 발췌 본문입니다."

        out = write_markdown(rows, wd / "sources.md", topic="PEM 수전해")
        md = out.read_text(encoding="utf-8")
        assert md.count("| 1 |") == 1 and md.count("| 2 |") == 1, md
        assert "PEM 수전해" in md and "건수: 2" in md
        assert "](https://example.com/pem)" in md
        assert "example.com" in md
        assert "폴백 발췌 본문입니다." in md
        assert "실패 URL 1건" in md
        assert "blocked.example" not in md   # 부록은 건수만
    print(f"[{_now()}] source_index demo OK")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "demo":
        demo()
        return 0
    parser = argparse.ArgumentParser(
        description="Build sources.md from _sources snapshots")
    parser.add_argument("work_dir")
    parser.add_argument("--topic", default="")
    parser.add_argument("--out", default="sources.md")
    args = parser.parse_args(argv)
    work = Path(args.work_dir)
    rows = build_index(work)
    out = Path(args.out)
    if not out.is_absolute():
        out = work / out
    write_markdown(rows, out, topic=args.topic or None, work_dir=work)
    fail_n = _failure_count(work)
    extra = f", 실패 {fail_n}건" if fail_n else ""
    print(f"{out}  ({len(rows)}건{extra})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
