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
