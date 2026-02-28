import base64
from email.mime.text import MIMEText
from core.utils.google_auth import GoogleAuthManager

class GmailClient:
    def __init__(self):
        self.auth = GoogleAuthManager()
        self.service = self.auth.get_service('gmail', 'v1')

    def list_messages(self, query='', max_results=10):
        """Lists Gmail messages matching the query."""
        results = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        return results.get('messages', [])

    def get_message(self, msg_id):
        """Gets a full message snippet and body."""
        message = self.service.users().messages().get(userId='me', id=msg_id).execute()
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        
        # Simple body extraction (first part)
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    body = base64.urlsafe_b64decode(data).decode()
                    break
        elif 'body' in payload:
            data = payload['body'].get('data', '')
            body = base64.urlsafe_b64decode(data).decode()

        return {
            'id': msg_id,
            'subject': subject,
            'from': sender,
            'snippet': message.get('snippet', ''),
            'body': body
        }

    def send_message(self, to, subject, body):
        """Sends an email."""
        message = MIMEText(body)
        message['to'] = to
        message['from'] = 'me'
        message['subject'] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': raw_message}
        
        send_result = self.service.users().messages().send(userId='me', body=create_message).execute()
        print(f"Message sent! ID: {send_result.get('id')}")
        return send_result

if __name__ == "__main__":
    # Test (Expects interaction if token_unified.json doesn't exist)
    client = GmailClient()
    messages = client.list_messages(max_results=3)
    for m in messages:
        details = client.get_message(m['id'])
        print(f"- {details['subject']} FROM {details['from']}")
