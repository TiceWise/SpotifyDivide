"""Web app for dividing spotify songs over different playlists."""

from flask import Flask, render_template, redirect, request, session, flash
from flask import url_for
from flask_session import Session
import spotipy
import os
import uuid
from functools import wraps
from datetime import timedelta
from config import ProductionConfig, DevelopmentConfig

app = Flask(__name__)

app.config.from_object("config.DevelopmentConfig")
Session(app)

# help from:
# https://stackoverflow.com/questions/57580411/...
# ...storing-spotify-token-in-flask-session-using-spotipy
# https://www.digitalocean.com/community/tutorials/...
# ...how-to-make-a-web-application-using-flask-in-python-3


# TODO: create account system + database to store selected target playlists...
# Without login" we need to store some info on client side; uuid, and
# preferably selected playlists. But we need the server session to transfer
# the loaded data between the divide renders/button presses...
# TODO: use flask 'g' for track info, and session for the rest?

# class CacheXHandler:
#     """
#     Modified version for handling the caching and retrieval of authorization tokens.

#     Based on abstraction CacheHandler() in cache_handler.py of spotipy.
#     Handles reading and writing Spotify authorization tokens
#     """

#     def get_cached_token(self):
#         """Get and return a token_info dictionary object."""
#         # return token_info
#         raise NotImplementedError()

#     def save_token_to_cache(self, token_info):
#         """Save a token_info dictionary object to the cache and return None."""
#         raise NotImplementedError()
#         return None


caches_folder = "./.spotify_caches/"
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)


def session_cache_path():
    """Create a cache for the current user."""
    return caches_folder + session.get("uuid")


@app.before_request
def make_session_permanent():
    """Set session lifetime before each request."""
    session.permanent = True
    app.permanent_session_lifetime = timedelta(hours=1)


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


