# n8n Skill Extraction Prompt

Extract the action and parameters for an automation workflow.
User Input: {user_input}
Possible Actions: google_calendar_add, google_calendar_list, notion_add_page, slack_message, generic_api_call.

Return a JSON object:
{{
    "action": "action_name",
    "params": {{ ... }},
    "context": "{role}"
}}
