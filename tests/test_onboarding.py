import pytest
from unittest.mock import MagicMock
from baton.onboarding import OnboardingManager
from baton.knowledge_store import KnowledgeStore
from baton.claude_client import ClaudeClient


@pytest.fixture
def manager(tmp_path):
    store = KnowledgeStore(base_dir=str(tmp_path))
    store.append("업무_프로세스", "- 비용신청은 3일 전까지")
    claude = MagicMock(spec=ClaudeClient)
    claude.generate_handover_candidates.return_value = [
        {"id": 1, "category": "업무_프로세스", "content": "비용신청 절차", "priority": "high"}
    ]
    slack_client = MagicMock()
    return OnboardingManager(slack_client=slack_client, claude=claude, store=store)


def test_format_candidates_message(manager):
    candidates = [
        {"id": 1, "category": "업무_프로세스", "content": "비용신청 절차", "priority": "high"},
        {"id": 2, "category": "자주_묻는_질문", "content": "연차 신청 방법", "priority": "medium"},
    ]
    result = manager._format_candidates_message(candidates)
    assert "비용신청" in result
    assert "🔴" in result


def test_format_onboarding_message(manager):
    items = [{"category": "업무_프로세스", "content": "비용신청 절차"}]
    result = manager._format_onboarding_message(items, predecessor_name="김철수")
    assert "김철수" in result
    assert "비용신청" in result
