# B2G- 서비스 기획 문서

> 팀 기획 문서 저장소입니다.

## 폴더 구조

```
docs/
├── 문제정의/     ← 우리가 풀려는 문제
│   ├── 김주하.md
│   ├── 신성.md
│   └── 재은.md
├── 솔루션/       ← 우리의 해결책
│   ├── 김주하.md
│   ├── 신성.md
│   └── 재은.md
└── GTM/          ← 시장 진입 전략
    ├── 김주하.md
    ├── 신성.md
    └── 재은.md
```

## 작성 방법

1. 내 이름의 파일을 열어 작성한다
2. 저장 후 커밋 & 푸시한다
3. 다른 팀원 파일도 읽고 피드백을 남긴다

## 팀원

| 이름 | 역할 |
|------|------|
| 김주하 | |
| 신성 | |
| 재은 | |

---

## 인수인계서 자동 생성 도구

Slack 메시지를 분석해 인수인계서를 자동으로 생성하는 스크립트입니다.

### 준비물

- Python 3.10 이상
- Slack User Token (`xoxp-...`) 또는 Bot Token (`xoxb-...`)
- Anthropic API Key

### 사용법

```bash
# 1. 의존성 설치
cd scripts
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env
# .env 파일을 열어 토큰 입력

# 3. 실행 (--user-id에 분석할 사람의 Slack User ID 입력)
python generate_handover.py --user-id U095TEK2W2C --output 인수인계서.md
```

### Slack User ID 확인 방법

Slack에서 해당 사람의 프로필 클릭 → `...더보기` → `멤버 ID 복사`

### 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--user-id` | 분석할 Slack 사용자 ID (필수) | - |
| `--output` | 출력 파일명 | `인수인계서.md` |
| `--limit` | 채널당 최대 메시지 수 | `200` |
| `--model` | 사용할 Claude 모델 | `claude-sonnet-4-6` |
