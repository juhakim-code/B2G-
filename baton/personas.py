import time
from slack_sdk import WebClient
from baton.claude_client import ClaudeClient

PERSONAS = [
    # 고난도 5명
    {"name": "김급함", "type": "difficult", "trait": "모든 것이 급하고 즉각 답변을 요구함"},
    {"name": "최불만", "type": "difficult", "trait": "기존 방식에 불만이 많고 반박을 잘 함"},
    {"name": "정복잡", "type": "difficult", "trait": "질문이 매우 길고 복잡하며 여러 내용을 한번에 물어봄"},
    {"name": "한예외", "type": "difficult", "trait": "항상 예외 케이스를 가져오며 원칙에 맞지 않는 요청을 함"},
    {"name": "오반복", "type": "difficult", "trait": "같은 질문을 여러 번 반복하며 확인을 과도하게 요구함"},
    # 일반 15명
    {"name": "박신입", "type": "normal", "trait": "열정적이고 질문이 많은 신입"},
    {"name": "이조용", "type": "normal", "trait": "말수가 적고 혼자 해결하려는 성격"},
    {"name": "강열심", "type": "normal", "trait": "업무에 성실하며 프로세스를 잘 따름"},
    {"name": "윤전직", "type": "normal", "trait": "다른 회사에서 이직한 경험자"},
    {"name": "장적응", "type": "normal", "trait": "새로운 환경에 천천히 적응 중"},
    {"name": "홍확인", "type": "normal", "trait": "꼼꼼하게 확인하는 스타일"},
    {"name": "임궁금", "type": "normal", "trait": "업무 배경과 이유가 항상 궁금함"},
    {"name": "조계획", "type": "normal", "trait": "미리 계획하고 일정을 중시함"},
    {"name": "신친절", "type": "normal", "trait": "친절하고 협조적인 성격"},
    {"name": "양혼란", "type": "normal", "trait": "업무 파악이 아직 안 된 상태"},
    {"name": "권신중", "type": "normal", "trait": "실수를 두려워하며 신중하게 행동"},
    {"name": "문배움", "type": "normal", "trait": "배우려는 의지가 강한 학습형"},
    {"name": "류성실", "type": "normal", "trait": "성실하고 책임감이 강함"},
    {"name": "고준비", "type": "normal", "trait": "사전에 자료를 찾아보고 질문함"},
    {"name": "나마무", "type": "normal", "trait": "감사하고 긍정적인 태도"},
]

QUESTION_PROMPT = """당신은 부트캠프 훈련생 '{name}'입니다.
성격: {trait}

아래는 실제 운영 채널과 업무 데이터입니다:
{knowledge_snippet}

이 상황에서 담당 매니저에게 슬랙 DM으로 보낼 질문 1개를 작성하세요.
짧고 자연스럽게, 실제 슬랙 메시지처럼 작성하세요.
{trait_instruction}

질문만 출력하세요 (설명 없이)."""


class SimulationManager:
    def __init__(self, slack_client: WebClient, claude: ClaudeClient, knowledge: str = ""):
        self.slack = slack_client
        self.claude = claude
        self.knowledge = knowledge

    def _generate_question(self, persona: dict) -> str:
        trait_instruction = (
            "공격적이거나 무리한 요청을 포함하세요." if persona["type"] == "difficult"
            else "일반적인 업무 질문을 하세요."
        )
        # 지식창고에서 앞부분 2000자만 사용 (토큰 절약)
        knowledge_snippet = self.knowledge[:2000] if self.knowledge else "업무 데이터 없음"
        response = self.claude.client.messages.create(
            model=self.claude.MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": QUESTION_PROMPT.format(
                name=persona["name"],
                trait=persona["trait"],
                trait_instruction=trait_instruction,
                knowledge_snippet=knowledge_snippet
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
