import requests
import json
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def chat(msg):
    r = requests.post('http://localhost:8000/mimi/chat', json={'message': msg, 'user_id': 'test'})
    print(f"Q: {msg}")
    resp = r.json().get('response', 'ERROR')
    print(f"A: {resp}")
    print()

chat('xin chao chi Mimi')
chat('Science Unit 8 hoc nhung noi dung nao?')
chat('Science Unit 8 học những vấn đề gì')
