"""
Slack 채널 메시지를 분석해 인수인계서를 자동 생성하는 스크립트

사용법:
    pip install -r requirements.txt
    cp .env.example .env  # 토큰 입력 후
    python generate_handover.py --user-id U095TEK2W2C --output 인수인계서.md
"""

import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except ImportError:
    sys.exit("slack_sdk 미설치. 'pip install -r requirements.txt' 실행 후 재시도하세요.")

try:
    import anthropic
except ImportError:
    sys.exit("anthropic 미설치. 'pip install -r requirements.txt' 실행 후 재시도하세요.")


def ts_to_date(ts: str) -> str:
    return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M")


def get_all_channels(client: WebClient) -> list[dict]:
    channels = []
    cursor = None
    while True:
        resp = client.conversations_list(limit=200, cursor=cursor, types="public_channel,private_channel")
        channels.extend(resp["channels"])
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    return channels


def get_channel_messages(client: WebClient, channel_id: str, limit: int = 200) -> list[dict]:
    messages = []
    cursor = None
    while len(messages) < limit:
        resp = client.conversations_history(
            channel=channel_id,
            limit=min(200, limit - len(messages)),
            cursor=cursor
        )
        messages.extend(resp.get("messages", []))
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not resp.get("has_more") or not cursor:
            break
    return messages


def collect_user_messages(client: WebClient, user_id: str, max_per_channel: int = 200) -> dict[str, list]:
    print("채널 목록 조회 중...")
    channels = get_all_channels(client)
    print(f"총 {len(channels)}개 채널 발견")

    result = {}
    for ch in channels:
        name = ch["name"]
        try:
            msgs = get_channel_messages(client, ch["id"], limit=max_per_channel)
            user_msgs = [
                m for m in msgs
                if m.get("user") == user_id
                and m.get("type") == "message"
                and m.get("subtype") not in ("channel_join", "channel_leave", "bot_message")
            ]
            if user_msgs:
                result[name] = user_msgs
                print(f"  ✓ #{name}: {len(user_msgs)}건")
        except SlackApiError as e:
            print(f"  ✗ #{name}: {e.response['error']} (건너뜀)")

    return result


def format_messages_for_prompt(messages_by_channel: dict[str, list]) -> str:
    lines = []
    total = sum(len(v) for v in messages_by_channel.values())
    lines.append(f"총 {total}건의 메시지 ({len(messages_by_channel)}개 채널)\n")

    for channel, msgs in messages_by_channel.items():
        lines.append(f"\n### 채널: #{channel} ({len(msgs)}건)")
        for m in sorted(msgs, key=lambda x: x["ts"]):
            date = ts_to_date(m["ts"])
            text = m.get("text", "").replace("\n", " ")[:400]
            lines.append(f"- [{date}] {text}")

    return "\n".join(lines)


def generate_with_claude(messages_text: str, api_key: str, model: str = "claude-sonnet-4-6") -> str:
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""다음은 Slack에서 수집한 매니저의 메시지 데이터입니다.
이 메시지들을 분석하여 후임자가 업무를 이어받을 수 있도록 **인수인계서**를 작성해주세요.

{messages_text}

---

아래 항목을 모두 포함하여 마크다운 형식으로 작성하세요:

1. **과정/업무 개요** - 어떤 업무를 담당했는지
2. **일일 업무 루틴** - 매일 반복되는 업무
3. **출결 관리** - 출결 방식, 오류 대응 이력
4. **행정 업무** - 훈련장려금, 디자인툴 환급 등
5. **프로젝트 일정** - 진행한 프로젝트 및 일정
6. **취업 지원 프로그램** - 운영한 프로그램 목록
7. **채널 구성** - 슬랙 채널별 역할
8. **주요 이슈 및 대응 이력** - 발생했던 문제와 해결 방법
9. **주의사항 및 인계 포인트** - 후임자가 꼭 알아야 할 사항

날짜는 메시지 타임스탬프를 변환하여 사용하세요."""

    print("Claude로 인수인계서 생성 중...")
    response = client.messages.create(
        model=model,
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def main():
    parser = argparse.ArgumentParser(description="Slack 메시지 기반 인수인계서 자동 생성")
    parser.add_argument("--user-id", required=True, help="분석할 Slack 사용자 ID (예: U095TEK2W2C)")
    parser.add_argument("--output", default="인수인계서.md", help="출력 파일명 (기본값: 인수인계서.md)")
    parser.add_argument("--limit", type=int, default=200, help="채널당 최대 메시지 수 (기본값: 200)")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Claude 모델 ID")
    args = parser.parse_args()

    slack_token = os.getenv("SLACK_USER_TOKEN") or os.getenv("SLACK_BOT_TOKEN")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not slack_token:
        sys.exit("오류: SLACK_USER_TOKEN 또는 SLACK_BOT_TOKEN 환경변수가 필요합니다.")
    if not anthropic_key:
        sys.exit("오류: ANTHROPIC_API_KEY 환경변수가 필요합니다.")

    slack_client = WebClient(token=slack_token)

    messages_by_channel = collect_user_messages(slack_client, args.user_id, args.limit)

    if not messages_by_channel:
        sys.exit(f"사용자 {args.user_id}의 메시지를 찾을 수 없습니다.")

    messages_text = format_messages_for_prompt(messages_by_channel)
    handover_doc = generate_with_claude(messages_text, anthropic_key, args.model)

    header = f"# 인수인계서\n\n> 생성일: {datetime.now().strftime('%Y-%m-%d')}  \n> 분석 대상 User ID: `{args.user_id}`  \n> 분석 채널 수: {len(messages_by_channel)}개  \n\n---\n\n"

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(header + handover_doc)

    print(f"\n✅ 완료! '{args.output}' 파일로 저장되었습니다.")


if __name__ == "__main__":
    main()
