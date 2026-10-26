# 대상 재현율과 열람 성공률. 네트워크는 replay 만 쓴다. demo 는 합성 자료만 본다.

import argparse
import importlib.util
import json
import os
import re
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
DEFAULT_FETCH = ROOT.parents[1] / "codes" / "market-deep-research" / "scripts" / "fetch.py"
# 한계: 정답지가 이 스킬 자신의 과거 결과이므로 이 점수는 회귀 감지용이지 절대 재현율이 아니다.
LIMITATION = "정답지가 이 스킬 자신의 과거 결과이므로 이 점수는 회귀 감지용이지 절대 재현율이 아니다."
HOST_GAP_SECONDS = 2.0


def norm(text: str) -> str:
    # 출처: _planning/exa-eval/exa_eval.py 의 norm(). 공백·하이픈을 빼고 소문자로 맞춘다.
    return re.sub(r"[\s\-]+", "", str(text or "").lower())


def die(message: str) -> None:
    raise SystemExit(message)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        die(f"파일을 읽지 못했습니다: {path} ({exc})")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def dump_json(path: Path, payload) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def load_json(path: Path):
    try:
        return json.loads(read_text(path))
    except ValueError as exc:
        die(f"JSON 이 아닙니다: {path}")
        raise exc


def name_keys(item: dict) -> set[str]:
    raw = [item.get("name") or ""]
    aliases = item.get("aliases") if isinstance(item.get("aliases"), list) else []
    raw.extend(aliases)
    return {key for key in (norm(value) for value in raw) if key}


def subject_name(row: dict, where: str) -> str | None:
    """v4/v3 는 context.entity, 구형 대장(영수증 OCR)은 최상위 subject."""
    context = row.get("context")
    if isinstance(context, dict) and "entity" in context:
        entity = context.get("entity")
        if isinstance(entity, str) and entity.strip():
            return entity.strip()
        if entity not in (None, ""):
            die(f"{where} context.entity 가 문자열이 아닙니다")
    if "subject" in row:
        subject = row.get("subject")
        if isinstance(subject, str) and subject.strip():
            return subject.strip()
        if subject not in (None, ""):
            die(f"{where} subject 가 문자열이 아닙니다")
    return None


def parse_jsonl(text: str, path: Path) -> list[tuple[int, dict]]:
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            die(f"{path}:{number} 행이 JSON 이 아닙니다")
        if not isinstance(row, dict):
            die(f"{path}:{number} 행이 객체가 아닙니다")
        rows.append((number, row))
    return rows


def collect_subjects(rows: list[tuple[int, dict]], path: Path) -> list[dict]:
    order: list[str] = []
    counts: dict[str, int] = {}
    for number, row in rows:
        if row.get("kind") == "evidence":
            continue
        where = f"{path}:{number}"
        name = subject_name(row, where)
        if name is None:
            die(f"{where} 행에서 대상을 읽지 못했습니다 (context.entity 또는 subject)")
        if name not in counts:
            order.append(name)
            counts[name] = 0
        counts[name] += 1
    if not order:
        die(f"대상을 한 건도 찾지 못했습니다: {path}")
    # 대장에는 별칭 필드가 없다. 점수 맞춤용으로 이름 자신만 넣는다.
    return [{"name": name, "aliases": [name], "fact_count": counts[name]} for name in order]


def build_truth(work_dir: Path, out: Path) -> list[dict]:
    facts = work_dir / "facts.jsonl"
    if not facts.is_file():
        die(f"사실 대장이 없습니다: {facts}")
    subjects = collect_subjects(parse_jsonl(read_text(facts), facts), facts)
    dump_json(out, subjects)
    total = sum(item["fact_count"] for item in subjects)
    print(f"대상 {len(subjects)}개, 사실 {total}건 → {out}")
    return subjects


def found_from_subjects(subjects: list[dict]) -> list[dict]:
    return [{"name": item["name"], "aliases": list(item["aliases"])} for item in subjects]


