# 바톤(BATON) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 슬랙 채널을 자동 학습하고, 인계자 검토를 거쳐 인수자에게 능동적으로 온보딩하는 AI 챗봇 바톤의 MVP를 구현한다.

**Architecture:** Slack Bolt(Socket Mode)로 봇 서버를 구성하고, Anthropic SDK로 지식 추출 및 답변을 처리한다. 마크다운 파일 기반 지식창고에 슬랙 채널 전체 기록을 주기적으로 학습·저장하고, 슬랙 명령어로 인계 프로세스(후보 추출 → 인계자 검토 → 인수자 온보딩)를 실행한다. 3단계 마지막에는 페르소나 봇이 실전 시뮬레이션을 진행한다.

**Tech Stack:** Python 3.11+, slack-bolt, anthropic, apscheduler, python-dotenv

---

## 파일 구조

```
AX-hackathon/
├── baton/
│   ├── __init__.py
│   ├── app.py              # Slack 봇 진입점, 이벤트 핸들러
│   ├── claude_client.py    # Anthropic API 래퍼 (지식 추출 + 답변)
│   ├── knowledge_store.py  # 마크다운 지식창고 읽기/쓰기
│   ├── learner.py          # 슬랙 히스토리 읽기 + 지식 추출
│   ├── scheduler.py        # 주간 자동 학습 스케줄러
│   ├── onboarding.py       # 인계자 검토 + 인수자 전달 흐름
│   └── personas.py         # 실전 시뮬레이션 페르소나 봇
├── knowledge/
│   ├── 업무_프로세스.md
│   ├── 자주_묻는_질문.md
│   ├── 담당자_스타일.md
│   └── 업데이트_로그.md
├── tests/
│   ├── test_knowledge_store.py
│   ├── test_claude_client.py
│   ├── test_learner.py
│   └── test_onboarding.py
├── .env
├── .env.example
└── requirements.txt
```

---

## Task 1: 프로젝트 기초 세팅

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `baton/__init__.py`
- Create: `knowledge/업무_프로세스.md`
- Create: `knowledge/자주_묻는_질문.md`
- Create: `knowledge/담당자_스타일.md`
- Create: `knowledge/업데이트_로그.md`

- [ ] **Step 1: requirements.txt 작성**

```
slack-bolt==1.20.1
anthropic==0.40.0
apscheduler==3.10.4
python-dotenv==1.0.1
slack-sdk==3.33.0
```

- [ ] **Step 2: .env.example 작성**

```
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
PREDECESSOR_NAME=전임자이름
```

- [ ] **Step 3: 실제 .env 파일 생성 (토큰 입력)**

`.env.example`을 복사해 `.env`로 만들고 실제 토큰 입력.  
Slack 토큰 발급 경로: api.slack.com → Your Apps → OAuth & Permissions

- [ ] **Step 4: 지식창고 파일 초기화**

각 파일을 아래 내용으로 생성:

`knowledge/업무_프로세스.md`:
```markdown
# 업무 프로세스
```

`knowledge/자주_묻는_질문.md`:
```markdown
# 자주 묻는 질문
```

`knowledge/담당자_스타일.md`:
```markdown
# 담당자 스타일 및 판단 기준
```

`knowledge/업데이트_로그.md`:
```markdown
# 업데이트 로그
```

- [ ] **Step 5: 패키지 설치**

```bash
pip install -r requirements.txt
```

Expected: 패키지 설치 완료, 오류 없음

- [ ] **Step 6: baton/__init__.py 생성 (빈 파일)**

- [ ] **Step 7: .gitignore에 .env 확인**

```bash
grep ".env" .gitignore
```

없으면 추가:
```
.env
knowledge/*.md
```

- [ ] **Step 8: 커밋**

```bash
git add requirements.txt .env.example baton/ knowledge/ .gitignore
git commit -m "feat: 프로젝트 기초 세팅 완료"
```

---

## Task 2: 지식창고 (KnowledgeStore)

**Files:**
- Create: `baton/knowledge_store.py`
- Create: `tests/test_knowledge_store.py`

- [ ] **Step 1: 테스트 작성**

