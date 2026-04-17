import pytest
from unittest.mock import MagicMock, patch
from baton.claude_client import ClaudeClient


@pytest.fixture
def client():
    return ClaudeClient(api_key="test-key")


def test_answer_question_returns_string(client):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="김철수이라면: 비용신청은 3일 전까지 하세요.")]
    with patch.object(client.client.messages, "create", return_value=mock_response):
        result = client.answer_question(
            question="비용신청 어떻게 해요?",
            knowledge="비용신청은 3일 전까지",
            predecessor_name="김철수"
        )
    assert "김철수" in result


def test_extract_knowledge_returns_dict(client):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"업무_프로세스": ["비용신청 3일 전"], "자주_묻는_질문": [], "담당자_스타일": []}')]
    with patch.object(client.client.messages, "create", return_value=mock_response):
        result = client.extract_knowledge("슬랙 메시지 내용")
    assert "업무_프로세스" in result
