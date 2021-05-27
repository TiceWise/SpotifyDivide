from flask import Flask, render_template, redirect, request, session, flash
from flask import url_for
from flask_session import Session
import spotipy
import os
import uuid
from functools import wraps
from datetime import timedelta

import time

app = Flask(__name__)
app.config.from_pyfile("config.py")
Session(app)
# app.secret_key = app.config["SECRET_SESSION_KEY"]

# help from:
# https://stackoverflow.com/questions/57580411/...
# ...storing-spotify-token-in-flask-session-using-spotipy
# https://www.digitalocean.com/community/tutorials/...
# ...how-to-make-a-web-application-using-flask-in-python-3

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
        # Then...
        # - load from session in the post stream
        return "TODO"
    # the user landed on the page... so get playlists from spotify
    else:
        # check the source playlist
        source_playlist = session.get("source_playlist")
        if not source_playlist:
            flash("No source playlist selected, select a source playlist in step 1.")
            return redirect(url_for("select_source"))

        if source_playlist == "liked_songs":
            tr = spotify.current_user_saved_tracks()
        else:
            tr = spotify.playlist_tracks(playlist_id=source_playlist)
            # TODO: possibly 'playlist_items', we can also move podcasts

        if len(tr["items"]) == 0:
            flash("Source playlist is empty, select another source playlist.")
            return redirect(url_for("select_source"))

        tracks = tr["items"]
        while tr["next"]:
            tr = spotify.next(tr)
            tracks.extend(tr["items"])

        # remove non-track items
        for track in reversed(tracks):
            if track["track"]["type"] != "track":
                tracks.remove(track)

        # print(len(tracks))
        if len(tr["items"]) == 0:
            flash(
                "Source playlist only contains non-track items (Podcasts), "
                "select another playlist."
            )
            return redirect(url_for("select_source"))

        # check the target playlists
        if not session.get("target_playlist_ids"):
            flash(
                "No target playlist selected, "
                "please select target playlists in step 2."
            )
            return redirect(url_for("select_target"))

        # TODO... check if we own the target playlists?... Should be the only
        # selectable options tho...

        target_playlist_ids = session.get("target_playlist_ids")

        target_playlists = []
        for target_playlist_id in target_playlist_ids:
            target_playlists.append(spotify.playlist(target_playlist_id))

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

        # STORE DATA IN SESSION: (note that this is only done in GET, when
        # the page is loaded.)
        # - playlists just the name and id's? TODO: Store that info earlier
        #       with the target selection where we still have it?)
        # - tracklist
        # - iteration number [initialize in GET to 0]
        session["target_playlists"] = target_playlists
        session["tracks"] = tracks
        session["track_counter"] = 0

        # Also...
        # - use the same way to 'render?', or is it rel. short code already?..
        # - we need next, previous, Move and next, and move and prev - buttons
        # - these button change to copy if 'delete from playlist' isn't
        #   selected?

        return render_divide()


