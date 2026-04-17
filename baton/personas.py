import time
import random
import json
from pathlib import Path
from slack_sdk import WebClient
from baton.claude_client import ClaudeClient

THREADS_FILE = Path("knowledge/active_threads.json")

PERSONAS = [
    # 고난도 5명
    {"name": "김급함", "type": "difficult", "trait": "모든 것이 급하고 즉각 답변을 요구함", "emoji": ":rage:"},
    {"name": "최불만", "type": "difficult", "trait": "기존 방식에 불만이 많고 반박을 잘 함", "emoji": ":face_with_symbols_on_mouth:"},
    {"name": "정복잡", "type": "difficult", "trait": "질문이 매우 길고 복잡하며 여러 내용을 한번에 물어봄", "emoji": ":dizzy_face:"},
    {"name": "한예외", "type": "difficult", "trait": "항상 예외 케이스를 가져오며 원칙에 맞지 않는 요청을 함", "emoji": ":smiling_imp:"},
    {"name": "오반복", "type": "difficult", "trait": "같은 질문을 여러 번 반복하며 확인을 과도하게 요구함", "emoji": ":repeat:"},
    # 일반 15명
    {"name": "박신입", "type": "normal", "trait": "열정적이고 질문이 많은 신입", "emoji": ":star-struck:"},
    {"name": "이조용", "type": "normal", "trait": "말수가 적고 혼자 해결하려는 성격", "emoji": ":shushing_face:"},
    {"name": "강열심", "type": "normal", "trait": "업무에 성실하며 프로세스를 잘 따름", "emoji": ":muscle:"},
    {"name": "윤전직", "type": "normal", "trait": "다른 회사에서 이직한 경험자", "emoji": ":briefcase:"},
    {"name": "장적응", "type": "normal", "trait": "새로운 환경에 천천히 적응 중", "emoji": ":seedling:"},
    {"name": "홍확인", "type": "normal", "trait": "꼼꼼하게 확인하는 스타일", "emoji": ":mag:"},
    {"name": "임궁금", "type": "normal", "trait": "업무 배경과 이유가 항상 궁금함", "emoji": ":thinking_face:"},
    {"name": "조계획", "type": "normal", "trait": "미리 계획하고 일정을 중시함", "emoji": ":calendar:"},
    {"name": "신친절", "type": "normal", "trait": "친절하고 협조적인 성격", "emoji": ":blush:"},
    {"name": "양혼란", "type": "normal", "trait": "업무 파악이 아직 안 된 상태", "emoji": ":sweat:"},
    {"name": "권신중", "type": "normal", "trait": "실수를 두려워하며 신중하게 행동", "emoji": ":grimacing:"},
    {"name": "문배움", "type": "normal", "trait": "배우려는 의지가 강한 학습형", "emoji": ":books:"},
    {"name": "류성실", "type": "normal", "trait": "성실하고 책임감이 강함", "emoji": ":trophy:"},
    {"name": "고준비", "type": "normal", "trait": "사전에 자료를 찾아보고 질문함", "emoji": ":pencil:"},
    {"name": "나마무", "type": "normal", "trait": "감사하고 긍정적인 태도", "emoji": ":pray:"},
]

QUESTION_PROMPT = """당신은 부트캠프 훈련생 '{name}'입니다.
성격: {trait}

아래는 실제 운영 채널 메시지와 업무 데이터입니다. 이 내용을 바탕으로 질문하세요:
{knowledge_snippet}

담당 매니저에게 슬랙 메시지로 보낼 질문 1개를 작성하세요.
- 위 실제 데이터에서 언급된 구체적인 업무(출결, 과제, 행정 등)를 소재로 하세요
- 짧고 자연스럽게, 실제 슬랙 메시지처럼 작성하세요
{trait_instruction}

질문만 출력하세요 (설명 없이)."""

FOLLOWUP_PROMPT = """당신은 부트캠프 훈련생 '{name}'입니다.
성격: {trait}

당신이 매니저에게 아래 질문을 했고, 매니저가 답변했습니다.

당신의 질문: {question}
매니저의 답변: {answer}

이 답변에 대해 당신의 성격대로 자연스럽게 반응하세요.
- 고난도 페르소나라면: 답변이 불충분하거나 추가 요구를 하세요
- 일반 페르소나라면: 감사하거나 추가 궁금한 점을 물어보세요

짧고 자연스럽게 슬랙 메시지처럼 1-2문장만 작성하세요. 메시지만 출력하세요."""

FEEDBACK_PROMPT = """당신은 인수인계 교육 전문가입니다.
아래 실제 업무 지식을 바탕으로, 매니저의 답변을 평가해주세요.

업무 지식:
{knowledge_snippet}

훈련생 질문: {question}
매니저 답변: {answer}

아래 형식으로 피드백을 주세요:
- 점수: X/10
- 잘한 점: (1줄)
- 보완할 점: (1줄, 없으면 "없음")
- 모범 답변 힌트: (1줄)

간결하게 작성하세요."""

INTRO_TEMPLATE = """:rotating_light: *실전 인수인계 시뮬레이션을 시작합니다!* :rotating_light:

━━━━━━━━━━━━━━━━━━━━━━━━━
당신은 지금 *김신성 매니저* 의 업무를 인수받았습니다.
지금부터 *{count}명의 훈련생* 이 순서대로 질문을 올립니다.

*각 메시지의 스레드에 실제처럼 답변해보세요!*
답변하면 페르소나가 반응하고 피드백도 드립니다.
━━━━━━━━━━━━━━━━━━━━━━━━━
잠시 후 첫 번째 훈련생이 메시지를 보냅니다..."""


