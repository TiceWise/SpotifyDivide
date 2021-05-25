from flask import Flask, render_template, redirect, request, session, flash
from flask import url_for
import spotipy
import os
import uuid
from functools import wraps
from datetime import timedelta

# import time

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


@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)


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
    # tic = time.perf_counter()

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

        # toc = time.perf_counter()
        # print(f"Select source total code time: {toc - tic:0.4f} seconds")

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
    # tic = time.perf_counter()

    # get the spotify thingy
    spotify = get_spotify()

    # if the user clicked on a confirm, go to next step
    if request.method == "POST":
        session["target_playlist_ids"] = request.form.getlist("target_playlist_ids")

        if not session.get("target_playlist_ids"):
            flash(
                "No target playlist selected, "
                "please select target playlists and confirm."
            )
            return redirect(url_for("select_target"))
        else:
            return redirect(url_for("divide"))
    # the user landed on the page... so get playlists from spotify
    else:
        pl = spotify.current_user_playlists()
        playlists = pl["items"]

        # loop till we get all playlists...
        while pl["next"]:
            pl = spotify.next(pl)
            playlists.extend(pl["items"])

        # if we've made a selection before, let's pre-check those items
        target_playlist_ids = session.get("target_playlist_ids")

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
                if target_playlist_ids:
                    if playlist["id"] in target_playlist_ids:
                        playlist["checked"] = True
                    else:
                        playlist["checked"] = False

        # return template with the playlists
        # toc = time.perf_counter()
        # print(f"Select target total code time: {toc - tic:0.4f} seconds")

        return render_template("select_target.html", playlists=playlists)


@app.route("/divide", methods=["GET", "POST"])
@login_required
def divide():
    """
    TODO...
    """

    # get the spotify thingy
    spotify = get_spotify()

    # if the user clicked on a confirm, go to next step
    if request.method == "POST":
        return "TODO"
    # the user landed on the page... so get playlists from spotify
    else:
        # check the source playlist
        source_playlist = session.get("source_playlist")
        if not source_playlist:
            flash("No source playlist selected, select a source playlist in step 1.")
            return redirect(url_for("select_target"))

        if source_playlist == "liked_songs":
            tr = spotify.current_user_saved_tracks()
        else:
            tr = spotify.playlist_tracks(playlist_id=source_playlist)
            # TODO: possibly 'playlist_items', we can also move podcasts

        if len(tr["items"]) == 0:
            flash("Playlist is empty, select an other source playlist.")
            return redirect(url_for("select_target"))

        tracks = tr["items"]
        while tr["next"]:
            tr = spotify.next(tr)
            tracks.extend(tr["items"])

        # print(len(tracks))

        # check the target playlists
        if not session.get("target_playlist_ids"):
            flash(
                "No target playlist selected, "
                "please select target playlists in step 2."
            )
            return redirect(url_for("select_target"))

        # TODO... check if we own the target playlists?...

        target_playlist_ids = session.get("target_playlist_ids")

        playlists = []
        for target_playlist_id in target_playlist_ids:
            playlists.append(spotify.playlist(target_playlist_id))

        # We only display the playlists that the user can edit: must be owned
        # by the user and not collaborative
        # (https://stackoverflow.com/questions/38885575/
        # spotify-web-api-how-to-find-playlists-the-user-can-edit)

        # audio_features(tracks=[])
        # current_user_saved_tracks_delete(track_id)
        # user_playlist_add_tracks(user, playlist_id, tracks)
        # Replace all tracks in a playlist

        # Parameters:
        # user - the id of the user
        # playlist_id - the id of the playlist
        # tracks - the list of track ids to add to the playlist

        # return template with the playlists

        """
        TODO: STORE DATA IN SESSION:
        - playlists (just the name and id's? Store that info earlier with
          the target selection where we still have it?)
        - tracklist
        - iteration number [initialize in GET to 0]

        Then...
        - load from session in the post stream

        Also...
        - use the same way to 'render?', or is it rel. short code already?..
        - we need next, previous, Move and next, and move and prev - buttons
        - these button change to copy if 'delete from playlist' isn't selected?
        """

        track = tracks[0]["track"]

        return render_template("divide.html", playlists=playlists, track=track)


if __name__ == "__main__":
    app.run(debug=True)
