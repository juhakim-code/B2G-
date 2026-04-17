import pytest
from unittest.mock import MagicMock
from baton.learner import SlackLearner
from baton.knowledge_store import KnowledgeStore
from baton.claude_client import ClaudeClient


@pytest.fixture
def learner(tmp_path):
    store = KnowledgeStore(base_dir=str(tmp_path))
    claude = MagicMock(spec=ClaudeClient)
    claude.extract_knowledge.return_value = {
        "업무_프로세스": ["비용신청은 3일 전까지"],
        "자주_묻는_질문": ["Q: 연차는? A: 인사팀에 신청"],
        "담당자_스타일": []
    }
    return SlackLearner(slack_token="xoxb-fake", claude=claude, store=store)


def test_format_messages(learner):
    messages = [
        {"user": "U001", "text": "비용신청 어떻게 해요?"},
        {"user": "U002", "text": "경리팀에 3일 전에 제출하면 돼요"},
    ]
    result = learner._format_messages(messages)
    assert "비용신청" in result
    assert "경리팀" in result


def test_save_extracted(learner, tmp_path):
    extracted = {
        "업무_프로세스": ["비용신청 절차"],
        "자주_묻는_질문": [],
        "담당자_스타일": []
    }
    learner._save_extracted(extracted, channel_name="일반")
    result = learner.store.read_all()
    assert "비용신청" in result
