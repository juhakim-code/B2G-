import time
from slack_sdk import WebClient
from baton.claude_client import ClaudeClient
from baton.knowledge_store import KnowledgeStore


class SlackLearner:
    HISTORY_DAYS = 90

    def __init__(self, slack_token: str, claude: ClaudeClient, store: KnowledgeStore):
        self.client = WebClient(token=slack_token)
        self.claude = claude
        self.store = store

    def get_public_channels(self) -> list:
        """공개 채널 목록 반환 (아카이브 제외)"""
        result = self.client.conversations_list(types="public_channel", limit=200)
        return [ch for ch in result["channels"] if not ch.get("is_archived")]

    def get_channel_history(self, channel_id: str) -> list:
        """채널 히스토리 가져오기 (HISTORY_DAYS 기준)"""
        oldest = str(time.time() - self.HISTORY_DAYS * 24 * 3600)
        messages = []
        cursor = None
        while True:
            result = self.client.conversations_history(
                channel=channel_id,
                oldest=oldest,
                limit=200,
                cursor=cursor
            )
            messages.extend([
                m for m in result["messages"]
                if m.get("text") and not m.get("bot_id")
            ])
            if not result.get("has_more"):
                break
            cursor = result["response_metadata"]["next_cursor"]
        return messages

    def _format_messages(self, messages: list) -> str:
        """메시지 리스트를 텍스트로 변환"""
        return "\n".join(
            f"[{m.get('user', '?')}]: {m.get('text', '')}"
            for m in messages
        )

    def _save_extracted(self, extracted: dict, channel_name: str) -> None:
        """추출된 지식을 지식창고에 저장"""
        for category in ["업무_프로세스", "자주_묻는_질문", "담당자_스타일"]:
            items = extracted.get(category, [])
            for item in items:
                if item:
                    self.store.append(category, f"- {item}")
        self.store.log_update(f"#{channel_name} 학습 완료")

    def learn_channel(self, channel_id: str, channel_name: str) -> None:
        """채널 하나 학습"""
        messages = self.get_channel_history(channel_id)
        if len(messages) < 3:
            return
        text = self._format_messages(messages)
        text = text[:3000]
        extracted = self.claude.extract_knowledge(text)
        self._save_extracted(extracted, channel_name)

    def learn_all_channels(self) -> int:
        """모든 공개 채널 학습. 학습한 채널 수 반환."""
        channels = self.get_public_channels()
        count = 0
        for ch in channels:
            try:
                self.learn_channel(ch["id"], ch["name"])
                count += 1
            except Exception as e:
                self.store.log_update(f"#{ch['name']} 학습 실패: {str(e)[:50]}")
        return count