def render_divide():
    track = session.get("tracks")[session.get("track_counter")]["track"]
    # date_added = session.get("tracks")[
    # session.get("track_counter")]["added_at"]
    # added_by = date_added = session.get("tracks")[
    # session.get("track_counter")]["added_by"]

    # specifically to retreive label info...
    spotify = get_spotify()
    albuminfo = spotify.album(track["album"]["id"])

    genres = []
    for artist in track["artists"]:
        genres.extend(spotify.artist(artist["id"])["genres"])

    # genre

    # TODO: uri/link for track, album and artist (once hoveredd over)?
    #   needs seperate artists.. but can be achieved with jinja for loop
    # TODO: add info on how to enable autoplay

    # TODO: song analysis info
    # TODO: Added to playlist info?...

    track_features = spotify.audio_features(track["id"])
    key = track_features[0]["key"]
    mode = key = track_features[0]["mode"]

    feature_strings = [
        "energy",
        "danceability",
        "valence",
        "speechiness",
        "acousticness",
        "instrumentalness",
        "liveness",
    ]

    bar_colors = [
        "#4000F5",
        "#CDF563",
        "#CB1381",
        "#9CF0E1",
        "#EF891C",
        "#EC5541",
        "#CC200E",
        "#721107",
    ]

    feature_list = []
    popularity_data = {
        "name": "Popularity",
        "value": track["popularity"],
        "color": bar_colors[0],
        # "color": "#CCF462",
    }
    feature_list.append(popularity_data)

    for i, feature in enumerate(feature_strings, start=1):
        data = {
            "name": feature.title()[:12],
            "value": round(float(track_features[0][feature]) * 100),
            "color": bar_colors[i],
        }
        feature_list.append(data)

    # uri = "https://embed.spotify.com/?uri=" + track["uri"]
    return render_template(
        "divide.html",
        playlists=session["target_playlists"],
        title=track["name"],
        album=track["album"]["name"],
        album_type=track["album"]["album_type"],
        track_type=track["type"],
        image_url=track["album"]["images"][0]["url"],
        artist_str=", ".join([artist["name"] for artist in track["artists"]]),
        preview_url=track["preview_url"],
        label=albuminfo["label"],
        release_date=track["album"]["release_date"],
        duration_str=time_string(int(track["duration_ms"])),
        genres_str=", ".join(genres),
        bpm=track_features[0]["tempo"],
        key_tone=get_key(key, mode, key_type="tonal"),
        key_cam=get_key(key, mode, key_type="camelot"),
        feature_list=feature_list,
    )


def time_string(dur):
    """
    transform time in ms to nice text:
    ## m ## s
    # or
    ## h ## m
    """
    dur = dur / 1000
    seconds = dur % 60
    seconds = int(seconds)
    minutes = (dur / 60) % 60
    minutes = int(minutes)
    hours = (dur / 60) / 60 % 60
    hours = int(hours)

    if hours == 0:
        return "%2d min %2d sec" % (minutes, seconds)
    elif hours > 0:
        return "%2d hr %2d min" % (hours, minutes)


def get_key(key, mode, key_type="camelot"):
    """
    transform the spotify key into something understandable
    key_type options: camelot, tonal, or both
    """

    if key == 0:
        key_str_cam = "8"
        key_str_ton = "C"
    elif key == 1:
        key_str_cam = "3"
        key_str_ton = "C#"
    elif key == 2:
        key_str_cam = "10"
        key_str_ton = "D"
    elif key == 3:
        key_str_cam = "5"
        key_str_ton = "D#"
    elif key == 4:
        key_str_cam = "12"
        key_str_ton = "E"
    elif key == 5:
        key_str_cam = "7"
        key_str_ton = "F"
    elif key == 6:
        key_str_cam = "2"
        key_str_ton = "F#"
    elif key == 7:
        key_str_cam = "9"
        key_str_ton = "G"
    elif key == 8:
        key_str_cam = "4"
        key_str_ton = "G#"
    elif key == 9:
        key_str_cam = "11"
        key_str_ton = "A"
    elif key == 10:
        key_str_cam = "6"
        key_str_ton = "A#"
    elif key == 11:
        key_str_cam = "1"
        key_str_ton = "B"
    else:
        key_str_cam = "n/a"
        key_str_ton = "n/a"

    # major and minor additions
    if mode == 1:
        mode_str_cam = "B"  # major
        mode_str_ton = ""  # major
    elif mode == 0:
        mode_str_cam = "A"  # minor
        mode_str_ton = "m"  # major
    else:
        mode_str_cam = "n/a"  # minor
        mode_str_ton = "n/a"  # major

    if key_type == "camelot":
        return key_str_cam + mode_str_cam
    elif key_type == "tonal":
        return key_str_ton + mode_str_ton
    elif key_type == "both":
        return key_str_cam + mode_str_cam + " - " + key_str_ton + mode_str_ton
    else:
        return ""


if __name__ == "__main__":
    app.run(debug=True)
