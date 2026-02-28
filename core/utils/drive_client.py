import io
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from core.utils.google_auth import GoogleAuthManager

class DriveClient:
    def __init__(self):
        self.auth = GoogleAuthManager()
        self.service = self.auth.get_service('drive', 'v3')

    def list_files(self, query="mimeType='application/vnd.google-apps.spreadsheet' or mimeType='application/pdf'", max_results=10):
        """Lists files in Google Drive."""
        results = self.service.files().list(
            q=query, pageSize=max_results, fields="nextPageToken, files(id, name, mimeType)").execute()
        return results.get('files', [])

    def download_file(self, file_id, destination_path):
        """Downloads a file from Drive."""
        request = self.service.files().get_media(fileId=file_id)
        with io.FileIO(destination_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                # print(f"Download {int(status.progress() * 100)}%.")
        return destination_path

    def export_google_doc(self, file_id, destination_path, mime_type='application/pdf'):
        """Exports a Google Doc/Sheet/Slide to a standard format."""
        request = self.service.files().export_media(fileId=file_id, mimeType=mime_type)
        with io.FileIO(destination_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
        return destination_path

    def upload_file(self, file_path, folder_id=None, mime_type=None):
        """Uploads a file to Drive."""
        file_metadata = {'name': os.path.basename(file_path)}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(file_path, mimetype=mime_type)
        file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')

if __name__ == "__main__":
    import os
    client = DriveClient()
    files = client.list_files(query="name contains 'Business Analysis'", max_results=5)
    for f in files:
        print(f"Found: {f['name']} ({f['id']})")
