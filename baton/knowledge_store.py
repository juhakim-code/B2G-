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
        for cat, path in self.files.items():
            if not path.exists():
                path.write_text(f"# {cat}\n", encoding="utf-8")

    def read_all(self) -> str:
        parts = []
        # 기존 마크다운 카테고리 파일
        for cat in ["업무_프로세스", "자주_묻는_질문", "담당자_스타일"]:
            path = self.files[cat]
            text = path.read_text(encoding="utf-8").strip()
            if text and text != f"# {cat}":
                parts.append(text)
        # 슬랙 채널 추출 txt 파일 + 인수인계서 md 파일
        for ext in ("*.txt", "인수인계서*.md"):
            for path in sorted(self.base_dir.glob(ext)):
                text = path.read_text(encoding="utf-8").strip()
                if text:
                    parts.append(f"## [{path.stem}]\n{text}")
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
