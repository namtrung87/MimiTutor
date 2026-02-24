import json
import os

class SimpleSkillStore:
    """
    Một hệ thống lưu trữ kỹ năng đơn giản dưới dạng JSON (PoC cho Vector Database).
    """
    def __init__(self, storage_path="core/skill_library.json"):
        self.storage_path = storage_path
        self._initialize_store()

    def _initialize_store(self):
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def add_skill(self, skill_card):
        with open(self.storage_path, 'r', encoding='utf-8') as f:
            skills = json.load(f)
        
        # Tránh trùng lặp tiêu đề
        if not any(s['title'] == skill_card['title'] for s in skills):
            skills.append(skill_card)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(skills, f, indent=4, ensure_ascii=False)
            return True
        return False

    def search_skills(self, query):
        """
        Tìm kiếm kỹ năng đơn giản theo từ khóa trong tiêu đề hoặc mô tả.
        (Mô phỏng Vector Search)
        """
        with open(self.storage_path, 'r', encoding='utf-8') as f:
            skills = json.load(f)
        
        results = [s for s in skills if query.lower() in s['title'].lower() or query.lower() in s['description'].lower()]
        return results