`tests/test_knowledge_store.py`:
```python
import pytest
from pathlib import Path
from baton.knowledge_store import KnowledgeStore


@pytest.fixture
def store(tmp_path):
    return KnowledgeStore(base_dir=str(tmp_path))


def test_read_all_empty(store):
    result = store.read_all()
    assert result == ""


def test_append_and_read(store):
    store.append("업무_프로세스", "- 비용신청은 3일 전까지 제출")
    result = store.read_all()
    assert "비용신청" in result


def test_append_invalid_category(store):
    # 존재하지 않는 카테고리는 무시
    store.append("없는카테고리", "내용")  # 오류 없이 통과


def test_log_update(store):
    store.log_update("테스트 학습 완료")
    log_path = store.files["업데이트_로그"]
    assert "테스트 학습 완료" in log_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_knowledge_store.py -v
```

Expected: `ModuleNotFoundError: No module named 'baton.knowledge_store'`

- [ ] **Step 3: KnowledgeStore 구현**

`baton/knowledge_store.py`:
```python
from pathlib import Path
from datetime import datetime


class KnowledgeStore:
    CATEGORIES = ["업무_프로세스", "자주_묻는_질문", "담당자_스타일", "업데이트_로그"]

    def __init__(self, base_dir: str = "knowledge"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.files = {
            cat: self.base_dir / f"{cat}.md" for cat in self.CATEGORIES
        }
        # 파일 없으면 초기화
        for cat, path in self.files.items():
            if not path.exists():
                path.write_text(f"# {cat}\n", encoding="utf-8")

    def read_all(self) -> str:
        parts = []
        for cat in ["업무_프로세스", "자주_묻는_질문", "담당자_스타일"]:
            path = self.files[cat]
            text = path.read_text(encoding="utf-8").strip()
            if text and text != f"# {cat}":
                parts.append(text)
        return "\n\n".join(parts)

    def append(self, category: str, content: str) -> None:
        path = self.files.get(category)
        if path is None:
            return
        with path.open("a", encoding="utf-8") as f:
            f.write(f"\n{content}\n")

    def log_update(self, message: str) -> None:
        path = self.files["업데이트_로그"]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        with path.open("a", encoding="utf-8") as f:
            f.write(f"\n- [{timestamp}] {message}\n")
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_knowledge_store.py -v
```

Expected: 4개 테스트 모두 PASSED

- [ ] **Step 5: 커밋**

```bash
git add baton/knowledge_store.py tests/test_knowledge_store.py
git commit -m "feat: 지식창고 KnowledgeStore 구현"
```

---

## Task 3: Claude API 클라이언트

**Files:**
- Create: `baton/claude_client.py`
- Create: `tests/test_claude_client.py`

- [ ] **Step 1: 테스트 작성**

`tests/test_claude_client.py`:
```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_claude_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'baton.claude_client'`

- [ ] **Step 3: ClaudeClient 구현**

