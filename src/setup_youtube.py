import os
import json
import urllib.request
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

# Scopes needed for YouTube upload and comments
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl"
REDIRECT_PORT = 8080
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"

authorization_code = None

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global authorization_code
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        
        if "code" in params:
            authorization_code = params["code"][0]
            self.wfile.write(b"<h1>Authorization Successful!</h1><p>You can close this tab and return to the terminal.</p>")
        else:
            self.wfile.write(b"<h1>Authorization Failed!</h1><p>No authorization code was found in the redirect.</p>")
            
    def log_message(self, format, *args):
        # Mute standard HTTP logging to keep console output clean
        return

def get_refresh_token(client_id: str, client_secret: str, code: str) -> dict:
    """Exchanges the authorization code for a refresh token."""
    url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode("utf-8"))

def main():
    print("=== YouTube OAuth2 Refresh Token Generator ===")
    print("To run this, you must have created a Google Cloud Project with the YouTube Data API enabled,")
    print("and configured an OAuth Consent Screen as a 'Desktop App' credentials.")
    print("")
    
    client_id = input("Enter your Client ID: ").strip()
    client_secret = input("Enter your Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("Error: Client ID and Client Secret are required.")
        return

    # Build authorization URL
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={urllib.parse.quote(SCOPES)}&"
        "access_type=offline&"
        "prompt=consent"
    )

    print("\nStarting local server to capture redirect...")
    server = HTTPServer(("localhost", REDIRECT_PORT), OAuthHandler)
    
    print("\nOpening browser to authorize Google Account...")
    print(f"If the browser doesn't open automatically, click here:\n{auth_url}\n")
    webbrowser.open(auth_url)
    
    # Wait for a single request containing the code
    server.handle_request()
    server.server_close()
    
    if not authorization_code:
        print("\nError: Failed to obtain authorization code.")
        return
        
    print("\nAuthorization code received! Exchanging code for refresh token...")
    try:
        tokens = get_refresh_token(client_id, client_secret, authorization_code)
        refresh_token = tokens.get("refresh_token")
        
        print("\n================ SUCCESS ================")
        print(f"Your YOUTUBE_REFRESH_TOKEN is:\n\n{refresh_token}\n")
        print("Save this token as a secret named 'YOUTUBE_REFRESH_TOKEN' in your GitHub repository secrets.")
        print("=========================================")
    except Exception as e:
        print(f"\nError exchanging code for token: {e}")

if __name__ == "__main__":
    main()
