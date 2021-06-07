"""Flask configuration."""
import os
# import sqlalchemy

# DATABASE
# DB_PASSWORD = os.environ.get("DB_PASSWORD")
# DB_PUBLIC_IP = os.environ.get("DB_PUBLIC_IP")
# DB_NAME = "spodivide"
# DB_PROJECT_ID = "spodivide"
# DB_INSTANCE_NAME = "spodivide"

# https://github.com/GoogleCloudPlatform/python-docs-samples/blob/master/cloud-sql/mysql/sqlalchemy/main.py
# SQLALCHEMY_DATABASE_URI = f"mysql+mysqldb://root:{DB_PASSWORD}@{DB_PUBLIC_IP}/{DB_NAME}?unix_socket=/cloudsql/{DB_PROJECT_ID}:{DB_INSTANCE_NAME}"
# first_str = str(sqlalchemy.engine.url.URL.create(
#             drivername="mysql+pymysql",
#             username='spodivide_db_user',  # e.g. "my-database-user"
#             password=DB_PASSWORD,  # e.g. "my-database-password"
#             host=DB_PUBLIC_IP,  # e.g. "127.0.0.1"
# #            port=3306,  # e.g. 3306
#             database=DB_NAME,  # e.g. "my-database-name"
#         ))
# SQLALCHEMY_DATABASE_URI = first_str  # + "?unix_socket=/cloudsql/" + os.environ.get("MYSQL_CONNECTION_NAME")

# SQLALCHEMY_TRACK_MODIFICATIONS = True
# SESSION_SQLALCHEMY_TABLE = "spodivide"

# FLASK
# TESTING = True
# DEBUG = True
# SHOW_DIALOG = True
# FLASK_ENV = "development"
TESTING = False
DEBUG = False
SHOW_DIALOG = False
FLASK_ENV = "production"
# SESSION_TYPE = "sqlalchemy"
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

API_BASE = "https://accounts.spotify.com"
REDIRECT_URI = "https://spodivide.herokuapp.com/login"
# REDIRECT_URI = "https://spodivide.com/login"
# REDIRECT_URI = "http://127.0.0.1:5000/login"
# Make sure you add this to Redirect URIs in the setting of the
# application dashboard of spotify developer
