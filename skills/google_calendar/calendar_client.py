import os
import datetime
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

class CalendarClient:
    def __init__(self, credentials_path=None, token_path=None):
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.credentials_path = credentials_path or os.path.join(self.base_path, 'credentials.json')
        self.token_path = token_path or os.path.join(self.base_path, 'token.json')
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticates with the Google Calendar API."""
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(f"Credentials file not found at: {self.credentials_path}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())

        self.service = build('calendar', 'v3', credentials=self.creds)

    def list_events(self, max_results=10, time_min=None):
        """Lists upcoming events."""
        if not time_min:
            time_min = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        print(f"Getting the upcoming {max_results} events")
        events_result = self.service.events().list(
            calendarId='primary', 
            timeMin=time_min,
            maxResults=max_results, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])

    def create_event(self, summary, start_time, end_time, description=None, location=None):
        """Creates a new event."""
        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time, # ISO 8601 format
                'timeZone': 'Asia/Ho_Chi_Minh', # Adjust as needed or make dynamic
            },
            'end': {
                'dateTime': end_time, # ISO 8601 format
                'timeZone': 'Asia/Ho_Chi_Minh',
            },
        }

        event = self.service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {event.get('htmlLink')}")
        return event

    def update_event(self, event_id, **kwargs):
        """Updates an existing event. kwargs can be summary, description, start, end, etc."""
        event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
        
        # Update fields
        for key, value in kwargs.items():
            if key in ['start', 'end']:
                 event[key] = {'dateTime': value, 'timeZone': 'Asia/Ho_Chi_Minh'}
            else:
                event[key] = value

        updated_event = self.service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        print(f"Event updated: {updated_event.get('htmlLink')}")
        return updated_event

    def delete_event(self, event_id):
        """Deletes an event."""
        self.service.events().delete(calendarId='primary', eventId=event_id).execute()
        print(f"Event deleted: {event_id}")
        return True

if __name__ == '__main__':
    # Test authentication
    try:
        client = CalendarClient()
        events = client.list_events(max_results=5)
        if not events:
            print('No upcoming events found.')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(start, event['summary'])
    except Exception as e:
        print(f"Authentication or API error: {e}")
