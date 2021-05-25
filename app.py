from flask import Flask, render_template, redirect, request, session, flash
from flask import url_for
import spotipy
import os
import uuid
from functools import wraps

app = Flask(__name__)
app.config.from_pyfile("config.py")
app.secret_key = app.config["SECRET_SESSION_KEY"]

# help from:
# https://stackoverflow.com/questions/57580411/storing-spotify-token-in-flask-session-using-spotipy
# https://www.digitalocean.com/community/tutorials/how-to-make-a-web-application-using-flask-in-python-3

# create a cache folder in general
caches_folder = "./.spotify_caches/"
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)


def session_cache_path():
    """
    Create a cache for the current user.
    """

    return caches_folder + session.get("uuid")


def get_spotify():
    """
    Returns the spotipy.Spotify for the current logged in user.
    User must be logged in to Spotify previously.
    """

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

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect("/")

    return spotipy.Spotify(auth_manager=auth_manager)


def login_required(f):
    """
    Decorate routes to require login.
    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("uuid") or not session.get("spotify_logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def index():
    """
    The basic route. Checks if user is logged in. If not, redirect to log in.
    If so, redirect to select source page.
    """

    if not session.get("uuid") or not session.get("spotify_logged_in"):
        return redirect(url_for("login"))

    return redirect(url_for("select_source"))


@app.route("/login")
def login():
    """
    Log user in to Spotify; create a token which we reuse using the
    cache_handler.
    https://github.com/plamere/spotipy/blob/master/examples/app.py
    """

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
    spotify = spotipy.Spotify(auth_manager=auth_manager)

    user = spotify.me()
    username = user["display_name"]

    session["spotify_logged_in"] = True

    flash(f"Logged in to Spotify as {username}")

    return redirect("/")


@app.route("/logout")
def logout():
    """
    Log the user out by deleting the cache file and clearing the session.
    """
    try:
        # TODO: make this a bit smarter such that we can store the source-
        # and target playlists
        # Remove the CACHE file (.cache-test) so that a new user can authorize.
        os.remove(session_cache_path())
        session.clear()
    except OSError as e:
        print("Error: %s - %s." % (e.filename, e.strerror))
    return redirect("/")


@app.route("/select_source", methods=["GET", "POST"])
@login_required
def select_source():
    """
    Select the 'source' playlist from which we divide the songs.
    We do so by getting all the users playlists from Spotify and
    letting the user click one.
    """
    # get the spotify thingy
    spotify = get_spotify()

    # if the user clicked on a playlist, go to next step
    if request.method == "POST":
        session["source_playlist"] = request.form.get("playlist_btn")
        print(session.get("source_playlist"))
        return redirect(url_for("select_target"))
    # the user landed on the page... so get playlists from spotify
    else:
        pl = spotify.current_user_playlists()
        playlists = pl["items"]

        # loop till we get all playlists...
        while pl["next"]:
            pl = spotify.next(pl)
            playlists.extend(pl["items"])

        # return template with the playlists
        return render_template("select_source.html", playlists=playlists)


@app.route("/select_target", methods=["GET", "POST"])
@login_required
def select_target():
    """
    Select the 'target' playlists to which we add the songs.
    We do so by getting all the users playlists from Spotify and
    letting the user select multiple.
    We only display the playlists that the user can edit (must be
    owned by the user and not collaborative))
    """
    # get the spotify thingy
    spotify = get_spotify()

    # if the user clicked on a confirm, go to next step
    if request.method == "POST":
        session["target_playlists"] = request.form.getlist("target_playlists")

        if not session.get("target_playlists"):
            flash("No target playlist selected, "
                  "please select a target playlist and confirm.")
            return redirect(url_for('select_target'))
        else:
            return "TODO"
    # the user landed on the page... so get playlists from spotify
    else:
        pl = spotify.current_user_playlists()
        playlists = pl["items"]

        # loop till we get all playlists...
        while pl["next"]:
            pl = spotify.next(pl)
            playlists.extend(pl["items"])

        # if we've made a selection before, let's pre-check those items
        target_playlists = session.get("target_playlists")

        # We only display the playlists that the user can edit: must be owned
        # by the user and not collaborative
        # (https://stackoverflow.com/questions/38885575/
        # spotify-web-api-how-to-find-playlists-the-user-can-edit)

        user = spotify.me()
        for playlist in reversed(playlists):
            # remove not-owned and collaborative playlists
            if playlist["owner"]["id"] != user["id"] or playlist["collaborative"]:
                playlists.remove(playlist)
            else:
                # if we've made a selection before, let's pre-check those items
                if target_playlists:
                    if playlist['id'] in target_playlists:
                        playlist['checked'] = True
                    else:
                        playlist['checked'] = False

        # return template with the playlists

        return render_template("select_target.html", playlists=playlists)


if __name__ == "__main__":
    app.run(debug=True)
