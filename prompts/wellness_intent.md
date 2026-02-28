# Wellness Intent Extraction Prompt

Analyze user input for wellness/nutrition intent.
User said: "{user_input}"

Current Meals:
{meals_summary}

Intent Categories:
1. delete_meal: User wants to delete/remove a specific meal (e.g., "Xoá bữa 2", "bỏ cái trưa nay").
2. nutrition_summary: User wants to know total calories or what they ate (e.g., "Hôm nay tôi ăn bao nhiêu?", "check calo").
3. nutrition_advice: General nutrition question (e.g., "Ăn phở béo không?", "Tư vấn bữa tối").
4. exercise_advice: DOMS/Energy reporting and workout advice.
5. other: Anything else.

Return JSON: {{"intent": "category", "index": null_or_int, "reasoning": "..."}}
