"""테스트가 스킬 폴더의 audit/search-log.jsonl 을 더럽히지 않게 작업 폴더를 임시로 돌린다."""
import pytest


@pytest.fixture(autouse=True)
def _isolated_work_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MDR_WORK_DIR", str(tmp_path / "_mdr_work"))
