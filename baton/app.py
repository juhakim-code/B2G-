import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from baton.knowledge_store import KnowledgeStore
from baton.claude_client import ClaudeClient
from baton.learner import SlackLearner
from baton.scheduler import LearningScheduler

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
def start_handover(ack, say):
    """인계 프로세스 시작 (Task 7에서 구현)"""
    ack()
    say("🔄 인계 프로세스를 준비 중입니다...")


if __name__ == "__main__":
    scheduler = LearningScheduler(learner)
    scheduler.start()
    print("📅 매주 월요일 오전 6시 자동 학습 스케줄러 시작")
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
