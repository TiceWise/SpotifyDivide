from flask import Flask, render_template, redirect, request, session, flash
import spotipy
import os
import uuid

app = Flask(__name__)
app.config.from_pyfile("config.py")
app.secret_key = app.config["SECRET_SESSION_KEY"]

# help from:
# https://stackoverflow.com/questions/57580411/storing-spotify-token-in-flask-session-using-spotipy
# https://medium.com/analytics-vidhya/discoverdaily-a-flask-web-application-built-with-the-spotify-api-and-deployed-on-google-cloud-6c046e6e731b
# https://www.digitalocean.com/community/tutorials/how-to-make-a-web-application-using-flask-in-python-3
# https://github.com/plamere/spotipy/blob/master/examples/app.py

caches_folder = "./.spotify_caches/"
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)


def session_cache_path():
    return caches_folder + session.get("uuid")


def check_log_in():
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        client_id=app.config["CLIENT_ID"],
        client_secret=app.config["CLIENT_SECRET"],
        redirect_uri=app.config["REDIRECT_URI"],
        scope=app.config["SCOPE"],
        cache_handler=cache_handler,
        show_dialog=True,
    )

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect("/")

    return spotipy.Spotify(auth_manager=auth_manager)


# authorization-code-flow Step 1. Have your application request authorization;
# the user logs in and authorizes access


@app.route("/")
def index():
    if not session.get("uuid"):
        # Step 1. Visitor is unknown, give random ID
        session["uuid"] = str(uuid.uuid4())

    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )

    # Don't reuse a SpotifyOAuth object because they store token info and you
    # could leak user tokens if you reuse a SpotifyOAuth object
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        client_id=app.config["CLIENT_ID"],
        client_secret=app.config["CLIENT_SECRET"],
        redirect_uri=app.config["REDIRECT_URI"],
        scope=app.config["SCOPE"],
        cache_handler=cache_handler,
        show_dialog=True,
    )

    if request.args.get("code"):
        # Step 3. Being redirected from Spotify auth page
        auth_manager.get_access_token(request.args.get("code"))
        return redirect("/")

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        # Step 2. Display sign in link when no token
        auth_url = auth_manager.get_authorize_url()

        return render_template("login.html", auth_url=auth_url)

    # Step 4. Signed in, display data
    session["login_success"] = True
    spotify = spotipy.Spotify(auth_manager=auth_manager)

    user = spotify.me()
    username = user["display_name"]

    flash(f"Logged in to Spotify as {username}")

    return redirect("/select_source")


@app.route("/select_source", methods=["GET", "POST"])
def select_source():
    # check if we are correctly logged in
    spotify = check_log_in()

    if request.method == "POST":
        print(request.form["playlist_id"])
        return request.form["playlist_id"]
    else:
        pl = spotify.current_user_playlists()
        # loop till we get all playlists...
        playlists = pl["items"]

        while pl["next"]:
            pl = spotify.next(pl)
            playlists.extend(pl["items"])

        # for playlist in playlists:
        #     print(playlist['name'])

        return render_template("select_source.html", playlists=playlists)


if __name__ == "__main__":
    app.run(debug=True)
