"""
바톤 슬랙 연결 테스트 스크립트
API 토큰 받은 후 .env 파일 채우고 실행: python test_connection.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

def test_env_vars():
    required = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "ANTHROPIC_API_KEY"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(f"❌ .env 파일에 아래 항목이 없어요:")
        for m in missing:
            print(f"   - {m}")
        return False
    print("✅ 환경변수 모두 확인됨")
    return True

def test_slack_connection():
    from slack_sdk import WebClient
    client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    result = client.auth_test()
    print(f"✅ 슬랙 연결 성공! 봇 이름: {result['bot_id']}")
    return True

def test_claude_connection():
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=10,
        messages=[{"role": "user", "content": "안녕"}]
    )
    print(f"✅ Claude API 연결 성공!")
    return True

if __name__ == "__main__":
    print("=== 바톤 연결 테스트 ===\n")
    if not test_env_vars():
        exit(1)
    try:
        test_slack_connection()
    except Exception as e:
        print(f"❌ 슬랙 연결 실패: {e}")
    try:
        test_claude_connection()
    except Exception as e:
        print(f"❌ Claude API 연결 실패: {e}")
    print("\n=== 테스트 완료 ===")
