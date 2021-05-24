"""Flask configuration."""
import os

TESTING = True
DEBUG = True
SHOW_DIALOG = True
SESSION_TYPE = "filesystem"
SESSION_FILE_DIR = "./.flask_session/"

FLASK_ENV = "development"
CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET")
SECRET_SESSION_KEY = os.environ.get("SECRET_SESSION_KEY")
SCOPE = ("playlist-read-private,"
         "playlist-modify-private,"
         "playlist-read-collaborative,"
         "playlist-modify-public,"
         "user-library-read,"
         "user-library-modify")
API_BASE = "https://accounts.spotify.com"

# Make sure you add this to Redirect URIs in the setting of the
# application dashboard
REDIRECT_URI = "http://127.0.0.1:5000/login"