`baton/claude_client.py`:
```python
import json
import anthropic


EXTRACT_PROMPT = """다음 슬랙 대화에서 업무 인수인계에 필요한 정보를 추출해주세요.

슬랙 대화:
{messages}

아래 JSON 형식으로만 응답하세요 (설명 없이 JSON만):
{{
  "업무_프로세스": ["발견된 업무 절차 (없으면 빈 배열)"],
  "자주_묻는_질문": ["반복된 질문과 답변 (없으면 빈 배열)"],
  "담당자_스타일": ["판단 기준, 말투 특성 (없으면 빈 배열)"]
}}"""

ANSWER_PROMPT = """당신은 {predecessor_name}의 업무 방식을 학습한 AI 어시스턴트 '바톤'입니다.
아래 지식창고를 바탕으로 {predecessor_name}의 스타일로 답변해주세요.

지식창고:
{knowledge}

질문: {question}

답변 형식: "{predecessor_name}이라면: [답변 내용]"
지식창고에 없는 내용이면 솔직하게 "해당 내용은 기록에 없어요. 직접 확인이 필요합니다." 라고 답하세요."""

HANDOVER_PROMPT = """아래 지식창고에서 {predecessor_name}의 업무 인수인계를 위해
가장 중요한 항목 10개를 선택해주세요.

지식창고:
{knowledge}

아래 JSON 배열 형식으로만 응답하세요:
[
  {{"id": 1, "category": "카테고리명", "content": "인계 내용", "priority": "high"}},
  ...
]
priority는 high/medium/low 중 하나."""


class ClaudeClient:
    MODEL = "claude-opus-4-6"

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def extract_knowledge(self, slack_messages: str) -> dict:
        """슬랙 메시지에서 인계 지식 추출. dict 반환."""
        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=2000,
            system="당신은 업무 지식을 추출하는 전문가입니다. JSON만 응답합니다.",
            messages=[{
                "role": "user",
                "content": EXTRACT_PROMPT.format(messages=slack_messages)
            }]
        )
        text = response.content[0].text.strip()
        # JSON 블록 추출
        if "```" in text:
            text = text.split("```")[1].replace("json", "").strip()
        return json.loads(text)

    def answer_question(self, question: str, knowledge: str, predecessor_name: str) -> str:
        """지식창고 기반 전임자 스타일 답변. 문자열 반환."""
        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": ANSWER_PROMPT.format(
                    predecessor_name=predecessor_name,
                    knowledge=knowledge,
                    question=question
                )
            }]
        )
        return response.content[0].text

    def generate_handover_candidates(self, knowledge: str, predecessor_name: str) -> list:
        """인계 후보 항목 10개 생성. list 반환."""
        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=3000,
            system="당신은 업무 인수인계 전문가입니다. JSON만 응답합니다.",
            messages=[{
                "role": "user",
                "content": HANDOVER_PROMPT.format(
                    predecessor_name=predecessor_name,
                    knowledge=knowledge
                )
            }]
        )
        text = response.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1].replace("json", "").strip()
        return json.loads(text)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_claude_client.py -v
```

Expected: 2개 테스트 모두 PASSED

- [ ] **Step 5: 커밋**

```bash
git add baton/claude_client.py tests/test_claude_client.py
git commit -m "feat: Claude API 클라이언트 구현"
```

---

## Task 4: Slack Bot 기본 연결 + DM 답변

**Files:**
- Create: `baton/app.py`

- [ ] **Step 1: app.py 작성**

`baton/app.py`:
```python
import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from baton.knowledge_store import KnowledgeStore
from baton.claude_client import ClaudeClient

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])
store = KnowledgeStore()
claude = ClaudeClient(api_key=os.environ["ANTHROPIC_API_KEY"])
PREDECESSOR_NAME = os.environ.get("PREDECESSOR_NAME", "전임자")


@app.event("message")
def handle_dm(event, say, logger):
    """DM으로 오는 질문에 전임자 스타일로 답변"""
    if event.get("channel_type") != "im":
        return
    if event.get("bot_id"):  # 봇 메시지 무시
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
    say("📚 슬랙 채널 학습을 시작합니다... (시간이 걸릴 수 있어요)")
    # learner는 Task 5에서 연결
    say("✅ 학습 완료! DM으로 질문해보세요.")


@app.command("/바톤-인계")
def start_handover(ack, say):
    """인계 프로세스 시작 (Task 7에서 구현)"""
    ack()
    say("🔄 인계 프로세스를 준비 중입니다...")


if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
```

- [ ] **Step 2: 봇 실행 테스트**

```bash
python -m baton.app
```

Expected: `⚡️ Bolt app is running!` 메시지 출력

슬랙에서 봇에게 DM 메시지 전송 → 답변 확인

- [ ] **Step 3: 커밋**

```bash
git add baton/app.py
git commit -m "feat: Slack 봇 기본 연결 및 DM 답변 구현"
```

---

## Task 5: 슬랙 히스토리 학습 (SlackLearner)

**Files:**
- Create: `baton/learner.py`
- Create: `tests/test_learner.py`

- [ ] **Step 1: 테스트 작성**

`tests/test_learner.py`:
```python
import pytest
from unittest.mock import MagicMock, patch
from baton.learner import SlackLearner
from baton.knowledge_store import KnowledgeStore
from baton.claude_client import ClaudeClient


