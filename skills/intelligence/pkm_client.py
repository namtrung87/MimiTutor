import os
import datetime

class PKMClient:
    """
    Client for Personal Knowledge Management (Second Brain).
    Supports localized Obsidian vault integration.
    """
    def __init__(self, vault_path=None):
        # Default to a subdirectory in the project or a user-defined path
        self.vault_path = vault_path or os.path.join(os.getcwd(), "SecondBrain")
        if not os.path.exists(self.vault_path):
            os.makedirs(self.vault_path)

    def save_learning_log(self, topic: str, content: str, tags: list = None):
        """Save a formatted learning log to the vault."""
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        file_name = f"{date_str} - {topic}.md".replace("/", "-")
        file_path = os.path.join(self.vault_path, "LearningLogs", file_name)
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        tag_str = " ".join([f"#{t}" for t in (tags or [])])
        markdown_content = f"""---
date: {date_str}
tags: [learning, {', '.join(tags or [])}]
type: learning_log
---
# {topic}

{content}

---
{tag_str}
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        return {"status": "success", "path": file_path}

    def generate_flashcard(self, question: str, answer: str, topic: str):
        """Save a flashcard (Spaced Repetiton) compatible with Obsidian-spaced-repetition plugin."""
        file_path = os.path.join(self.vault_path, "Flashcards", f"{topic}.md")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        flashcard_content = f"\n{question} #flashcard\n{answer}\n"
        
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(flashcard_content)
            
        return {"status": "success", "topic": topic}
