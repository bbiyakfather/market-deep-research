"""배치 3B: 렌더 입력 이미지를 G3 기준선에 봉인하는 R02 회귀."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import manifest
import verify_facts
from skill_paths import WorkPaths, resolve_work_dir

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def _work(tmp_path, topic="봉인이미지"):
    return WorkPaths(resolve_work_dir(topic, base=tmp_path))


def test_report_image_refs_dedup_order_skips_remote():
    text = (
        "![a](chart.png)\n"
        "![b](assets/x.png)\n"
        "![c](chart.png)\n"
        "![d](https://origin.test/x.png)\n"
        '<img src="root.png">'
    )
    assert verify_facts.report_image_refs(text) == ["chart.png", "assets/x.png", "root.png"]


def test_root_image_enters_g3_baseline_as_report_image(tmp_path):
    wp = _work(tmp_path)
    png = wp.root / "chart.png"
    png.write_bytes(PNG)
    wp.report_md.write_text("![차트](chart.png)\n\n[그림] 출처: 예시 (F001)\n", encoding="utf-8")
    sealed = manifest.build(wp, for_g3=True)
    meta = sealed["entries"]["chart.png"]
    assert meta["label"] == "report_image"
    assert meta["sha256"] == manifest.sha256_file(png)


def test_tamper_root_image_after_g3_fails_verify_and_snapshot(tmp_path):
    wp = _work(tmp_path, "변조이미지")
    png = wp.root / "chart.png"
    png.write_bytes(PNG)
    wp.report_md.write_text("![차트](chart.png)\n\n[그림] 출처: 예시 (F001)\n", encoding="utf-8")
    sealed = manifest.build(wp, for_g3=True)
    assert sealed["entries"]["chart.png"]["label"] == "report_image"
    assert manifest.verify(wp)["ok"]
    before = manifest._final_snapshot(wp)
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"1" * 64)
    result = manifest.verify(wp)
    assert not result["ok"] and "chart.png" in result["changed"]
    after = manifest._final_snapshot(wp)
    assert after["chart.png"] != before["chart.png"]


def test_assets_image_keeps_assets_label_without_duplicate(tmp_path):
    wp = _work(tmp_path, "자산이미지")
    asset = wp.root / "assets" / "in.png"
    asset.write_bytes(PNG)
    root_png = wp.root / "chart.png"
    root_png.write_bytes(PNG)
    wp.report_md.write_text(
        "![자산](assets/in.png)\n\n[그림] 출처: 예시 (F001)\n\n"
        "![루트](chart.png)\n\n[그림] 출처: 예시 (F001)\n",
        encoding="utf-8",
    )
    sealed = manifest.build(wp, for_g3=True)
    assert list(sealed["entries"]).count("assets/in.png") == 1
    assert sealed["entries"]["assets/in.png"]["label"] == "assets"
    assert sealed["entries"]["chart.png"]["label"] == "report_image"


@pytest.mark.parametrize("target_kind", ["parent", "absolute"])
def test_outside_image_ref_fails_boundary(tmp_path, target_kind):
    wp = WorkPaths(tmp_path)
    outside = tmp_path.parent / "outside.png"
    outside.write_bytes(PNG)
    target = "../outside.png" if target_kind == "parent" else outside.as_posix()
    failures, _ = verify_facts.check_figures(
        f"![그림]({target})\n[그림] 출처: 예시\n", {}, wp)
    assert any("[도판경계]" in failure for failure in failures), failures


def test_report_without_images_has_no_report_image_entries(tmp_path):
    wp = _work(tmp_path, "무도판")
    wp.report_md.write_text("# 보고서\n\n수치만 있다.\n", encoding="utf-8")
    wp.facts.write_text("", encoding="utf-8")
    paths = manifest._tracked_paths(wp.root)
    assert paths["report.md"][0] == "report_md"
    assert all(label != "report_image" for label, _p in paths.values())
    sealed = manifest.build(wp, for_g3=True)
    assert manifest.verify(wp)["ok"]
    assert not any(meta["label"] == "report_image" for meta in sealed["entries"].values())