def get_spotify():
    """
    Return the spotipy.Spotify for the current logged in user.

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


@app.route("/")
def index():
    """
    Check if user is logged in. If not, redirect to log in.

    If so, redirect to select source page.
    """
    if not session.get("uuid") or not session.get("spotify_logged_in"):
        return redirect(url_for("login"))

    return redirect(url_for("select_source"))


@app.route("/login")
def login():
    """
    Log user in to Spotify; create a token (reuse with cache_handler).

    https://github.com/plamere/spotipy/blob/master/examples/app.py
    """
    if not session.get("uuid"):
        # Step 1. Visitor is unknown, give random ID
        session["uuid"] = str(uuid.uuid4())
        # initialize some settings for the divide page
        session["action_playlist_ids"] = []
        session["radio_action"] = "radio_move"
        session["select_all"] = None

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
    """Log the user out by deleting the cache file and clearing the session."""
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
    # TODO: user input field for spotify uri?

    # get the spotify thingy
    spotify = get_spotify()

    # if the user clicked on a playlist, go to next step
    if request.method == "POST":
        session["source_playlist"] = request.form.get("playlist_btn")
        return redirect(url_for("select_target"))
    # the user landed on the page... so get playlists from spotify
    else:
        pl = spotify.current_user_playlists()
        playlists = pl["items"]

        # loop till we get all playlists...
        while pl["next"]:
            pl = spotify.next(pl)
            playlists.extend(pl["items"])

        # TODO: fixed images somewhat quick and dirty in the html templates:
        # I wanted to get the smallest images to safe bandwidth and memory
        # so set het image index to -1; the last spotify image index.

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
    # TODO: user input field for spotify uri's + parse?

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
        return render_template("select_target.html", playlists=playlists)


@app.route("/divide", methods=["GET", "POST"])
@login_required
def divide():
    """TODO..."""
    # get the spotify thingy
    spotify = get_spotify()

    # if the user clicked on a confirm, go to next step
    if request.method == "POST":
        # Then...
        # - load from session in the post stream
        # current_user_saved_tracks_delete(track_id)
        # user_playlist_add_tracks(user, playlist_id, tracks)

        # action playlists.. is very similar to target playlists
        action_playlist_ids = request.form.getlist("action_playlist_ids")
        session["action_playlist_ids"] = action_playlist_ids
        # action; move, copy or remove -
        # name of button; radio_move, radio_copy or radio_remove
        radio_action = request.form["radio_action"]
        session["radio_action"] = radio_action
        # is select_all checked? is 'on' or None (this is just to set the same state)
        select_all = request.form.get("select_all")
        session["select_all"] = select_all
        # previous or next butoon clicked? returns button name (btn_prev or btn_next)
        btn_clicked = request.form["btn_clicked"]

        if (btn_clicked == "btn_next_no_action") or (
            btn_clicked == "btn_prev_no_action"
        ):
            session["track_counter"] = update_count(btn_clicked)
            return render_divide()

        if (btn_clicked != "btn_next") and (btn_clicked != "btn_prev"):
            flash("Something went wrong... (unexpected POST method/button click)")
            return redirect(url_for("divide"))

        # on empty playlist and 'move' return alert (please use delete), do not change
        # song number
        if not action_playlist_ids and radio_action == "radio_move":
            flash(
                "No action taken as you've selected 'Move', but without a "
                "target playlist."
            )
            session["track_counter"] = update_count(btn_clicked)
            return render_divide()

        # on empty playlist and 'copy' return alert (no playlist selected). do change
        # song number
        if not action_playlist_ids and radio_action == "radio_copy":
            flash(
                "No action taken as you've selected 'Copy', but without a "
                "target playlist."
            )
            session["track_counter"] = update_count(btn_clicked)
            return render_divide()
            # we're not removing songs, so always one (this) song remains,
            # so no need to check for -1

        # If we do have a target playlist selected, and we're on the remove, that's
        # probably a mistake to, as nothing will be done with the target playlist
        # let's warn the user and do nothing
        if action_playlist_ids and radio_action == "radio_remove":
            flash(
                "No action taken as you've selected 'Remove', but you also have a "
                "target playlist selected. Deselect all playlist to remove, or "
                "select the 'Copy' or 'Move' action."
            )
            return render_divide()

        track_data = session.get("tracks")[session.get("track_counter")]["track"]

        # add song to target playlists (move and copy)
        if radio_action == "radio_move" or radio_action == "radio_copy":
            for action_playlist in action_playlist_ids:
                spotify.playlist_add_items(action_playlist, [track_data["uri"]])
            # for move, the update count is updated in the next loop
            if radio_action == "radio_copy":
                session["track_counter"] = update_count(btn_clicked)
                # we're not removing songs, so always one (this) song remains,
                # so no need to check for -1

        # delete song from source playlist + delete from sessiontracks (move and delete)
        if radio_action == "radio_move" or radio_action == "radio_remove":
            # delete from playlist...
            # ...case liked songs
            if session.get("source_playlist") == "liked_songs":
                spotify.current_user_saved_tracks_delete([track_data["id"]])
            # ...case playlist
            else:
                # TODO: double check if user is owner? Tho 'Copy' should be
                # only option in that case, and this will just return an error
                # so not destructive..
                spotify.playlist_remove_specific_occurrences_of_items(
                    playlist_id=session.get("source_playlist"),
                    items=[
                        {
                            "uri": track_data["id"],
                            "positions": [session.get("track_counter")],
                        }
                    ],
                )
            # delete from sessiontracks (move and delete)
            tracks = session.get("tracks")
            this_track = tracks[session.get("track_counter")]
            tracks.remove(this_track)
            session["tracks"] = tracks
            # as we delete a track.. the next song automatically comes in the place
            # of the track counter, but... it might be a non-track type.. so let's
            # update count handle that...; set to -1, and pass to update count.
            # This will also handle the edge case that we're at the last track...
            # However, if we're going in the other direction, we need the original
            # action.
            if btn_clicked == "btn_next":
                session["track_counter"] -= 1
                session["track_counter"] = update_count(btn_clicked)
            if btn_clicked == "btn_prev":
                session["track_counter"] = update_count(btn_clicked)

            if session.get("track_counter") == -1:
                flash(
                    "No (more) tracks in source playlist, "
                    "select another source playlist."
                )
                return redirect(url_for("select_source"))

        # return all the selected stuff as before to the render (via session)!
        return render_divide()

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
            # possibly 'playlist_items', we can also move podcasts, quite difficult tho.

        if len(tr["items"]) == 0:
            flash("Source playlist is empty, select another source playlist.")
            return redirect(url_for("select_source"))

        tracks = tr["items"]
        while tr["next"]:
            tr = spotify.next(tr)
            tracks.extend(tr["items"])

        # remove non-track items
        skip_count = 0
        for track in reversed(tracks):
            if track["track"]["type"] != "track":
                track["skip"] = True
                skip_count += 1
            else:
                track["skip"] = False

        if len(tr["items"]) == skip_count:
            flash(
                "Source playlist only contains non-track items (Podcasts), "
                "select another playlist."
            )
            return redirect(url_for("select_source"))

        # check if user is owner of source playlist, if not owner (or collab etc.),
        # do not show move or delete options; only copy. # liked songs is definetly
        # ours, so no problems there
        user = spotify.me()
        session["move_remove_enabled"] = True
        if source_playlist != "liked_songs":
            playlist = spotify.playlist(source_playlist)
            if playlist["owner"]["id"] != user["id"] or playlist["collaborative"]:
                session["move_remove_enabled"] = False
                flash(
                    "Only the 'copy' action is available, as you do not own the "
                    "source playlist (or it's a collaborative playlist), so we "
                    "can't remove items from the source playlist."
                )

        # check the target playlists
        if not session.get("target_playlist_ids"):
            flash(
                "No target playlist selected, "
                "please select target playlists in step 2."
            )
            return redirect(url_for("select_target"))

        # TODO... check if we own the target playlists?... Should be the only
        # selectable options tho based on previous settings

        target_playlist_ids = session.get("target_playlist_ids")

        # reading each playlist from the spotify api takes about 0.1 per playlist
        # so if many playlists are selected this can take a long time, all my playlists
        # resulted in about 15 seconds!... the target loading of step 2 takes 0.8 - 2.2
        # seconds so... let's use that method (and pop) if we have more than x
        # playlists...
        # After timing both option multiple times, i measured that loading all playlists
        # and popping was faster as of the length of 7 playlists.

        if len(target_playlist_ids) < 7:
            target_playlists = []
            for target_playlist_id in target_playlist_ids:
                target_playlists.append(spotify.playlist(target_playlist_id))

        else:
            pl = spotify.current_user_playlists()
            target_playlists = pl["items"]

            # loop till we get all playlists...
            while pl["next"]:
                pl = spotify.next(pl)
                target_playlists.extend(pl["items"])

            for playlist in reversed(target_playlists):
                # remove not-owned and collaborative playlists
                if playlist["id"] not in target_playlist_ids:
                    target_playlists.remove(playlist)

        # STORE DATA IN SESSION: (note that this is only done in GET, when
        # the page is loaded.)
        # - playlists just the name and id's? TODO: Store that info earlier
        #       with the target selection where we still have it?)
        # - tracklist
        # - iteration number [initialize in GET to 0]
        session["target_playlists"] = target_playlists
        session["tracks"] = tracks

        # do not start at a 'skip' track
        track_counter = 0

        while tracks[track_counter]["skip"]:
            track_counter += 1

        session["track_counter"] = track_counter

        # render the divide page
        return render_divide()


# TODO: bug report button?
# TODO: buy me a beer button?
# TODO: add google ads?


def update_count(btn_clicked):
    """
    Update the track counter; at which track are we in the track list.

    Returns the updated counter; the integer where we are.
    """
    number_of_tracks = len(session.get("tracks"))
    track_counter = session.get("track_counter")
    tracks = session.get("tracks")

    # iter counter to break infinite loop (e.g. only non-track tracks (all skip))
    iter_count = 0

    # do while emulation, for skipping non-track songs
    condition = True
    while condition:
        if btn_clicked == "btn_next" or btn_clicked == "btn_next_no_action":
            if track_counter + 1 >= number_of_tracks:
                track_counter = 0
            else:
                track_counter += 1
        elif btn_clicked == "btn_prev" or btn_clicked == "btn_prev_no_action":
            if track_counter - 1 < 0:
                track_counter = number_of_tracks - 1
            else:
                track_counter -= 1
        # infinite loop if we delete all non-skip tracks
        # use counter and number of tracks
        iter_count += 1
        if iter_count >= number_of_tracks:
            track_counter = -1
            break
        else:
            # update condition for while loop, to do the next iteration, until
            # we find a song that has skip = false
            condition = tracks[track_counter]["skip"]

    return track_counter


def render_divide():
    """Render the divide page. Gets info from session. Return html code."""
    # Get the track information from the current track
    track = session.get("tracks")[session.get("track_counter")]["track"]
    # date_added = session.get(
    #   "tracks")[session.get("track_counter")]["added_at"]
    # added_by = date_added = session.get(
    #   "tracks")[session.get("track_counter")]["added_by"]

    # specifically to retreive label info...
    spotify = get_spotify()
    albuminfo = spotify.album(track["album"]["id"])

    genres = []
    for artist in track["artists"]:
        genres.extend(spotify.artist(artist["id"])["genres"])

    # set up page as it was (initialize, action, select all, action lists)
    # the action button and select_all check box are in the session already

    for playlist in session.get("target_playlists"):
        if playlist["id"] in session.get("action_playlist_ids"):
            playlist["checked"] = True
        else:
            playlist["checked"] = False

    # TODO: uri/link for track, album and artist (once hoveredd over)?
    #   needs seperate artists.. but can be achieved with jinja for loop
    # TODO: add hover over info on how to enable autoplay
    # TODO: add hover over info on valence etc.
    # TODO: Added to playlist info?...

    track_features = spotify.audio_features(track["id"])
    key = track_features[0]["key"]
    mode = track_features[0]["mode"]

    # tic = time.perf_counter()
    # track_analysis = spotify.audio_analysis(track["id"])
    # toc = time.perf_counter()
    # print(toc - tic)
    # print(
    #     "key: "
    #     + str(key)
    #     + " (conf: "
    #     + str(track_analysis["track"]["key_confidence"])
    #     + "), mode: "
    #     + str(mode)
    #     + " (conf: "
    #     + str(track_analysis["track"]["mode_confidence"])
    #     + ")"
    # )

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
        act_playlists=session.get("target_playlists"),
        title=track["name"],
        album=track["album"]["name"],
        album_type=track["album"]["album_type"],
        track_type=track["type"],
        image_url=track["album"]["images"][0]["url"],
        artist_str=", ".join([artist["name"] for artist in track["artists"]]),
        # preview_url=track["preview_url"],
        uri=track["uri"],
        label=albuminfo["label"],
        release_date=track["album"]["release_date"],
        duration_str=time_string(int(track["duration_ms"])),
        genres_str=", ".join(genres),
        bpm=track_features[0]["tempo"],
        key_tone=get_key(key, mode, key_type="tonal"),
        key_cam=get_key(key, mode, key_type="camelot"),
        feature_list=feature_list,
        move_remove_enabled=session.get("move_remove_enabled"),
        radio_action=session.get("radio_action"),
        select_all=session.get("select_all"),
    )


def time_string(dur):
    """
    Transform time in ms to nice text.

    ## m ## s or ## h ## m
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
    Transform the spotify key into something understandable key_type options.

    Key_type options: camelot, tonal, or both
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
    # app.run(debug=True)
    app.run()
