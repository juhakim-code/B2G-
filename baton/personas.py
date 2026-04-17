import time
from slack_sdk import WebClient
from baton.claude_client import ClaudeClient

PERSONAS = [
    {"name": "박신입", "type": "normal", "trait": "열정적이고 질문이 많은 신입"},
    {"name": "이조용", "type": "normal", "trait": "말수가 적고 혼자 해결하려는 성격"},
    {"name": "김급함", "type": "difficult", "trait": "모든 것이 급하고 즉각 답변을 요구함"},
    {"name": "최불만", "type": "difficult", "trait": "기존 방식에 불만이 많고 반박을 잘 함"},
    {"name": "정복잡", "type": "difficult", "trait": "질문이 매우 길고 복잡하며 여러 내용을 한번에 물어봄"},
    {"name": "한예외", "type": "difficult", "trait": "항상 예외 케이스를 가져오며 원칙에 맞지 않는 요청을 함"},
    {"name": "오반복", "type": "difficult", "trait": "같은 질문을 여러 번 반복하며 확인을 과도하게 요구함"},
    {"name": "강보통1", "type": "normal", "trait": "업무에 성실하며 프로세스를 잘 따름"},
    {"name": "강보통2", "type": "normal", "trait": "새로운 업무에 적응 중인 재직자"},
    {"name": "강보통3", "type": "normal", "trait": "다른 부서에서 이동해온 경험자"},
]

QUESTION_PROMPT = """당신은 회사 직원 '{name}'입니다.
성격: {trait}

아래 업무 상황에서 담당자에게 DM으로 보낼 질문 1개를 작성해주세요.
짧고 자연스럽게, 실제 슬랙 메시지처럼 작성하세요.

업무 상황: 부트캠프 훈련생 관리, 비용 처리, 출결 관리, 민원 대응
{trait_instruction}

질문만 출력하세요 (설명 없이)."""


class SimulationManager:
    def __init__(self, slack_client: WebClient, claude: ClaudeClient):
        self.slack = slack_client
        self.claude = claude

    def _generate_question(self, persona: dict) -> str:
        trait_instruction = (
            "공격적이거나 무리한 요청을 포함하세요." if persona["type"] == "difficult"
            else "일반적인 업무 질문을 하세요."
        )
        response = self.claude.client.messages.create(
            model=self.claude.MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": QUESTION_PROMPT.format(
                name=persona["name"],
                trait=persona["trait"],
                trait_instruction=trait_instruction
            )}]
        )
        return response.content[0].text.strip()

    def run_simulation(self, target_user_id: str, persona_count: int = 5) -> None:
        """선택된 수만큼 페르소나가 순서대로 DM 발송"""
        personas = PERSONAS[:persona_count]
        dm = self.slack.conversations_open(users=target_user_id)
        channel_id = dm["channel"]["id"]

        self.slack.chat_postMessage(
            channel=channel_id,
            text=f"🎭 *실전 시뮬레이션을 시작합니다!*\n{persona_count}명의 가상 훈련생이 순서대로 메시지를 보냅니다.\n실제처럼 응답해보세요!"
        )

        for persona in personas:
            question = self._generate_question(persona)
            emoji = "😤" if persona["type"] == "difficult" else "😊"
            self.slack.chat_postMessage(
                channel=channel_id,
                text=f"{emoji} *[{persona['name']}]*: {question}"
            )
            time.sleep(2)
