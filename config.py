"""Flask and spotify configuration."""
import os


# FLASK
class Config(object):
    """Flask base config, specifies general settings."""

    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = "./.flask_session/"
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


class ProductionConfig(Config):
    """Flask production config, making sure all is set for dev env."""

    TESTING = False
    DEBUG = False
    SHOW_DIALOG = False
    FLASK_ENV = "production"
    REDIRECT_URI = "https://spodivide.com/login"


class DevelopmentConfig(Config):
    """Flask development config, such that we can debug."""

    TESTING = True
    DEBUG = True
    SHOW_DIALOG = True
    FLASK_ENV = "development"
    # REDIRECT_URI = "http://192.168.1.21:5000/login"
    REDIRECT_URI = "http://10.50.5.128:5000/login"


# API_BASE = "https://accounts.spotify.com"

# Old redirect uri's:
# REDIRECT_URI = "https://spodivide.herokuapp.com/login"
# REDIRECT_URI = "https://spodivide.com/login"
# Make sure you add this to Redirect URIs in the setting of the
# application dashboard of spotify developer
