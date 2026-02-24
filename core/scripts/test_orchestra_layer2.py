from core.agents.supervisor import build_supervisor_graph
import os

def test_orchestra_routing():
    print("--- 🔬 Testing Orchestra 2.0 Routing & Expertise ---")
    
    app = build_supervisor_graph()
    
    test_cases = [
        {
            "name": "PhD Research",
            "query": "Làm thế nào để áp dụng mô hình Fuzzy AHP cho việc đánh giá rủi ro tín dụng tại Việt Nam?",
            "expected_route": "research"
        },
        {
            "name": "Supporting Wife (Bank)",
            "query": "Vợ tôi đang cần cải thiện chỉ số NPS cho phân khúc SME tại ngân hàng, hãy nháp giúp tôi một email chiến lược.",
            "expected_route": "bank"
        },
        {
            "name": "Mimi's Tutor",
            "query": "Mimi đang gặp khó khăn với bài tập toán lớp 6 về phân số, hãy giúp em ấy theo cách Socratic.",
            "expected_route": "mimi"
        }
    ]
    
    for case in test_cases:
        print(f"\n[TestCase]: {case['name']}")
        print(f"Query: {case['query']}")
        
        initial_state = {
            "messages": [case["query"]],
            "input_file": "",
            "file_content": None,
            "extracted_skill": None,
            "skill_saved": False,
            "routing_category": None
        }
        
        try:
            # We just take the first few steps to verify routing and specialized response
            results = list(app.stream(initial_state))
            # In LangGraph, supervisor is the first node
            # The second node is the specialized expert
            for output in results:
                for node, value in output.items():
                    print(f"  [{node}]: {value['messages'][-1][:100]}...")
            
        except Exception as e:
            print(f"  FAILED: {e}")

if __name__ == "__main__":
    test_orchestra_routing()