@pytest.fixture
def learner(tmp_path):
    store = KnowledgeStore(base_dir=str(tmp_path))
    claude = MagicMock(spec=ClaudeClient)
    claude.extract_knowledge.return_value = {
        "업무_프로세스": ["비용신청은 3일 전까지"],
        "자주_묻는_질문": ["Q: 연차는? A: 인사팀에 신청"],
        "담당자_스타일": []
    }
    return SlackLearner(slack_token="xoxb-fake", claude=claude, store=store)


def test_format_messages(learner):
    messages = [
        {"user": "U001", "text": "비용신청 어떻게 해요?"},
        {"user": "U002", "text": "경리팀에 3일 전에 제출하면 돼요"},
    ]
    result = learner._format_messages(messages)
    assert "비용신청" in result
    assert "경리팀" in result


def test_save_extracted(learner, tmp_path):
    extracted = {
        "업무_프로세스": ["비용신청 절차"],
        "자주_묻는_질문": [],
        "담당자_스타일": []
    }
    learner._save_extracted(extracted, channel_name="일반")
    result = learner.store.read_all()
    assert "비용신청" in result
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_learner.py -v
```

Expected: `ModuleNotFoundError: No module named 'baton.learner'`

- [ ] **Step 3: SlackLearner 구현**

`baton/learner.py`:
```python
import time
from slack_sdk import WebClient
from baton.claude_client import ClaudeClient
from baton.knowledge_store import KnowledgeStore


class SlackLearner:
    HISTORY_DAYS = 90  # 슬랙 무료 플랜 기준 90일

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
            messages.extend([m for m in result["messages"] if m.get("text") and not m.get("bot_id")])
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
        if len(messages) < 3:  # 메시지가 너무 적으면 스킵
            return
        text = self._format_messages(messages)
        # 메시지가 너무 길면 앞 3000자만 처리 (토큰 절약)
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
```

- [ ] **Step 4: app.py에 learner 연결**

`baton/app.py`의 import 블록 아래에 추가:
```python
from baton.learner import SlackLearner

learner = SlackLearner(
    slack_token=os.environ["SLACK_BOT_TOKEN"],
    claude=claude,
    store=store
)
```

`trigger_learning` 함수를 아래로 교체:
```python
@app.command("/바톤-학습")
def trigger_learning(ack, say, logger):
    ack()
    say("📚 슬랙 채널 학습을 시작합니다...")
    count = learner.learn_all_channels()
    say(f"✅ {count}개 채널 학습 완료! DM으로 질문해보세요.")
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_learner.py -v
```

Expected: 2개 테스트 모두 PASSED

- [ ] **Step 6: 커밋**

```bash
git add baton/learner.py baton/app.py tests/test_learner.py
git commit -m "feat: 슬랙 히스토리 자동 학습 구현"
```

---

## Task 6: 주간 자동 학습 스케줄러

**Files:**
- Create: `baton/scheduler.py`
- Modify: `baton/app.py`

- [ ] **Step 1: scheduler.py 작성**

`baton/scheduler.py`:
```python
from apscheduler.schedulers.background import BackgroundScheduler
from baton.learner import SlackLearner


class LearningScheduler:
    def __init__(self, learner: SlackLearner):
        self.learner = learner
        self.scheduler = BackgroundScheduler(timezone="Asia/Seoul")

    def start(self) -> None:
        """매주 월요일 오전 6시 자동 학습 등록 후 시작"""
        self.scheduler.add_job(
            self.learner.learn_all_channels,
            trigger="cron",
            day_of_week="mon",
            hour=6,
            minute=0,
            id="weekly_learning",
            replace_existing=True
        )
        self.scheduler.start()

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown()
```

- [ ] **Step 2: app.py에 스케줄러 연결**

import 추가:
```python
from baton.scheduler import LearningScheduler
```

`if __name__ == "__main__":` 블록을 아래로 교체:
```python
if __name__ == "__main__":
    scheduler = LearningScheduler(learner)
    scheduler.start()
    print("📅 매주 월요일 오전 6시 자동 학습 스케줄러 시작")
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
```

- [ ] **Step 3: 봇 재실행 후 스케줄러 로그 확인**

```bash
python -m baton.app
```

Expected: `📅 매주 월요일 오전 6시 자동 학습 스케줄러 시작` 출력 후 봇 실행

- [ ] **Step 4: 커밋**

```bash
git add baton/scheduler.py baton/app.py
git commit -m "feat: 주간 자동 학습 스케줄러 구현"
```

---

## Task 7: 온보딩 흐름 (인계자 검토 → 인수자 전달)

**Files:**
- Create: `baton/onboarding.py`
- Create: `tests/test_onboarding.py`
- Modify: `baton/app.py`

- [ ] **Step 1: 테스트 작성**

`tests/test_onboarding.py`:
```python
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
    assert "🔴" in result  # high priority


