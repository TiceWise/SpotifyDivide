"""Flask configuration."""
from os import environ, path

TESTING = True
DEBUG = True
SHOW_DIALOG =True

FLASK_ENV = 'development'
CLIENT_ID = environ.get('SPODI_CLIENT_ID')
CLIENT_SECRET = environ.get('SPODI_CLIENT_SECRET')
SECRET_SESSION_KEY = environ.get('SECRET_SESSION_KEY')
SCOPE = 'playlist-modify-private,playlist-modify-public,user-library-modify'
API_BASE = 'https://accounts.spotify.com'

# Make sure you add this to Redirect URIs in the setting of the application dashboard
REDIRECT_URI = "http://127.0.0.1:5000/api_callback"