---
name: google-calendar-sync
description: Manages scheduling, meetings, and calendar events via n8n automation.
metadata:
  version: "1.0"
  type: "automation"
---

# Google Calendar Skill

This skill allows the agent to interact with the user's Google Calendar.

## Prerequisites
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `google-api-python-client`
- `credentials.json` (OAuth 2.0 Client ID) in the root or `skills/google_calendar/` directory.

## Capabilities

1.  **List Events**: Retrieve upcoming events.
2.  **Create Event**: Schedule a new event.
3.  **Update Event**: Modify an existing event.
4.  **Delete Event**: Remove an event.

## Setup

1.  Place `credentials.json` in `E:\Drive\Antigravitiy\Orchesta assistant\skills\google_calendar\`.
2.  Run `python skills/google_calendar/authenticate.py` to generate `token.json`.

## Usage (Python)

```python
from skills.google_calendar.calendar_client import CalendarClient

client = CalendarClient()
events = client.list_events(max_results=5)
for event in events:
    print(event['summary'], event['start'])
```