def test_format_onboarding_message(manager):
    items = [{"category": "업무_프로세스", "content": "비용신청 절차"}]
    result = manager._format_onboarding_message(items, predecessor_name="김철수")
    assert "김철수" in result
    assert "비용신청" in result
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_onboarding.py -v
```

Expected: `ModuleNotFoundError: No module named 'baton.onboarding'`

- [ ] **Step 3: OnboardingManager 구현**

`baton/onboarding.py`:
```python
from slack_sdk import WebClient
from baton.claude_client import ClaudeClient
from baton.knowledge_store import KnowledgeStore

PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}


class OnboardingManager:
    def __init__(self, slack_client: WebClient, claude: ClaudeClient, store: KnowledgeStore):
        self.slack = slack_client
        self.claude = claude
        self.store = store
        # 진행 중인 인계 세션 임시 저장 {predecessor_user_id: candidates}
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
                             selected_ids: list[int], predecessor_name: str) -> None:
        """선택된 항목으로 인계시트 생성 → 인수자 DM 전송"""
        candidates = self._sessions.get(predecessor_user_id, [])
        selected = [c for c in candidates if c["id"] in selected_ids]

        dm = self.slack.conversations_open(users=successor_user_id)
        channel_id = dm["channel"]["id"]
        self.slack.chat_postMessage(
            channel=channel_id,
            text=self._format_onboarding_message(selected, predecessor_name)
        )
        # 세션 정리
        self._sessions.pop(predecessor_user_id, None)
```

- [ ] **Step 4: app.py에 온보딩 명령어 연결**

import 추가:
```python
from baton.onboarding import OnboardingManager

onboarding = OnboardingManager(slack_client=app.client, claude=claude, store=store)
```

`/바톤-인계` 명령어 교체:
```python
@app.command("/바톤-인계")
def start_handover(ack, say, command):
    """인계 프로세스 시작. 사용법: /바톤-인계"""
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
    # 형식: <@U123456> 1,2,3
    parts = text.split()
    if len(parts) < 2:
        say("사용법: `/바톤-인계-확정 @인수자 1,2,3`")
        return
    # <@U123456> → U123456
    successor_id = parts[0].strip("<@>").split("|")[0]
    selected_ids = [int(x) for x in parts[1].split(",") if x.strip().isdigit()]
    predecessor_id = command["user_id"]

    onboarding.confirm_and_deliver(predecessor_id, successor_id, selected_ids, PREDECESSOR_NAME)
    say(f"✅ <@{successor_id}>님께 온보딩 내용을 전달했습니다!")
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_onboarding.py -v
```

Expected: 2개 테스트 모두 PASSED

- [ ] **Step 6: 슬랙에서 실제 흐름 테스트**

1. `/바톤-인계` 입력 → DM으로 후보 목록 수신 확인
2. `/바톤-인계-확정 @동료 1,2,3` 입력 → 동료 DM으로 온보딩 메시지 수신 확인

- [ ] **Step 7: 커밋**

```bash
git add baton/onboarding.py baton/app.py tests/test_onboarding.py
git commit -m "feat: 인계자 검토 및 인수자 온보딩 흐름 구현"
```

---

## Task 8: 실전 시뮬레이션 (페르소나 봇)

**Files:**
- Create: `baton/personas.py`
- Modify: `baton/app.py`

- [ ] **Step 1: personas.py 작성**

`baton/personas.py`:
```python
import time
from slack_sdk import WebClient
from baton.claude_client import ClaudeClient

