"""Flask configuration."""
import os

# FLASK
# TESTING = True
# DEBUG = True
# SHOW_DIALOG = True
TESTING = False
DEBUG = False
SHOW_DIALOG = False
SESSION_TYPE = "filesystem"
SESSION_FILE_DIR = "./.flask_session/"
# FLASK_ENV = "development"
FLASK_ENV = "production"
SECRET_KEY = os.environ.get("SECRET_SESSION_KEY")

# SPOTIFY
CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET")
SCOPE = (
    "playlist-read-private,"
    "playlist-modify-private,"
    "playlist-read-collaborative,"
    "playlist-modify-public,"
    "user-library-read,"
    "user-library-modify"
)
API_BASE = "https://accounts.spotify.com"
# REDIRECT_URI = "http://192.168.1.20:5000/login"
REDIRECT_URI = "http://127.0.0.1:5000/login"
# Make sure you add this to Redirect URIs in the setting of the
# application dashboard of spotify developer
