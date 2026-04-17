import pytest
from pathlib import Path
from baton.knowledge_store import KnowledgeStore


@pytest.fixture
def store(tmp_path):
    return KnowledgeStore(base_dir=str(tmp_path))


def test_read_all_empty(store):
    result = store.read_all()
    assert result == ""


def test_append_and_read(store):
    store.append("업무_프로세스", "- 비용신청은 3일 전까지 제출")
    result = store.read_all()
    assert "비용신청" in result


def test_append_invalid_category(store):
    store.append("없는카테고리", "내용")  # 오류 없이 통과


def test_log_update(store):
    store.log_update("테스트 학습 완료")
    log_path = store.files["업데이트_로그"]
    assert "테스트 학습 완료" in log_path.read_text(encoding="utf-8")