# 페르소나 정의 (강성 5명 포함)
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
            text=f"🎭 *실전 시뮬레이션을 시작합니다!*\n{persona_count}명의 가상 훈련생이 순서대로 DM을 보냅니다.\n실제처럼 응답해보세요!"
        )

        for persona in personas:
            question = self._generate_question(persona)
            emoji = "😤" if persona["type"] == "difficult" else "😊"
            self.slack.chat_postMessage(
                channel=channel_id,
                text=f"{emoji} *[{persona['name']}]*: {question}"
            )
            time.sleep(2)  # 메시지 간격
```

- [ ] **Step 2: app.py에 시뮬레이션 명령어 추가**

import 추가:
```python
from baton.personas import SimulationManager

simulation = SimulationManager(slack_client=app.client, claude=claude)
```

명령어 추가:
```python
@app.command("/바톤-시뮬레이션")
def run_simulation(ack, say, command):
    """실전 시뮬레이션 시작. 사용법: /바톤-시뮬레이션 5"""
    ack()
    text = command.get("text", "5").strip()
    count = int(text) if text.isdigit() else 5
    count = min(count, len(PERSONAS) if hasattr(simulation, 'PERSONAS') else 10)
    user_id = command["user_id"]

    say(f"🎭 {count}명 페르소나 시뮬레이션을 시작합니다!")
    simulation.run_simulation(target_user_id=user_id, persona_count=count)
```

`from baton.personas import PERSONAS` import도 추가:
```python
from baton.personas import SimulationManager, PERSONAS

simulation = SimulationManager(slack_client=app.client, claude=claude)
```

명령어의 count 계산 수정:
```python
    count = min(count, len(PERSONAS))
```

- [ ] **Step 3: 슬랙에서 시뮬레이션 테스트**

```
/바톤-시뮬레이션 3
```

Expected: DM으로 페르소나 3명이 순서대로 질문 메시지 전송

- [ ] **Step 4: 커밋 및 푸시**

```bash
git add baton/personas.py baton/app.py
git commit -m "feat: 실전 시뮬레이션 페르소나 봇 구현"
git push
```

---

## 전체 테스트

- [ ] **전체 테스트 실행**

```bash
pytest tests/ -v
```

Expected: 전체 테스트 PASSED

- [ ] **전체 흐름 시연 순서**

1. `/바톤-학습` → 채널 학습 완료 확인
2. DM으로 질문 → 전임자 스타일 답변 확인
3. `/바톤-인계` → 후보 목록 DM 수신 확인
4. `/바톤-인계-확정 @동료 1,2` → 온보딩 메시지 전달 확인
5. `/바톤-시뮬레이션 5` → 페르소나 질문 DM 수신 확인

---

## (선택) 실시간 채널 메시지 학습

스펙의 "상시 실시간 학습" 기능. 주간 학습으로 MVP는 충분하나, 추가 구현 시 아래를 `app.py`에 추가:

```python
@app.event("message")
def handle_channel_message(event, logger):
    """채널 새 메시지를 실시간으로 지식창고에 추가"""
    if event.get("channel_type") == "im":
        return  # DM은 학습 제외
    if event.get("bot_id"):
        return  # 봇 메시지 제외
    text = event.get("text", "").strip()
    if len(text) < 10:
        return  # 너무 짧은 메시지 제외
    extracted = claude.extract_knowledge(text)
    for category in ["업무_프로세스", "자주_묻는_질문", "담당자_스타일"]:
        for item in extracted.get(category, []):
            if item:
                store.append(category, f"- {item}")
```

추가 필요 OAuth Scope: `channels:history`(이미 포함)

---

## 슬랙 앱 설정 체크리스트

Slack API 대시보드(api.slack.com)에서 아래 권한이 설정되어야 합니다.

**OAuth Scopes (Bot Token):**
- `channels:history` — 채널 메시지 읽기
- `channels:read` — 채널 목록 조회
- `chat:write` — 메시지 전송
- `commands` — 슬래시 명령어
- `im:history` — DM 히스토리
- `im:read` — DM 채널 접근
- `im:write` — DM 열기
- `users:read` — 사용자 정보

**Slash Commands 등록:**
- `/바톤-학습`
- `/바톤-인계`
- `/바톤-인계-확정`
- `/바톤-시뮬레이션`

**Socket Mode:** 활성화 필요
