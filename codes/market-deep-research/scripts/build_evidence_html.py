#!/usr/bin/env python3
"""build_evidence_html.py — report.md 의 F태그 문장마다 근거 인용 카드를 붙인 증빙판 HTML(단일 파일·오프라인).

  python build_evidence_html.py <report.md> <work_dir> [--customer]

구조: 본문 F태그 문장 → 바로 아래 `<details>` 인용 카드(verbatim·span·출처 URL·접근시각·sha256·캡처 썸네일·
출처 유형·원문 품질) → 그 안의 `<details>` ±6행 맥락 → `_sources/<sha12>_clean.txt` 상대 링크 → 끝에 검색 기록.
`--customer` 는 맥락창·전문 링크·검색 기록을 뺀 고객용(audit/evidence-customer.html, 내부판을 덮어쓰지 않는다).
새 서술은 만들지 않는다: 원고 문장과 대장 필드를 그대로 옮길 뿐이다. 외부 의존성 0(html 모듈).
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit

import span_tools
import verify_facts as vf
from render_pdf import embed_local_image
from facts_db import _read_jsonl, evidence_ids
from skill_paths import WorkPaths

CSS = ("body{font:14px/1.6 system-ui,'Malgun Gothic',sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem}"
       "details{margin:.3rem 0 .9rem 1rem;border-left:3px solid #9ab;padding-left:.7rem}"
       "pre{background:#f4f4f4;padding:.5rem;overflow:auto;white-space:pre-wrap}"
       "blockquote{margin:.3rem 0;padding:.3rem .7rem;background:#fafaf0}"
       ".b{display:inline-block;font-size:12px;padding:0 .4rem;margin-right:.3rem;border:1px solid #888;border-radius:3px}"
       ".m{color:#555;font-size:12px}img{max-width:20rem;border:1px solid #ccc}table{border-collapse:collapse}"
       "td,th{border:1px solid #ccc;padding:.15rem .4rem;font-size:12px}")


def _e(x) -> str:
    return html.escape(str(x if x is not None else ""), quote=True)


def _link(url: str | None, label: str | None = None) -> str:
    # http(s) 만 링크로 만든다(javascript: 등 차단). 그 외는 평문.
    if url and urlsplit(url).scheme in ("http", "https"):
        return f'<a href="{_e(url)}" rel="noopener noreferrer">{_e(label or url)}</a>'
    return _e(url)


def _t_url(url: str, t) -> str | None:
    """span.t(mm:ss|h:mm:ss) 를 출처 URL 의 시각 지정으로 붙인다(유튜브 t=, 그 외 #t=). 형식이 틀리면 None."""
    if not (isinstance(t, str) and vf._SPAN_T.fullmatch(t)):
        return None
    sec = 0
    for part in t.split(":"):
        sec = sec * 60 + int(part)
    if "youtu" in urlsplit(url).netloc:
        return url + ("&" if "?" in url else "?") + f"t={sec}"
    return url.split("#")[0] + f"#t={sec}"


def _clean_ref(e: dict) -> str | None:
    span = e.get("span") if isinstance(e.get("span"), dict) else {}
    ref = span.get("clean") or str(e.get("sha256") or "")[:12]
    return ref or None


def _clean_lines(wp: WorkPaths, e: dict):
    """(파일명, 행 목록). 없거나 형식이 틀리면 (None, None)."""
    try:
        ref = _clean_ref(e)
        path = span_tools.clean_path(wp.root, ref) if ref else None
    except ValueError:
        return None, None
    if not path or not path.is_file():
        return None, None
    return path.name, span_tools.load_clean(wp.root, ref)


def _thumb(wp: WorkPaths, e: dict) -> str:
    """캡처를 data URI 로 내장해 HTML 을 단일 파일로 유지한다(render_pdf 와 같은 함수·경로 제한)."""
    cap = e.get("capture")
    if not isinstance(cap, str) or not cap:
        return ""
    try:
        uri = embed_local_image(cap, wp.root)
    except (ValueError, RuntimeError, OSError):
        return ""
    return f'<img alt="{_e(e["id"])} 캡처" src="{uri}">'


def _card(wp: WorkPaths, e: dict, passed: set[str], links_ok: bool, customer: bool) -> str:
    span = e.get("span") if isinstance(e.get("span"), dict) else {}
    name, lines = _clean_lines(wp, e)
    badges = ["원문 대조 통과"] if e["id"] in passed else ([] if customer else ["원문 대조 미확인"])
    badges += [f"출처유형: {e['source_tier']}"] if e.get("source_tier") else []
    badges += [f"원문품질: {e['raw_quality']}"] if e.get("raw_quality") else []
    out = [f'<div class="b-row">{"".join(f"<span class=b>{_e(b)}</span>" for b in badges)}</div>']
    if e.get("verbatim"):
        out.append(f"<blockquote>{_e(e['verbatim'])}</blockquote>")
    loc = []
    has_line = type(span.get("line")) is int and type(span.get("end", span.get("line"))) is int
    if has_line:
        loc.append(f"clean {span['line']}~{span.get('end', span['line'])}행")
    if span.get("t"):
        loc.append(f"t={span['t']}")
    url = e.get("source_url")
    t_link = _t_url(url, span.get("t")) if (links_ok and url and not has_line) else None
    src = _link(t_link, url) if t_link else (_link(url) if links_ok else _e(url))
    out.append(f'<div class="m">{_e(" · ".join(loc))} 출처 {src}<br>접근 {_e(e.get("accessed_at"))}'
               f' · sha256 {_e(e.get("sha256"))}</div>')
    out.append(_thumb(wp, e))
    if not customer and lines is not None:
        hit = (span["line"], span.get("end", span["line"])) if has_line and e.get("verbatim") is not None \
            else (span_tools.find_span(lines, e["verbatim"]) if e.get("verbatim") else None)
        if hit:
            out.append(f"<details><summary>앞뒤 맥락(±6행)</summary><pre>{_e(span_tools.context(lines, *hit))}</pre></details>")
        if links_ok:
            out.append(f'<div class="m"><a href="../_sources/{quote(name)}">원문 전문({_e(name)})</a></div>')
    return "\n".join(x for x in out if x)


def _search_table(wp: WorkPaths) -> str:
    path = wp.audit / "search-log.jsonl"
    rows = _read_jsonl(path) if path.is_file() else []
    cols = ("ts", "axis", "tier", "backend", "query", "n_returned", "n_kept", "error")
    body = "".join("<tr>" + "".join(f"<td>{_e(r.get(c))}</td>" for c in cols) + "</tr>" for r in rows)
    return (f"<h2>검색 기록</h2><p class=m>{len(rows)}건(빈 결과·실패 포함)</p>"
            f"<table><tr>{''.join(f'<th>{c}</th>' for c in cols)}</tr>{body}</table>")


def build(report_md: Path | str, work: WorkPaths | Path | str, *, customer: bool = False) -> Path:
    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    md = Path(report_md).read_text(encoding="utf-8")
    facts = {f["id"]: f for f in _read_jsonl(wp.facts) if isinstance(f, dict) and "id" in f}
    evidence = {e["id"]: e for e in _read_jsonl(wp.evidence) if isinstance(e, dict) and "id" in e}
    passed: set[str] = set()
    vf.check_spans(facts, evidence, wp, passed)            # 대조는 verify_facts 와 같은 함수 — 재구현 없음
    body, _ = vf.split_body_appendix(md)
    parts = ["<!doctype html><html lang=ko><head><meta charset=utf-8>"
             '<meta name="referrer" content="no-referrer"><title>증빙판</title>'
             f"<style>{CSS}</style></head><body><h1>증빙판{'(고객용)' if customer else ''}</h1>"]
    for seg in vf.split_segments(body, preserve_text=True):
        if seg.lstrip().startswith("#"):
            parts.append(f"<h3>{_e(seg.lstrip('# ').strip())}</h3>")
            continue
        fids = list(dict.fromkeys(m.group(0).strip("()[]") for m in vf.TAG.finditer(seg)))
        if not fids:
            continue
        parts.append(f"<p>{_e(seg)}</p>")
        for fid in fids:
            f = facts.get(fid)
            evs = [evidence[i] for i in (evidence_ids(f) if f else []) if i in evidence]
            # URL 개수와 clean 파일 개수가 어긋나면(리다이렉트 병합·교체 의심) 링크를 붙이지 않는다.
            urls = {e.get("source_url") for e in evs if e.get("source_url")}
            files = {n for e in evs for n in [_clean_lines(wp, e)[0]] if n}
            links_ok = not files or len(urls) == len(files)
            if customer and evs:       # 고객용은 fact 당 대표 evidence 1건: 대조 통과·lead 재열람 해시 일치 우선
                reread = {str(ev.get("reread_sha256") or "").lower() for ev in (f.get("verify_events") or [])
                          if isinstance(ev, dict) and ev.get("by") == "lead" and ev.get("action") == "reread"}
                evs = [min(evs, key=lambda e: (str(e.get("sha256") or "").lower() not in reread, e["id"] not in passed))]
            note = "" if (links_ok or customer) else f"<div class=m>URL {len(urls)}개 ↔ 원문 파일 {len(files)}개 불일치 — 링크 미부착</div>"
            cards = "".join(f"<details><summary>{_e(fid)} · {_e(e['id'])}</summary>"
                            f"{_card(wp, e, passed, links_ok, customer)}</details>" for e in evs)
            parts.append(cards + note if evs else f"<div class=m>{_e(fid)}: 연결된 evidence 없음</div>")
    if not customer:
        parts.append(_search_table(wp))
    parts.append("</body></html>")
    out = wp.audit / ("evidence-customer.html" if customer else "evidence.html")
    wp.audit.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="증빙판 HTML 생성")
    ap.add_argument("report_md")
    ap.add_argument("work_dir")
    ap.add_argument("--customer", action="store_true", help="맥락창·전문 링크·검색 기록 제거")
    a = ap.parse_args(argv)
    print(build(a.report_md, a.work_dir, customer=a.customer))
    return 0


if __name__ == "__main__":
    sys.exit(main())