def split_aliases(cell: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,、;]\s*", cell) if part.strip()]


def parse_universe(text: str) -> list[dict] | None:
    table = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if not table:
        return None
    header = [cell.strip() for cell in table[0].strip("|").split("|")]
    if "대상" not in header:
        return None
    name_at = header.index("대상")
    alias_at = header.index("별칭") if "별칭" in header else None
    flag_at = header.index("포함/제외") if "포함/제외" in header else None
    found = []
    for line in table[1:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        if name_at >= len(cells) or not cells[name_at]:
            die("universe.md 표에서 대상 열을 읽지 못했습니다")
        if flag_at is not None:
            if flag_at >= len(cells):
                die("universe.md 표에서 포함/제외 열을 읽지 못했습니다")
            flag = cells[flag_at]
            if flag == "제외":
                continue
            if flag not in ("", "포함"):
                die(f"universe.md 포함/제외 값을 읽지 못했습니다: {flag}")
        name = cells[name_at]
        aliases = [name]
        if alias_at is not None and alias_at < len(cells):
            for alias in split_aliases(cells[alias_at]):
                if alias not in aliases:
                    aliases.append(alias)
        found.append({"name": name, "aliases": aliases})
    return found


def found_from_lines(text: str) -> list[dict]:
    found = []
    for line in text.splitlines():
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        found.append({"name": name, "aliases": [name]})
    return found


def found_from_json_data(data, path: Path) -> list[dict]:
    if isinstance(data, list) and all(isinstance(item, str) for item in data):
        return [{"name": item.strip(), "aliases": [item.strip()]} for item in data if item.strip()]
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        if any(key in item for item in data for key in ("context", "subject", "claim", "claim_key")):
            return found_from_subjects(collect_subjects(list(enumerate(data, 1)), path))
        found = []
        for item in data:
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                die(f"찾은 목록의 name 을 읽지 못했습니다: {path}")
            aliases = [name.strip()]
            extra = item.get("aliases")
            if extra is not None and not isinstance(extra, list):
                die(f"찾은 목록의 aliases 가 배열이 아닙니다: {path}")
            for alias in extra or []:
                if not isinstance(alias, str) or not alias.strip():
                    die(f"찾은 목록의 aliases 를 읽지 못했습니다: {path}")
                if alias.strip() not in aliases:
                    aliases.append(alias.strip())
            found.append({"name": name.strip(), "aliases": aliases})
        return found
    die(f"찾은 목록 형식을 읽지 못했습니다: {path}")


def load_found(path: Path) -> list[dict]:
    if not path.is_file():
        die(f"찾은 목록이 없습니다: {path}")
    text = read_text(path)
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return found_from_subjects(collect_subjects(parse_jsonl(text, path), path))
    if suffix == ".json":
        return found_from_json_data(load_json(path), path)
    if suffix == ".md" or path.name == "universe.md":
        table = parse_universe(text)
        if table is not None:
            return table
    stripped = text.lstrip()
    if suffix not in {".md", ".txt"} and stripped[:1] in "[{":
        try:
            data = json.loads(text)
        except ValueError:
            data = None
        if data is not None:
            return found_from_json_data(data, path)
    return found_from_lines(text)


def load_truth(path: Path) -> list[dict]:
    data = load_json(path)
    if not isinstance(data, list) or not data:
        die(f"정답지는 대상이 든 배열이어야 합니다: {path}")
    items = []
    for row in data:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str) or not row["name"].strip():
            die(f"정답지 항목에 name 이 없습니다: {path}")
        if not isinstance(row.get("aliases"), list):
            die(f"정답지 항목에 aliases 배열이 없습니다: {path}")
        count = row.get("fact_count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            die(f"정답지 fact_count 가 없습니다: {path}")
        name = row["name"].strip()
        aliases = [name]
        for alias in row["aliases"]:
            if not isinstance(alias, str) or not alias.strip():
                die(f"정답지 aliases 가 문자열이 아닙니다: {path}")
            if alias.strip() not in aliases:
                aliases.append(alias.strip())
        items.append({"name": name, "aliases": aliases, "fact_count": count})
    return items


def score(truth: list[dict], found: list[dict]) -> dict:
    # 한계: 정답지가 이 스킬 자신의 과거 결과이므로 이 점수는 회귀 감지용이지 절대 재현율이 아니다.
    truth_keys = [name_keys(item) for item in truth]
    found_keys = [name_keys(item) for item in found]
    all_found = set().union(*found_keys) if found_keys else set()
    all_truth = set().union(*truth_keys) if truth_keys else set()
    missed = []
    hit = 0
    for item, keys in zip(truth, truth_keys):
        if keys & all_found:
            hit += 1
        else:
            missed.append({"name": item["name"], "fact_count": item["fact_count"]})
    extras = []
    seen: set[str] = set()
    for item, keys in zip(found, found_keys):
        if keys & all_truth:
            continue
        key = norm(item["name"])
        if key in seen:
            continue
        seen.add(key)
        extras.append({"name": item["name"]})
    total = len(truth)
    return {
        "recall": {"found": hit, "total": total, "ratio": round(hit / total, 4)},
        "missed": missed,
        "extra": extras,
        "limitation": LIMITATION,
    }


def http_error(row: dict) -> bool:
    try:
        return int(row.get("http_status")) >= 400
    except (TypeError, ValueError):
        return False


def line_status(row: dict) -> str:
    status = row.get("status")
    if status in ("ok", "partial", "fail"):
        return status
    # 구 로그에는 status 가 없다. 스냅샷만으로 ok 라고 단정하지 않는다.
    if row.get("failure_reason") or http_error(row) or not row.get("snapshot_path"):
        return "fail"
    return "partial"


def acquisition_status(rows: list[dict]) -> str:
    """URL 의 마지막 확보 상태.

    kind=final 이 있으면 그 마지막 status 가 한 호출의 확보 결과다.
    구 로그는 계층 시도마다 한 줄이고, 성공 뒤에 폴백 실패가 마지막에 온다.
    그때는 성공 시도가 있으면 그 상태, 한 번도 없으면 fail 이다.
    """
    finals = [row for row in rows if row.get("kind") == "final"]
    if finals:
        return line_status(finals[-1])
    found = None
    for row in rows:
        status = line_status(row)
        if status in ("ok", "partial"):
            found = status
    return found or "fail"


def domain_of(url: str) -> str:
    try:
        host = urlsplit(url).hostname
    except ValueError:
        host = None
    return (host or "(호스트 없음)").lower()


def failed_urls(work_dirs: list[Path], out: Path) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for work_dir in work_dirs:
        path = work_dir / "audit" / "fetch-log.jsonl"
        if not path.is_file():
            die(f"fetch-log 가 없습니다: {path}")
        grouped: dict[str, list[dict]] = {}
        first: list[str] = []
        for number, row in parse_jsonl(read_text(path), path):
            url = row.get("url")
            if not isinstance(url, str) or not url.strip():
                continue
            url = url.strip()
            if url not in grouped:
                first.append(url)
                grouped[url] = []
            grouped[url].append(row)
        for url in first:
            if acquisition_status(grouped[url]) != "fail" or url in seen:
                continue
            seen.add(url)
            ordered.append(url)
    write_text(out, ("\n".join(ordered) + "\n") if ordered else "")
    domains = Counter(domain_of(url) for url in ordered)
    print(f"실패 URL {len(ordered)}건, 도메인 {len(domains)}개 → {out}", file=sys.stderr)
    for host, count in sorted(domains.items(), key=lambda item: (-item[1], item[0])):
        print(f"{host}\t{count}", file=sys.stderr)
    return ordered


def load_fetch(script: Path):
    folder = str(script.parent)
    sys.path.insert(0, folder)
    mod_name = "mdr_recall_fetch"
    sys.modules.pop(mod_name, None)
    spec = importlib.util.spec_from_file_location(mod_name, script)
    if spec is None or spec.loader is None:
        die(f"fetch.py 를 열 수 없습니다: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        die(f"fetch.py 를 불러오지 못했습니다: {script} ({exc})")
    fetch = getattr(module, "fetch", None)
    if not callable(fetch):
        die(f"fetch() 가 없습니다: {script}")
    return fetch, folder


def tier_and_reason(result: dict) -> tuple[str | None, str | None]:
    # 공개 반환 키 status·trace·final_url 만 본다.
    trace = result.get("trace") if isinstance(result.get("trace"), list) else []
    tier = None
    reason = None
    for row in trace:
        if not isinstance(row, dict):
            continue
        if row.get("verdict") in ("ok", "partial") and row.get("tier"):
            tier = str(row["tier"])
        for key in ("fail", "error", "reason"):
            if row.get(key):
                reason = str(row[key])
    status = result.get("status")
    if status in ("ok", "partial"):
        return tier, None
    return None, reason


def replay_row(url: str, result, seconds: float) -> dict:
    if not isinstance(result, dict):
        return {"url": url, "status": "fail", "tier": None, "reason": "반환이 객체가 아님", "seconds": seconds}
    status = result.get("status")
    tier, reason = tier_and_reason(result)
    if status not in ("ok", "partial", "fail"):
        status = "fail"
        reason = reason or "status 없음"
    return {"url": url, "status": status, "tier": tier, "reason": reason, "seconds": seconds}


def read_urls(path: Path, limit: int | None) -> list[str]:
    if not path.is_file():
        die(f"URL 목록이 없습니다: {path}")
    if limit is not None and limit < 1:
        die("--limit 은 1 이상이어야 합니다")
    urls = []
    seen: set[str] = set()
    for line in read_text(path).splitlines():
        url = line.strip()
        if not url or url.startswith("#") or url in seen:
            continue
        seen.add(url)
        urls.append(url)
        if limit is not None and len(urls) >= limit:
            break
    if not urls:
        die(f"URL 이 없습니다: {path}")
    return urls


def summarize(results: list[dict]) -> dict:
    counts = Counter(row["status"] for row in results)
    total = len(results)
    by_tier: Counter = Counter()
    fail_domains: Counter = Counter()
    for row in results:
        if row["status"] in ("ok", "partial") and row.get("tier"):
            by_tier[row["tier"]] += 1
        elif row["status"] == "fail":
            fail_domains[domain_of(row["url"])] += 1
    return {
        "ok": counts["ok"],
        "partial": counts["partial"],
        "fail": counts["fail"],
        "ratios": {key: round(counts[key] / total, 4) for key in ("ok", "partial", "fail")},
        "by_tier": dict(by_tier),
        "fail_by_domain": dict(fail_domains),
    }


def replay(urls_path: Path, out: Path, limit: int | None, no_third_party: bool,
           fetch_script: Path | None) -> dict:
    script = (fetch_script or DEFAULT_FETCH).resolve()
    if not script.is_file():
        die(f"fetch.py 가 없습니다: {script}")
    urls = read_urls(urls_path, limit)
    previous = os.environ.get("MDR_NO_THIRD_PARTY")
    if no_third_party:
        os.environ["MDR_NO_THIRD_PARTY"] = "1"
    cwd = Path.cwd()
    inserted = None
    results = []
    last_hit: dict[str, float] = {}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                fetch, inserted = load_fetch(script)
                for url in urls:
                    host = domain_of(url)
                    if host != "(호스트 없음)" and host in last_hit:
                        gap = HOST_GAP_SECONDS - (time.monotonic() - last_hit[host])
                        if gap > 0:
                            time.sleep(gap)
                    started = time.monotonic()
                    try:
                        raw = fetch(url)
                    except Exception as exc:
                        raw = {"status": "fail", "final_url": url, "trace": [{"error": str(exc)}]}
                    seconds = round(time.monotonic() - started, 3)
                    if host != "(호스트 없음)":
                        last_hit[host] = time.monotonic()
                    results.append(replay_row(url, raw, seconds))
            finally:
                os.chdir(cwd)
    finally:
        if inserted and inserted in sys.path:
            sys.path.remove(inserted)
        if no_third_party:
            if previous is None:
                os.environ.pop("MDR_NO_THIRD_PARTY", None)
            else:
                os.environ["MDR_NO_THIRD_PARTY"] = previous
    payload = {"results": results, "summary": summarize(results)}
    dump_json(out, payload)
    summary = payload["summary"]
    print(f"ok {summary['ok']} / partial {summary['partial']} / fail {summary['fail']} "
          f"({len(results)}건) → {out}")
    return payload


def compare_runs(left: dict, right: dict) -> dict:
    """두 replay 결과의 ok/partial/fail 전환표와 URL 목록."""
    def index(doc: dict) -> dict[str, str]:
        rows = doc.get("results") if isinstance(doc, dict) else None
        if not isinstance(rows, list):
            die("replay JSON 에 results 배열이 없습니다")
        out = {}
        for row in rows:
            url = row.get("url") if isinstance(row, dict) else None
            status = row.get("status") if isinstance(row, dict) else None
            if not url or status not in ("ok", "partial", "fail"):
                die("replay 결과의 url·status 를 읽지 못했습니다")
            out[url] = status
        return out

    left_i, right_i = index(left), index(right)
    states = ("ok", "partial", "fail")
    transitions = {f"{src}->{dst}": [] for src in states for dst in states}
    for url in sorted(left_i.keys() & right_i.keys()):
        transitions[f"{left_i[url]}->{right_i[url]}"].append(url)
    return {"counts": {key: len(urls) for key, urls in transitions.items()},
            "transitions": transitions,
            "only_left": [url for url in left_i if url not in right_i],
            "only_right": [url for url in right_i if url not in left_i]}


def expect_die(fn) -> None:
    try:
        fn()
    except SystemExit as exc:
        if not str(exc):
            die("오류 메시지가 비어 있습니다")
        return
    die("오류로 끝나야 할 호출이 통과했습니다")


def demo() -> None:
    slept: list[float] = []
    original_sleep = time.sleep

    def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    time.sleep = fake_sleep
    cwd = Path.cwd()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "research_demo"
            (work / "audit").mkdir(parents=True)
            facts = [
                {"id": "F001", "claim": "a", "context": {"metric": "m", "entity": "Alpha Corp",
                                                         "geography": "KR", "period": "2024"}},
                {"id": "F002", "claim": "b", "context": {"metric": "m", "entity": "Alpha Corp",
                                                         "geography": "KR", "period": "2024"}},
                {"id": "F003", "claim": "c", "context": {"metric": "m", "entity": "  Beta  ",
                                                         "geography": "KR", "period": "2024"}},
                {"id": "F004", "claim": "d", "subject": "Gamma", "status": "confirmed"},
                {"kind": "evidence", "id": "E001"},
            ]
            write_text(work / "facts.jsonl", "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in facts))
            truth = build_truth(work, root / "truth" / "demo.json")
            assert [item["name"] for item in truth] == ["Alpha Corp", "Beta", "Gamma"]
            assert [item["fact_count"] for item in truth] == [2, 1, 1]
            assert sum(item["fact_count"] for item in truth) == 4

            broken = root / "broken"
            broken.mkdir()
            write_text(broken / "facts.jsonl", json.dumps({"id": "F009", "claim": "x"}) + "\n")
            expect_die(lambda: build_truth(broken, root / "no.json"))
            expect_die(lambda: build_truth(root / "missing", root / "no.json"))

            found_text = root / "found.txt"
            write_text(found_text, "alpha-corp\nalpha-corp\nExtra Co\n")
            scored = score(load_truth(root / "truth" / "demo.json"), load_found(found_text))
            assert scored["recall"] == {"found": 1, "total": 3, "ratio": 0.3333}
            assert [row["name"] for row in scored["missed"]] == ["Beta", "Gamma"]
            assert scored["extra"] == [{"name": "Extra Co"}]
            assert scored["limitation"] == LIMITATION

            universe = root / "audit" / "universe.md"
            write_text(universe, "\n".join([
                "| 대상 | 별칭 | 목록 출처 | 포함/제외 | 사유 |",
                "| --- | --- | --- | --- | --- |",
                "| Beta | 베타 | 합성 | 포함 | |",
                "| Gamma | | 합성 | 제외 | 범위 밖 |",
                "| Delta | Delta Inc | 합성 | 포함 | |",
            ]) + "\n")
            from_table = load_found(universe)
            assert [item["name"] for item in from_table] == ["Beta", "Delta"]
            assert "베타" in from_table[0]["aliases"]
            table_score = score(truth, from_table)
            assert table_score["recall"]["found"] == 1
            assert [row["name"] for row in table_score["extra"]] == ["Delta"]

            log = [
                {"url": "https://opened.example/a", "tier": "direct", "http_status": 200,
                 "snapshot_path": "audit/a.txt"},
                {"url": "https://opened.example/a", "tier": "wayback", "failure_reason": "no snapshot"},
                {"url": "https://blocked.example/z", "tier": "jina", "http_status": 403,
                 "snapshot_path": "audit/z.txt"},
                {"url": "https://closed.example/b", "tier": "direct", "http_status": 403,
                 "failure_reason": "http 403"},
                {"url": "https://closed.example/b", "tier": "jina", "failure_reason": "timeout"},
                {"kind": "attempt", "url": "https://later.example/c", "status": "ok",
                 "snapshot_path": "audit/c.txt"},
                {"kind": "final", "url": "https://later.example/c", "status": "fail"},
                {"kind": "attempt", "url": "https://fine.example/d", "status": "fail",
                 "failure_reason": "x"},
                {"kind": "final", "url": "https://fine.example/d", "status": "ok"},
            ]
            write_text(work / "audit" / "fetch-log.jsonl",
                       "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in log))
            urls = failed_urls([work], root / "urls" / "demo.txt")
            assert urls == ["https://blocked.example/z", "https://closed.example/b", "https://later.example/c"]
            expect_die(lambda: failed_urls([broken], root / "urls" / "no.txt"))

            left = {"results": [
                {"url": "https://closed.example/b", "status": "fail", "tier": None, "reason": "x", "seconds": 0.1},
                {"url": "https://fine.example/d", "status": "ok", "tier": "direct", "reason": None, "seconds": 0.1},
            ]}
            right = {"results": [
                {"url": "https://closed.example/b", "status": "ok", "tier": "jina", "reason": None, "seconds": 0.2},
                {"url": "https://only.example/e", "status": "fail", "tier": None, "reason": "y", "seconds": 0.1},
            ]}
            diff = compare_runs(left, right)
            assert diff["counts"]["fail->ok"] == 1
            assert diff["counts"]["ok->ok"] == 0
            assert diff["transitions"]["fail->ok"] == ["https://closed.example/b"]
            assert diff["only_right"] == ["https://only.example/e"]
            assert diff["only_left"] == ["https://fine.example/d"]

            stub = root / "stub"
            stub.mkdir()
            write_text(stub / "fetch.py", "\n".join([
                "import os",
                "from pathlib import Path",
                "def fetch(url, success_selectors=None, expected_title=None):",
                "    Path('audit').mkdir(exist_ok=True)",
                "    Path('audit/marker.txt').write_text('x', encoding='utf-8')",
                "    if os.environ.get('MDR_NO_THIRD_PARTY') != '1':",
                "        return {'status': 'fail', 'final_url': url, 'trace': [{'tier': 'direct', 'fail': 'env'}]}",
                "    if url.endswith('/fail'):",
                "        return {'status': 'fail', 'final_url': url,",
                "                'trace': [{'tier': 'direct', 'fail': 'stub-fail'}, {'tier': 'jina', 'error': 'stub-jina'}]}",
                "    if url.endswith('/partial'):",
                "        return {'status': 'partial', 'final_url': url,",
                "                'trace': [{'tier': 'jina', 'verdict': 'partial', 'reason': 'thin'}]}",
                "    return {'status': 'ok', 'final_url': url, 'trace': [{'tier': 'direct', 'verdict': 'ok'}]}",
                "",
            ]))
            write_text(root / "urls" / "replay.txt", "\n".join([
                "https://a.example/ok",
                "https://b.example/partial",
                "https://a.example/fail",
            ]) + "\n")
            os.environ.pop("MDR_NO_THIRD_PARTY", None)
            ran = replay(root / "urls" / "replay.txt", root / "runs" / "stub.json",
                         None, True, stub / "fetch.py")
            assert os.environ.get("MDR_NO_THIRD_PARTY") is None
            assert [row["status"] for row in ran["results"]] == ["ok", "partial", "fail"]
            assert [row["tier"] for row in ran["results"]] == ["direct", "jina", None]
            assert ran["results"][2]["reason"] == "stub-jina"
            assert ran["summary"]["ok"] == 1 and ran["summary"]["partial"] == 1 and ran["summary"]["fail"] == 1
            assert ran["summary"]["by_tier"] == {"direct": 1, "jina": 1}
            assert ran["summary"]["fail_by_domain"] == {"a.example": 1}
            assert slept and abs(slept[0] - HOST_GAP_SECONDS) < 0.05
            assert not (cwd / "audit" / "marker.txt").exists()
            limited = replay(root / "urls" / "replay.txt", root / "runs" / "limit.json",
                             2, True, stub / "fetch.py")
            assert len(limited["results"]) == 2
    finally:
        time.sleep = original_sleep
        os.chdir(cwd)
    print("recall_eval demo OK")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="대상 재현율과 열람 성공률을 잰다")
    sub = parser.add_subparsers(dest="cmd", required=True)

    build = sub.add_parser("build-truth", help="사실 대장에서 정답 대상을 뽑는다")
    build.add_argument("work_dir")
    build.add_argument("--out", required=True)

    scoring = sub.add_parser("score", help="정답 대비 재현율을 계산한다")
    scoring.add_argument("--truth", required=True)
    scoring.add_argument("--found", required=True)

    failed = sub.add_parser("failed-urls", help="끝내 실패한 URL 을 뽑는다")
    failed.add_argument("work_dirs", nargs="+")
    failed.add_argument("--out", required=True)

    play = sub.add_parser("replay", help="실패 URL 을 fetch 로 한 번씩 다시 연다")
    play.add_argument("urls")
    play.add_argument("--out", required=True)
    play.add_argument("--limit", type=int)
    play.add_argument("--no-third-party", action="store_true")
    play.add_argument("--fetch-script")

    diff = sub.add_parser("compare", help="두 replay 의 상태 전환을 비교한다")
    diff.add_argument("left")
    diff.add_argument("right")

    sub.add_parser("demo", help="네트워크 없이 합성 자료로 점검한다")

    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.cmd == "demo":
        demo()
    elif args.cmd == "build-truth":
        build_truth(Path(args.work_dir), Path(args.out))
    elif args.cmd == "score":
        payload = score(load_truth(Path(args.truth)), load_found(Path(args.found)))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.cmd == "failed-urls":
        failed_urls([Path(item) for item in args.work_dirs], Path(args.out))
    elif args.cmd == "replay":
        script = Path(args.fetch_script) if args.fetch_script else None
        replay(Path(args.urls), Path(args.out), args.limit, args.no_third_party, script)
    elif args.cmd == "compare":
        print(json.dumps(compare_runs(load_json(Path(args.left)), load_json(Path(args.right))),
                         ensure_ascii=False, indent=2))
    else:
        die(f"알 수 없는 명령: {args.cmd}")


if __name__ == "__main__":
    main()
