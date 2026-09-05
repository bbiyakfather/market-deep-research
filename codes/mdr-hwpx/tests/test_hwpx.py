"""test_hwpx.py — mdr-hwpx 구조 검사 + (한글 있으면) export/grade 스모크.

표준 라이브러리 unittest. 외부 프레임워크 없음.
스크립트 결함은 이 파일이 고치지 않는다 — 테스트가 실패로 드러낸다.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_ROOT / "scripts"
TEMPLATE = SKILL_ROOT / "assets" / "forms" / "navion-2026.hwpx"
PROFILE = SKILL_ROOT / "profiles" / "navion-2026.json"
HWP_EXE = Path(r"C:/Program Files (x86)/Hnc/Office 2024/HOffice130/Bin/Hwp.exe")

sys.path.insert(0, str(SCRIPTS))
import merge_hwpx  # noqa: E402
import export_pdf  # noqa: E402

_CLI_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}

# 프로필 실측 ID (navion-2026)
TITLE_CHAR, TITLE_PARA = 23, 46
BODY1_CHAR, BODY1_PARA = 27, 50
CAPTION_CHAR, CAPTION_PARA = 32, 52
TH_CHAR, TH_PARA = 38, 55
BODY_W = 48188
PX2HWP = 75
IMG_W, IMG_H = 200, 100


def _run(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    """scripts/<name> CLI 를 utf-8 로 실행(Windows cp949 콘솔 대비)."""
    return subprocess.run(
        [sys.executable, str(SCRIPTS / args[0]), *args[1:]],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=_CLI_ENV, timeout=timeout,
    )


def _json_last_line(text: str) -> dict:
    for line in reversed(text.splitlines()):
        s = line.strip()
        if s.startswith("{") and s.endswith("}"):
            return json.loads(s)
    raise AssertionError(f"JSON 한 줄 없음:\n{text[-800:]}")


def _zip_files(path: Path) -> tuple[list, dict[str, bytes]]:
    with zipfile.ZipFile(path) as z:
        infos = list(z.infolist())
        files = {n.replace("\\", "/"): z.read(n) for n in z.namelist()}
    return infos, files


def _xml(files: dict[str, bytes], name: str) -> str:
    return files[name].decode("utf-8")


def _n_para(xml: str) -> int:
    return len(re.findall(r"<hp:p\b", xml))


def _write_png(path: Path, w: int = IMG_W, h: int = IMG_H, color=(20, 80, 180)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (w, h), color).save(path, "PNG")


def _big_table_md(n: int = 60) -> str:
    lines = ["<표> 큰표", "", "| 열A | 열B |", "|---|---|"]
    for i in range(n):
        lines.append(f"| r{i:02d} | d{i:02d} |")
    lines += ["", "* 출처 : 큰표출처"]
    return "\n".join(lines)


def _manuscript_text(title: str, img_name: str, missing: str | None = None) -> str:
    parts = [
        f"# {title}",
        "## 2단계제목",
        "### 3단계제목",
        "#### 4단계제목",
        "",
        "① 짧은제목",
        "",
        "① 1단계, 프로젝트 설계 : 설명이 길게 붙은 원 숫자는 제목이 아니라 본문이어야 한다 A & B",
        "",
        "❍ 본문 **굵게텍스트** 와 각주<sup>1)</sup>",
        "",
        "- 하위 근거 문단",
        "",
        "<sup>1)</sup> 각주 정의 문단",
        "",
        "<표> 작은표",
        "",
        "| 구분 | 내용 |",
        "|---|---|",
        "| 가 | 나 |",
        "",
        "* 출처 : 테스트출처",
        "",
        f"![]({img_name})",
        "",
        "[그림] 작은 그림 캡션",
        "",
        _big_table_md(60),
        "",
    ]
    if missing:
        parts += [f"![]({missing})", ""]
    return "\n".join(parts) + "\n"


def _write_header_plus_one_byte(src: Path, dest: Path) -> None:
    """한 모듈 header.xml 을 1바이트 바꾼 사본 hwpx 를 만든다."""
    with zipfile.ZipFile(src) as zin:
        items = [(info, zin.read(info.filename)) for info in zin.infolist()]
    with zipfile.ZipFile(dest, "w") as zout:
        for info, data in items:
            name = info.filename.replace("\\", "/")
            if name == "Contents/header.xml":
                data = data + b"X"
            if name == "mimetype":
                zout.writestr(name, data, zipfile.ZIP_STORED)
            else:
                zout.writestr(name, data, zipfile.ZIP_DEFLATED)


class HwpxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._td = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._td.name)
        cls.ms1_dir = cls.tmp / "ms1"
        cls.ms1_dir.mkdir()
        cls.ms1_png = cls.ms1_dir / "small.png"
        _write_png(cls.ms1_png, color=(20, 80, 180))
        cls.ms1 = cls.ms1_dir / "원고.md"
        cls.ms1.write_text(
            _manuscript_text("모듈1제목", "small.png", missing="missing.png"),
            encoding="utf-8",
        )
        cls.ms2_dir = cls.tmp / "ms2"
        cls.ms2_dir.mkdir()
        _write_png(cls.ms2_dir / "small.png", color=(180, 40, 20))
        cls.ms2 = cls.ms2_dir / "원고.md"
        cls.ms2.write_text(
            _manuscript_text("모듈2제목", "small.png"),
            encoding="utf-8",
        )
        with zipfile.ZipFile(TEMPLATE) as z:
            hdr = z.read("Contents/header.xml").decode("utf-8")
        cls.orig_item_cnt = int(
            re.search(r'<hh:charProperties itemCnt="(\d+)"', hdr).group(1)
        )
        cls.hwpx1 = None
        cls.merged = None

    @classmethod
    def tearDownClass(cls) -> None:
        cls._td.cleanup()

    def test_01_build_structure(self) -> None:
        out = self.tmp / "모듈1.hwpx"
        r = _run(
            "build_hwpx.py", "build", str(self.ms1),
            "--template", str(TEMPLATE),
            "--profile", "navion-2026",
            "--out", str(out),
        )
        self.assertEqual(r.returncode, 0, r.stderr + "\n" + r.stdout)
        result = _json_last_line(r.stdout)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["images"], 1, result)
        self.assertIn("missing.png", result["skipped_images"], result)
        type(self).hwpx1 = out

        infos, files = _zip_files(out)
        self.assertEqual(infos[0].filename.replace("\\", "/"), "mimetype")
        self.assertEqual(infos[0].compress_type, zipfile.ZIP_STORED)
        for name in ("Contents/header.xml", "Contents/section0.xml", "Contents/content.hpf"):
            self.assertIn(name, files, list(files))
        self.assertIn("BinData/image1.PNG", files)
        self.assertEqual(
            sum(1 for n in files if n.startswith("BinData/")), 1, list(files),
        )

        hpf = _xml(files, "Contents/content.hpf")
        img_items = re.findall(r'<opf:item\s+id="(image\d+)"([^>]*)>', hpf)
        self.assertEqual([i[0] for i in img_items], ["image1"], hpf[-600:])
        self.assertIn("hashkey=", img_items[0][1], img_items)
        # 양식 사본의 예시 이미지 항목(원본 hashkey)은 남아 있으면 안 된다
        tpl_hpf = zipfile.ZipFile(TEMPLATE).read("Contents/content.hpf").decode("utf-8")
        tpl_keys = re.findall(r'id="image\d+"[^>]*hashkey="([^"]+)"', tpl_hpf)
        for key in tpl_keys:
            self.assertNotIn(key, hpf, f"템플릿 예시 hashkey 잔존: {key}")

        header = _xml(files, "Contents/header.xml")
        sec = _xml(files, "Contents/section0.xml")

        first_p = re.search(r"<hp:p\b[^>]*>.*?</hp:p>", sec, re.S)
        self.assertIsNotNone(first_p)
        first_run = re.search(r"<hp:run\b[^>]*>.*?</hp:run>", first_p.group(0), re.S)
        self.assertIsNotNone(first_run)
        self.assertIn("<hp:secPr", first_run.group(0))

        self.assertIn(f'charPrIDRef="{TITLE_CHAR}"', sec)
        self.assertIn(f'paraPrIDRef="{TITLE_PARA}"', sec)
        self.assertIn(f'charPrIDRef="{BODY1_CHAR}"', sec)
        self.assertIn(f'paraPrIDRef="{BODY1_PARA}"', sec)
        self.assertIn(f'charPrIDRef="{CAPTION_CHAR}"', sec)
        self.assertIn(f'paraPrIDRef="{CAPTION_PARA}"', sec)
        self.assertIn(f'charPrIDRef="{TH_CHAR}"', sec)
        self.assertIn(f'paraPrIDRef="{TH_PARA}"', sec)

        new_cnt = int(re.search(r'<hh:charProperties itemCnt="(\d+)"', header).group(1))
        self.assertEqual(new_cnt, self.orig_item_cnt + 1, new_cnt)
        bold_id = self.orig_item_cnt
        bold_pr = re.search(rf'<hh:charPr id="{bold_id}".*?</hh:charPr>', header, re.S)
        self.assertIsNotNone(bold_pr, header[-400:])
        self.assertIn("<hh:bold/>", bold_pr.group(0))
        self.assertRegex(
            sec,
            rf'<hp:run charPrIDRef="{bold_id}"><hp:t>굵게텍스트</hp:t></hp:run>',
        )

        tables = re.findall(r"<hp:tbl\b.*?</hp:tbl>", sec, re.S)
        self.assertEqual(len(tables), 2, f"표 {len(tables)}개")
        for tbl in tables:
            self.assertIn('pageBreak="CELL"', tbl)
            self.assertIn('repeatHeader="1"', tbl)
            self.assertIn('colSpan="2"', tbl)
            self.assertIn('borderFillIDRef="16"', tbl)
            self.assertIn('side="TOP"', tbl)
        self.assertIn('treatAsChar="1"', tables[0])
        self.assertIn('treatAsChar="0"', tables[1])

        pic = re.search(r"<hp:pic\b.*?</hp:pic>", sec, re.S)
        self.assertIsNotNone(pic)
        pic_xml = pic.group(0)
        self.assertIn('side="BOTTOM"', pic_xml)
        clip = re.search(
            r'<hp:imgClip left="0" right="(\d+)" top="0" bottom="(\d+)"/>', pic_xml,
        )
        self.assertIsNotNone(clip, pic_xml)
        self.assertEqual(int(clip.group(1)), IMG_W * PX2HWP)
        self.assertEqual(int(clip.group(2)), IMG_H * PX2HWP)
        org = re.search(r'<hp:orgSz width="(\d+)" height="(\d+)"/>', pic_xml)
        self.assertEqual(int(org.group(1)), IMG_W * PX2HWP)
        self.assertEqual(int(org.group(2)), IMG_H * PX2HWP)
        cur = re.search(r'<hp:curSz width="(\d+)" height="(\d+)"/>', pic_xml)
        self.assertEqual(int(cur.group(1)), BODY_W)

        texts = re.findall(r"<hp:t>(.*?)</hp:t>", sec, re.S)
        self.assertFalse(
            any(t.startswith(("❍ ", "○ ", "- ")) for t in texts),
            [t for t in texts if t.startswith(("❍ ", "○ ", "- "))],
        )
        self.assertTrue(all("❍" not in t and "○" not in t for t in texts), texts)
        self.assertIn("A &amp; B", sec)
        self.assertNotIn("A & B", sec)

    def test_02_split_outline(self) -> None:
        report = self.tmp / "report.md"
        assets = self.tmp / "assets"
        _write_png(assets / "x.png", w=16, h=16)
        report.write_text(
            "서문 단락이다.\n\n"
            "# Ⅱ. 가\n\n"
            "![x](assets/x.png)\n\n"
            "[그림] 엑스\n\n"
            "<표> 표캡션\n\n"
            "| a | b |\n|---|---|\n| 1 | 2 |\n\n"
            "# Ⅲ. 나\n\n"
            "본문 나.\n",
            encoding="utf-8",
        )
        out_dir = self.tmp / "manuscript"
        r = _run("build_hwpx.py", "split", str(report), "--out", str(out_dir))
        self.assertEqual(r.returncode, 0, r.stderr + "\n" + r.stdout)
        names = sorted(p.name for p in out_dir.glob("*.md"))
        self.assertEqual(names, ["00_서문.md", "Ⅱ_가.md", "Ⅲ_나.md"], names)
        ga = (out_dir / "Ⅱ_가.md").read_text(encoding="utf-8")
        self.assertIn("](../assets/x.png)", ga)
        self.assertNotIn("](assets/x.png)", ga)
        seomun = (out_dir / "00_서문.md").read_text(encoding="utf-8")
        self.assertIn("서문 단락이다.", seomun)

        mods = [out_dir / "00_서문.md", out_dir / "Ⅱ_가.md", out_dir / "Ⅲ_나.md"]
        r2 = _run("build_hwpx.py", "outline", *[str(p) for p in mods], "--json")
        self.assertEqual(r2.returncode, 0, r2.stderr + "\n" + r2.stdout)
        info = json.loads(r2.stdout)
        self.assertIsInstance(info, list)
        self.assertEqual(len(info), 3, info)
        by_name = {Path(x["file"]).name: x for x in info}
        self.assertEqual(len(by_name["00_서문.md"]["titles"]), 0)
        self.assertEqual(len(by_name["Ⅱ_가.md"]["titles"]), 1)
        self.assertEqual(by_name["Ⅱ_가.md"]["titles"][0]["text"], "Ⅱ. 가")
        self.assertEqual(by_name["Ⅱ_가.md"]["tables"], ["표캡션"])
        self.assertEqual(by_name["Ⅱ_가.md"]["figures"], ["엑스"])
        self.assertEqual(len(by_name["Ⅲ_나.md"]["titles"]), 1)
        self.assertEqual(by_name["Ⅲ_나.md"]["titles"][0]["text"], "Ⅲ. 나")

    def test_split_rejects_no_parts_and_count_mismatch_before_writing(self) -> None:
        report = self.tmp / "core.md"
        out_dir = self.tmp / "split-failure"
        cases = [
            ("# Executive Summary\n본문\n## 조사 개요\n본문\n", [], "로마숫자 부 헤딩 0개"),
            ("# Ⅰ. 요약\n본문\n", ["--expect-parts", "11"], "부 수 불일치"),
            ("# Ⅰ. 요약\n본문\n", ["--expect-parts", "0"], "부 수 불일치"),
            ("# Ⅰ. 요약\nA\n# Ⅰ. 요약\nB\n", ["--expect-parts", "2"], "파일명 중복"),
        ]
        for text, args, message in cases:
            with self.subTest(message=message, args=args):
                report.write_text(text, encoding="utf-8")
                result = _run("build_hwpx.py", "split", str(report), "--out", str(out_dir), *args)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(message, result.stderr)
                self.assertFalse(out_dir.exists(), "오류가 있는 원고는 출력 전에 거부")
        out_dir.mkdir()
        existing = out_dir / "00_서문.md"
        existing.write_bytes(b"previous output")
        report.write_text("# Executive Summary\n본문", encoding="utf-8")
        result = _run("build_hwpx.py", "split", str(report), "--out", str(out_dir))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(existing.read_bytes(), b"previous output")

    def test_split_core_eleven_parts_excludes_preface(self) -> None:
        report = self.tmp / "core-mapped.md"
        roman = "ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪ"
        report.write_text("표지 메타\n\n" + "\n".join(
            f"## {key}. 장\n본문 {key}\n### 하위 축\n축 본문\n" for key in roman), encoding="utf-8")
        out_dir = self.tmp / "eleven-parts"
        result = _run("build_hwpx.py", "split", str(report), "--out", str(out_dir), "--expect-parts", "11")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(list(out_dir.glob("*.md"))), 12)
        self.assertEqual((out_dir / "00_서문.md").read_text(encoding="utf-8").strip(), "표지 메타")
        for key in roman:
            body = (out_dir / f"{key}_장.md").read_text(encoding="utf-8")
            self.assertTrue(body.startswith(f"# {key}. 장\n"))
            self.assertIn("## 하위 축", body)

    def test_03_form_probe(self) -> None:
        r = _run(
            "form_probe.py", str(TEMPLATE),
            "--profile", str(PROFILE),
        )
        self.assertEqual(r.returncode, 0, r.stderr + "\n" + r.stdout)

        bad = self.tmp / "bad-profile.json"
        data = json.loads(PROFILE.read_text(encoding="utf-8"))
        data["styles"]["title"][0] = 9999
        bad.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        r2 = _run(
            "form_probe.py", str(TEMPLATE),
            "--profile", str(bad),
        )
        self.assertEqual(r2.returncode, 1, r2.stderr + "\n" + r2.stdout)
        combined = r2.stdout + r2.stderr
        self.assertIn("9999", combined)

    def test_04_merge(self) -> None:
        m1 = self.tmp / "mod1.hwpx"
        m2 = self.tmp / "mod2.hwpx"
        r1 = _run(
            "build_hwpx.py", "build", str(self.ms1),
            "--template", str(TEMPLATE), "--profile", "navion-2026",
            "--out", str(m1),
        )
        r2 = _run(
            "build_hwpx.py", "build", str(self.ms2),
            "--template", str(TEMPLATE), "--profile", "navion-2026",
            "--out", str(m2),
        )
        self.assertEqual(r1.returncode, 0, r1.stderr + "\n" + r1.stdout)
        self.assertEqual(r2.returncode, 0, r2.stderr + "\n" + r2.stdout)
        type(self).hwpx1 = m1

        merged = self.tmp / "merged.hwpx"
        rm = _run("merge_hwpx.py", str(m1), str(m2), "--out", str(merged))
        self.assertEqual(rm.returncode, 0, rm.stderr + "\n" + rm.stdout)
        summary = _json_last_line(rm.stdout)
        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["modules"], 2, summary)
        self.assertEqual(summary["images"], 2, summary)
        type(self).merged = merged

        _, f1 = _zip_files(m1)
        _, f2 = _zip_files(m2)
        infos, fm = _zip_files(merged)
        self.assertEqual(f1["Contents/header.xml"], fm["Contents/header.xml"])
        self.assertEqual(f1["Contents/header.xml"], f2["Contents/header.xml"])

        s1 = _xml(f1, "Contents/section0.xml")
        s2 = _xml(f2, "Contents/section0.xml")
        sm = _xml(fm, "Contents/section0.xml")
        self.assertEqual(_n_para(sm), _n_para(s1) + _n_para(s2))
        self.assertEqual(sm.count("<hp:secPr"), 1)
        self.assertEqual(sm.count('pageBreak="1"'), 1)
        idx = sm.find('pageBreak="1"')
        self.assertIn("모듈2제목", sm[idx:idx + 800])

        names = set(fm)
        self.assertIn("BinData/image1.PNG", names)
        self.assertIn("BinData/image2.PNG", names)
        hpf = _xml(fm, "Contents/content.hpf")
        ids = re.findall(r'<opf:item\s+id="(image\d+)"', hpf)
        self.assertEqual(sorted(ids), ["image1", "image2"], ids)
        self.assertEqual(len(ids), len(set(ids)), ids)

        bad = self.tmp / "bad-header.hwpx"
        _write_header_plus_one_byte(m1, bad)
        with self.assertRaises(ValueError) as ctx:
            merge_hwpx.merge([str(m1), str(bad)], str(self.tmp / "nope.hwpx"))
        self.assertIn("header.xml 이 다름", str(ctx.exception))

    def test_05_export_grade_smoke(self) -> None:
        if self.merged is None or not Path(self.merged).exists():
            self.fail("test_04 merge 산출물이 없다")
        if not HWP_EXE.exists():
            self.skipTest("Hwp.exe 경로 없음")
        before = set(export_pdf._hwp_pids())
        try:
            import win32com.client as w
            h = w.gencache.EnsureDispatch("HWPFrame.HwpObject")
        except Exception:
            leftover = set(export_pdf._hwp_pids()) - before
            for pid in leftover:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    capture_output=True, text=True, encoding="oem", errors="replace",
                )
            self.skipTest("HWPFrame.HwpObject Dispatch 실패")
        spawned = set(export_pdf._hwp_pids()) - before
        if spawned:
            # 우리가 띄운 창만 닫는다. 이미 떠 있던 사용자 한글은 Quit 하지 않는다.
            try:
                h.Quit()
            except Exception:
                pass
            leftover = set(export_pdf._hwp_pids()) - before
            for pid in leftover:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    capture_output=True, text=True, encoding="oem", errors="replace",
                )

        pdf = self.tmp / "merged.pdf"
        r = _run("export_pdf.py", str(self.merged), str(pdf), timeout=180)
        leftover = set(export_pdf._hwp_pids()) - before
        if leftover:
            for pid in leftover:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    capture_output=True, text=True, encoding="oem", errors="replace",
                )
            self.fail(f"Hwp.exe 잔존 PID {leftover}; export rc={r.returncode} {r.stderr}")
        if r.returncode == 2:
            self.skipTest("한글 없음")
        self.assertEqual(r.returncode, 0, r.stderr + "\n" + r.stdout)
        self.assertTrue(pdf.exists() and pdf.stat().st_size > 0, pdf)

        import fitz
        doc = fitz.open(pdf)
        try:
            n_pages = doc.page_count
        finally:
            doc.close()
        self.assertGreaterEqual(n_pages, 2, n_pages)

        rg = _run(
            "grade_pdf.py", str(pdf),
            "--md", str(self.ms1),
            "--out", str(self.tmp / "grade.json"),
        )
        self.assertEqual(rg.returncode, 0, rg.stderr + "\n" + rg.stdout)
        summary = _json_last_line(rg.stdout)
        self.assertEqual(
            set(summary["defects"]),
            {"aspect", "word_cut", "table_spill", "gap"},
            summary,
        )
        self.assertGreaterEqual(summary["images"], 1, summary)


if __name__ == "__main__":
    unittest.main(verbosity=2)
