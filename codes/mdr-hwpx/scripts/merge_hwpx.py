"""모듈 HWPX 여러 개를 같은 템플릿 전제로 한 문서로 합친다.

header.xml 바이트가 같아야 하고, 첫 모듈의 secPr 만 남긴다. 이후 모듈은 첫 문단에
pageBreak=1 을 넣고 BinData/imageN 을 전역 순번으로 다시 붙인다.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SEC_HEAD_RE = re.compile(r"<\?xml.*?<hs:sec[^>]*>", re.S)
SEC_COL_RUN_RE = re.compile(
    r"<hp:run\b[^>]*>\s*<hp:secPr\b.*?</hp:secPr>\s*"
    r"(?:<hp:ctrl>\s*<hp:colPr\b.*?</hp:ctrl>\s*)?"
    r"</hp:run>",
    re.S,
)
IMAGE_ITEM_RE = re.compile(r'<opf:item\s+id="(image\d+)"[^>]*/\s*>')
BIN_NAME_RE = re.compile(r"BinData/(image(\d+))\.([A-Za-z0-9]+)$")


def _split_section(sec: str) -> tuple[str, str]:
    """section0.xml 을 `<?xml…><hs:sec>` 머리와 본문(닫는 태그 제외)으로 가른다."""
    m = SEC_HEAD_RE.match(sec)
    if not m:
        raise ValueError("section0.xml 머리가 없음")
    body = re.sub(r"</hs:sec>\s*$", "", sec[m.end():])
    return m.group(0), body


def _strip_sec_col_run(body: str) -> str:
    """이후 모듈의 secPr/colPr 이 들어 있는 run 을 제거한다."""
    n, k = SEC_COL_RUN_RE.subn("", body, count=1)
    if k:
        return n
    n = re.sub(r"<hp:secPr\b.*?</hp:secPr>", "", body, count=1, flags=re.S)
    n = re.sub(r"<hp:ctrl>\s*<hp:colPr\b.*?</hp:ctrl>", "", n, count=1, flags=re.S)
    return n


def _first_para_pagebreak(body: str) -> str:
    """모듈 첫 문단의 pageBreak='0' 만 '1' 로 바꾼다(표 안 문단은 건드리지 않음)."""
    m = re.search(r"<hp:p\b[^>]*>", body)
    if not m:
        return body
    tag = m.group(0)
    if 'pageBreak="0"' in tag:
        tag = tag.replace('pageBreak="0"', 'pageBreak="1"', 1)
    elif "pageBreak=" not in tag:
        tag = tag[:-1] + ' pageBreak="1">'
    return body[: m.start()] + tag + body[m.end():]


def _hashkey(data: bytes) -> str:
    import base64
    return base64.b64encode(hashlib.md5(data).digest()).decode("ascii")


def _collect_images(zf: zipfile.ZipFile, hpf: str) -> list[dict]:
    """BinData/imageN.EXT 를 번호순으로 모으고, 짝이 되는 content.hpf 항목을 붙인다."""
    by_id: dict[str, list[str]] = {}
    for m in IMAGE_ITEM_RE.finditer(hpf):
        by_id.setdefault(m.group(1), []).append(m.group(0))

    found: list[tuple[int, str, str, str]] = []
    for name in zf.namelist():
        m = BIN_NAME_RE.match(name.replace("\\", "/"))
        if m:
            found.append((int(m.group(2)), m.group(1), m.group(3), name))
    found.sort()

    out: list[dict] = []
    for num, iid, ext, name in found:
        data = zf.read(name)
        file_key = _hashkey(data)
        chosen = None
        for raw in by_id.get(iid, []):
            km = re.search(r'hashkey="([^"]*)"', raw)
            if km and km.group(1) == file_key:
                chosen = raw
                break
        if chosen is None and by_id.get(iid):
            chosen = by_id[iid][-1]
        key = file_key
        if chosen:
            km = re.search(r'hashkey="([^"]*)"', chosen)
            if km:
                key = km.group(1)
        mt = "image/jpeg" if ext.lower() in ("jpg", "jpeg") else f"image/{ext.lower()}"
        if chosen:
            mm = re.search(r'media-type="([^"]*)"', chosen)
            if mm:
                mt = mm.group(1)
        out.append({
            "old_id": iid,
            "old_n": num,
            "ext": ext,
            "data": data,
            "item_xml": chosen,
            "hashkey": key,
            "media": mt,
        })
    return out


def _rewrite_item(img: dict, new_id: str) -> str:
    """opf:item 의 id/href 만 새 번호로 바꾸고 hashkey 는 그대로 둔다."""
    ext = img["ext"]
    raw = img["item_xml"]
    if raw:
        xml = re.sub(r'id="image\d+"', f'id="{new_id}"', raw, count=1)
        xml = re.sub(
            r'href="BinData/image\d+\.[^"]+"',
            f'href="BinData/{new_id}.{ext}"',
            xml,
            count=1,
        )
        return xml
    return (
        f'<opf:item id="{new_id}" href="BinData/{new_id}.{ext}" '
        f'media-type="{img["media"]}" isEmbeded="1" hashkey="{img["hashkey"]}"/>'
    )


def _remap_refs(xml: str, old_to_new: dict[int, int]) -> str:
    """binaryItemIDRef='imageN' 을 임시 토큰 경유로 바꿔 이미 바뀐 번호를 다시 안 건드린다."""
    for old in sorted(old_to_new, reverse=True):
        token = f"__MERGEIMG_{old}__"
        xml = xml.replace(f'binaryItemIDRef="image{old}"', f'binaryItemIDRef="{token}"')
    for old, new in old_to_new.items():
        token = f"__MERGEIMG_{old}__"
        xml = xml.replace(f'binaryItemIDRef="{token}"', f'binaryItemIDRef="image{new}"')
    return xml


def _read_hwpx(path: Path) -> dict:
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        files = {n.replace("\\", "/"): z.read(n) for n in names}
        header = files.get("Contents/header.xml")
        section = files.get("Contents/section0.xml")
        hpf = files.get("Contents/content.hpf")
        if header is None or section is None or hpf is None:
            raise ValueError(f"HWPX 구성 부족: {path}")
        images = _collect_images(z, hpf.decode("utf-8"))
    return {"path": path, "files": files, "header": header, "section": section,
            "hpf": hpf, "images": images}


def merge(paths, out) -> dict:
    """같은 템플릿으로 만든 모듈 hwpx 들을 한 파일로 합친다."""
    paths = [Path(p) for p in paths]
    out_path = Path(out)
    if not paths:
        raise ValueError("합칠 모듈이 없음")
    mods = [_read_hwpx(p) for p in paths]
    for m in mods[1:]:
        if m["header"] != mods[0]["header"]:
            raise ValueError(f"header.xml 이 다름: {mods[0]['path']} vs {m['path']}")

    head, first_body = _split_section(mods[0]["section"].decode("utf-8"))
    bodies = [first_body]
    all_images: list[dict] = []
    next_n = 1

    def take_images(mod: dict, body: str) -> str:
        nonlocal next_n
        mapping: dict[int, int] = {}
        for img in mod["images"]:
            new_n = next_n
            next_n += 1
            mapping[img["old_n"]] = new_n
            img["new_id"] = f"image{new_n}"
            img["new_n"] = new_n
            all_images.append(img)
        return _remap_refs(body, mapping)

    bodies[0] = take_images(mods[0], first_body)
    for mod in mods[1:]:
        _, body = _split_section(mod["section"].decode("utf-8"))
        body = _strip_sec_col_run(body)
        body = _first_para_pagebreak(body)
        bodies.append(take_images(mod, body))

    section = head + "".join(bodies) + "</hs:sec>"

    hpf = mods[0]["hpf"].decode("utf-8")
    hpf = IMAGE_ITEM_RE.sub("", hpf)
    items = "".join(_rewrite_item(img, img["new_id"]) for img in all_images)
    if '<opf:item id="section0"' in hpf:
        hpf = hpf.replace('<opf:item id="section0"', items + '<opf:item id="section0"', 1)
    else:
        hpf = hpf.replace("</opf:manifest>", items + "</opf:manifest>", 1)

    first = mods[0]["files"]
    skip = {"mimetype", "Contents/section0.xml", "Contents/content.hpf"}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        mime = first.get("mimetype", b"application/hwp+zip")
        z.writestr("mimetype", mime, zipfile.ZIP_STORED)
        for name, data in first.items():
            if name in skip or name.startswith("BinData/"):
                continue
            z.writestr(name, data)
        z.writestr("Contents/section0.xml", section.encode("utf-8"))
        z.writestr("Contents/content.hpf", hpf.encode("utf-8"))
        for img in all_images:
            z.writestr(f"BinData/{img['new_id']}.{img['ext']}", img["data"])

    return {
        "ok": True,
        "out": str(out_path),
        "artifacts": [str(out_path)],
        "modules": len(mods),
        "images": len(all_images),
    }


def _mini_png(color: tuple[int, int, int]) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color).save(buf, "PNG")
    return buf.getvalue()


def _write_min_hwpx(path: Path, header: str, title: str, png: bytes) -> None:
    """템플릿 없이 최소 header/section/hpf + image1 로 데모용 hwpx 를 조립한다."""
    sec = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        '<hs:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
        'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
        'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core">'
        '<hp:p id="0" paraPrIDRef="46" styleIDRef="0" pageBreak="0" '
        'columnBreak="0" merged="0">'
        '<hp:run charPrIDRef="23">'
        '<hp:secPr id="" textDirection="HORIZONTAL">'
        '<hp:pagePr width="59528" height="84186">'
        '<hp:margin header="2835" footer="2835" left="5669" right="5669" '
        'top="4252" bottom="4252"/></hp:pagePr></hp:secPr>'
        '<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" '
        'colCount="1" sameSz="1" sameGap="0"/></hp:ctrl></hp:run>'
        f'<hp:run charPrIDRef="23"><hp:t>{title}</hp:t></hp:run></hp:p>'
        '<hp:p id="0" paraPrIDRef="50" styleIDRef="0" pageBreak="0" '
        'columnBreak="0" merged="0">'
        '<hp:run charPrIDRef="27">'
        '<hc:img binaryItemIDRef="image1" bright="0" contrast="0" '
        'effect="REAL_PIC" alpha="0"/></hp:run></hp:p>'
        "</hs:sec>"
    )
    key = _hashkey(png)
    hpf = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<opf:package xmlns:opf="http://www.idpf.org/2007/opf/">'
        "<opf:manifest>"
        '<opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>'
        f'<opf:item id="image1" href="BinData/image1.PNG" media-type="image/png" '
        f'isEmbeded="1" hashkey="{key}"/>'
        '<opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>'
        "</opf:manifest></opf:package>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", "application/hwp+zip", zipfile.ZIP_STORED)
        z.writestr("Contents/header.xml", header.encode("utf-8"))
        z.writestr("Contents/section0.xml", sec.encode("utf-8"))
        z.writestr("Contents/content.hpf", hpf.encode("utf-8"))
        z.writestr("BinData/image1.PNG", png)


def demo() -> None:
    """작은 hwpx 두 개를 메모리에서 만들어 합친 뒤 단락·pageBreak·이미지 재번호·header 불일치를 확인한다."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        a, b, out = td / "a.hwpx", td / "b.hwpx", td / "merged.hwpx"
        header = '<?xml version="1.0"?><hh:head>SAME</hh:head>'
        _write_min_hwpx(a, header, "Module A", _mini_png((255, 0, 0)))
        _write_min_hwpx(b, header, "Module B", _mini_png((0, 255, 0)))
        r = merge([a, b], out)
        assert r["ok"] and r["modules"] == 2 and r["images"] == 2, r
        with zipfile.ZipFile(out) as z:
            assert z.infolist()[0].filename == "mimetype"
            assert z.infolist()[0].compress_type == zipfile.ZIP_STORED
            names = [n.replace("\\", "/") for n in z.namelist()]
            assert "BinData/image1.PNG" in names and "BinData/image2.PNG" in names
            sec = z.read("Contents/section0.xml").decode("utf-8")
            hpf = z.read("Contents/content.hpf").decode("utf-8")
        assert len(re.findall(r"<hp:p ", sec)) == 4, sec[:400]
        assert len(re.findall(r'pageBreak="1"', sec)) == 1
        assert 'binaryItemIDRef="image1"' in sec and 'binaryItemIDRef="image2"' in sec
        assert sec.count("<hp:secPr") == 1 and sec.count("<hp:colPr") == 1
        assert 'id="image1"' in hpf and 'id="image2"' in hpf
        bad = td / "bad.hwpx"
        _write_min_hwpx(bad, '<?xml version="1.0"?><hh:head>OTHER</hh:head>',
                        "X", _mini_png((0, 0, 255)))
        try:
            merge([a, bad], td / "nope.hwpx")
            raise AssertionError("header 불일치가 통과됨")
        except ValueError as e:
            assert str(e).startswith("header.xml 이 다름"), e


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--demo" in args:
        demo()
        print("demo ok")
        return 0
    out = None
    paths: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--out":
            if i + 1 >= len(args):
                print("usage: merge_hwpx.py <m1.hwpx> ... --out <out.hwpx>", file=sys.stderr)
                return 1
            out = args[i + 1]
            i += 2
            continue
        paths.append(args[i])
        i += 1
    if not paths or not out:
        print("usage: merge_hwpx.py <m1.hwpx> ... --out <out.hwpx>", file=sys.stderr)
        return 1
    try:
        result = merge(paths, out)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
