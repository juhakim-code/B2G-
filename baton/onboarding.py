from slack_sdk import WebClient
from baton.claude_client import ClaudeClient
from baton.knowledge_store import KnowledgeStore

PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}


class OnboardingManager:
    def __init__(self, slack_client: WebClient, claude: ClaudeClient, store: KnowledgeStore):
        self.slack = slack_client
        self.claude = claude
        self.store = store
        self._sessions: dict = {}

    def _format_candidates_message(self, candidates: list) -> str:
        lines = ["📋 *바톤이 분석한 인계 후보 목록입니다.*\n포함할 항목에 ✅ 이모지로 반응해주세요!\n"]
        for item in candidates:
            emoji = PRIORITY_EMOJI.get(item.get("priority", "low"), "⚪")
            lines.append(f"{emoji} *[{item['id']}] {item['category']}*: {item['content']}")
        lines.append("\n인수자 슬랙 ID와 함께 `/바톤-인계-확정 @인수자 1,2,3` 형식으로 확정해주세요.")
        return "\n".join(lines)

    def _format_onboarding_message(self, items: list, predecessor_name: str) -> str:
        lines = [f"👋 안녕하세요! 바톤입니다.\n*{predecessor_name}님*의 업무를 체계적으로 알려드릴게요.\n"]
        for i, item in enumerate(items, 1):
            lines.append(f"*{i}단계 | {item['category']}*\n{item['content']}\n")
        lines.append("❓ 궁금한 점은 이 DM으로 언제든 질문해주세요!")
        return "\n".join(lines)

    def start_handover(self, predecessor_user_id: str, predecessor_name: str) -> None:
        """인계 프로세스 시작: 후보 목록 생성 → 인계자 DM 전송"""
        knowledge = self.store.read_all()
        candidates = self.claude.generate_handover_candidates(knowledge, predecessor_name)
        self._sessions[predecessor_user_id] = candidates

        dm = self.slack.conversations_open(users=predecessor_user_id)
        channel_id = dm["channel"]["id"]
        self.slack.chat_postMessage(
            channel=channel_id,
            text=self._format_candidates_message(candidates)
        )

    def confirm_and_deliver(self, predecessor_user_id: str, successor_user_id: str,
                             selected_ids: list, predecessor_name: str) -> None:
        """선택된 항목으로 인계시트 생성 → 인수자 DM 전송"""
        candidates = self._sessions.get(predecessor_user_id, [])
        selected = [c for c in candidates if c["id"] in selected_ids]

        dm = self.slack.conversations_open(users=successor_user_id)
        channel_id = dm["channel"]["id"]
        self.slack.chat_postMessage(
            channel=channel_id,
            text=self._format_onboarding_message(selected, predecessor_name)
        )
        self._sessions.pop(predecessor_user_id, None)
