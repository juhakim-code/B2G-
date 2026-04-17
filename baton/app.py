import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from baton.knowledge_store import KnowledgeStore
from baton.claude_client import ClaudeClient
from baton.learner import SlackLearner
from baton.scheduler import LearningScheduler
from baton.onboarding import OnboardingManager
from baton.personas import SimulationManager, PERSONAS

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])
store = KnowledgeStore()
claude = ClaudeClient(api_key=os.environ["ANTHROPIC_API_KEY"])
PREDECESSOR_NAME = os.environ.get("PREDECESSOR_NAME", "전임자")

learner = SlackLearner(
    slack_token=os.environ["SLACK_BOT_TOKEN"],
    claude=claude,
    store=store
)
onboarding = OnboardingManager(slack_client=app.client, claude=claude, store=store)
simulation = SimulationManager(slack_client=app.client, claude=claude)


@app.event("message")
def handle_dm(event, say, logger):
    """DM으로 오는 질문에 전임자 스타일로 답변"""
    if event.get("channel_type") != "im":
        return
    if event.get("bot_id"):
        return

    question = event.get("text", "").strip()
    if not question:
        return

    knowledge = store.read_all()
    if not knowledge:
        say("아직 학습된 내용이 없어요. `/바톤-학습` 명령어로 먼저 학습을 시작해주세요.")
        return

    answer = claude.answer_question(question, knowledge, PREDECESSOR_NAME)
    say(answer)


@app.command("/바톤-학습")
def trigger_learning(ack, say, logger):
    """수동으로 전체 채널 학습 트리거"""
    ack()
    say("📚 슬랙 채널 학습을 시작합니다...")
    count = learner.learn_all_channels()
    say(f"✅ {count}개 채널 학습 완료! DM으로 질문해보세요.")


@app.command("/바톤-인계")
def start_handover(ack, say, command):
    """인계 프로세스 시작"""
    ack()
    user_id = command["user_id"]
    say(f"🔄 {PREDECESSOR_NAME}님의 인계 후보를 분석 중입니다...")
    onboarding.start_handover(user_id, PREDECESSOR_NAME)
    say("✅ DM으로 후보 목록을 보내드렸어요. 확인 후 `/바톤-인계-확정`을 사용해주세요.")


@app.command("/바톤-인계-확정")
def confirm_handover(ack, say, command):
    """인계 확정. 사용법: /바톤-인계-확정 @인수자 1,2,3"""
    ack()
    text = command.get("text", "").strip()
    parts = text.split()
    if len(parts) < 2:
        say("사용법: `/바톤-인계-확정 @인수자 1,2,3`")
        return
    successor_id = parts[0].strip("<@>").split("|")[0]
    selected_ids = [int(x) for x in parts[1].split(",") if x.strip().isdigit()]
    predecessor_id = command["user_id"]

    onboarding.confirm_and_deliver(predecessor_id, successor_id, selected_ids, PREDECESSOR_NAME)
    say(f"✅ <@{successor_id}>님께 온보딩 내용을 전달했습니다!")


@app.command("/바톤-시뮬레이션")
def run_simulation(ack, say, command):
    """실전 시뮬레이션 시작. 사용법: /바톤-시뮬레이션 5"""
    ack()
    text = command.get("text", "5").strip()
    count = int(text) if text.isdigit() else 5
    count = min(count, len(PERSONAS))
    user_id = command["user_id"]
    say(f"🎭 {count}명 페르소나 시뮬레이션을 시작합니다!")
    simulation.run_simulation(target_user_id=user_id, persona_count=count)


if __name__ == "__main__":
    scheduler = LearningScheduler(learner)
    scheduler.start()
    print("📅 매주 월요일 오전 6시 자동 학습 스케줄러 시작")
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
