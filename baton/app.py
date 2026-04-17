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
simulation = SimulationManager(slack_client=app.client, claude=claude, knowledge=store.read_all())


@app.event("message")
def handle_message(event, say, logger):
    if event.get("bot_id"):
        return
    text = event.get("text", "").strip()
    if not text:
        return

    thread_ts = event.get("thread_ts")

    # 시뮬레이션 스레드 답변 감지
    if thread_ts and simulation.get_thread_info(thread_ts):
        simulation.handle_thread_reply(thread_ts, text)
        return

    # DM 질문 답변
    if event.get("channel_type") == "im":
        knowledge = store.read_all()
        if not knowledge:
            say("아직 학습된 내용이 없어요. `/baton-simulation` 으로 시뮬레이션을 시작해보세요.")
            return
        answer = claude.answer_question(text, knowledge, PREDECESSOR_NAME)
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


@app.command("/baton-simulation")
def run_simulation(ack, respond, command):
    """실전 시뮬레이션 시작. 사용법: /baton-simulation 5"""
    ack()
    text = command.get("text", "20").strip()
    count = int(text) if text.isdigit() else 20
    count = min(count, len(PERSONAS))
    user_id = command["user_id"]
    channel_id = command["channel_id"]
    simulation.run_simulation(target_user_id=user_id, persona_count=count, channel_id=channel_id)


if __name__ == "__main__":
    scheduler = LearningScheduler(learner)
    scheduler.start()
    print("바톤 봇 시작 - 매주 월요일 오전 6시 자동 학습 스케줄러 실행 중")
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