class SimulationManager:
    def __init__(self, slack_client: WebClient, claude: ClaudeClient, knowledge: str = ""):
        self.slack = slack_client
        self.claude = claude
        self.knowledge = knowledge

    def _load_threads(self) -> dict:
        if THREADS_FILE.exists():
            return json.loads(THREADS_FILE.read_text(encoding="utf-8"))
        return {}

    def _save_threads(self, threads: dict) -> None:
        THREADS_FILE.write_text(json.dumps(threads, ensure_ascii=False, indent=2), encoding="utf-8")

    def _register_thread(self, thread_ts: str, persona: dict, question: str, channel_id: str) -> None:
        threads = self._load_threads()
        threads[thread_ts] = {"persona": persona, "question": question, "channel_id": channel_id}
        self._save_threads(threads)

    def get_thread_info(self, thread_ts: str) -> dict | None:
        return self._load_threads().get(thread_ts)

    def _generate_question(self, persona: dict) -> str:
        trait_instruction = (
            "공격적이거나 무리한 요청을 포함하세요." if persona["type"] == "difficult"
            else "일반적인 업무 질문을 하세요."
        )
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

    def handle_thread_reply(self, thread_ts: str, user_answer: str) -> None:
        """스레드 답변 감지 → 페르소나 반응 + 피드백"""
        info = self.get_thread_info(thread_ts)
        if not info:
            return

        persona = info["persona"]
        question = info["question"]
        channel_id = info["channel_id"]
        knowledge_snippet = self.knowledge[:2000] if self.knowledge else ""

        # 1. 페르소나 반응
        followup = self.claude.client.messages.create(
            model=self.claude.MODEL,
            max_tokens=150,
            messages=[{"role": "user", "content": FOLLOWUP_PROMPT.format(
                name=persona["name"],
                trait=persona["trait"],
                question=question,
                answer=user_answer
            )}]
        ).content[0].text.strip()

        self.slack.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=f"{persona['emoji']} *{persona['name']}*: {followup}"
        )

        # 2. AI 피드백
        feedback = self.claude.client.messages.create(
            model=self.claude.MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": FEEDBACK_PROMPT.format(
                knowledge_snippet=knowledge_snippet,
                question=question,
                answer=user_answer
            )}]
        ).content[0].text.strip()

        self.slack.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=f":robot_face: *바톤 피드백*\n{feedback}"
        )

    def _get_channel_id(self, channel_name: str) -> str:
        name = channel_name.lstrip("#")
        resp = self.slack.conversations_list(limit=200, types="public_channel")
        for ch in resp["channels"]:
            if ch["name"] == name:
                try:
                    self.slack.conversations_join(channel=ch["id"])
                except Exception:
                    pass
                return ch["id"]
        raise ValueError(f"채널 #{name} 을 찾을 수 없습니다.")

    def run_simulation(self, target_user_id: str, persona_count: int = 20,
                       channel_id: str = None, channel_name: str = "시뮬레이션") -> None:
        difficult = [p for p in PERSONAS if p["type"] == "difficult"]   # 5명
        normal = [p for p in PERSONAS if p["type"] == "normal"]         # 15명

        # 요청 수에 맞게 5:15 비율 유지
        diff_count = min(5, max(1, persona_count * 5 // 20))
        norm_count = persona_count - diff_count
        selected = random.sample(difficult, min(diff_count, len(difficult))) + \
                   random.sample(normal, min(norm_count, len(normal)))
        random.shuffle(selected)
        personas = selected
        if not channel_id:
            channel_id = self._get_channel_id(channel_name)

        self.slack.chat_postMessage(
            channel=channel_id,
            text=INTRO_TEMPLATE.format(count=persona_count)
        )
        time.sleep(2)

        for i, persona in enumerate(personas, 1):
            try:
                question = self._generate_question(persona)
            except Exception as e:
                self.slack.chat_postMessage(
                    channel=channel_id,
                    text=f":warning: [{persona['name']}] 질문 생성 실패: {str(e)}"
                )
                continue

            difficulty = ":red_circle: 고난도" if persona["type"] == "difficult" else ":large_green_circle: 일반"

            try:
                result = self.slack.chat_postMessage(
                    channel=channel_id,
                    text=(
                        f"{persona['emoji']} *{persona['name']}* ({i}/{persona_count})  {difficulty}\n"
                        f"_{persona['trait']}_\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"{question}\n\n"
                        f"> :speech_balloon: 스레드에 답변해주세요."
                    )
                )
                thread_ts = result["ts"]
                self._register_thread(thread_ts, persona, question, channel_id)
            except Exception as e:
                self.slack.chat_postMessage(
                    channel=channel_id,
                    text=f":warning: [{persona['name']}] 메시지 전송 실패: {str(e)}"
                )
            time.sleep(2)

        self.slack.chat_postMessage(
            channel=channel_id,
            text=":checkered_flag: *모든 질문이 올라왔습니다!*\n각 스레드에 답변하면 페르소나 반응과 피드백을 받을 수 있어요."
        )
