from flask import Flask, render_template, redirect, request, session, make_response,session,redirect
import spotipy
import spotipy.util as util
import time
import json

app = Flask(__name__)
app.config.from_pyfile('config.py')
app.secret_key = app.config['SECRET_SESSION_KEY']
# help from:
# https://stackoverflow.com/questions/57580411/storing-spotify-token-in-flask-session-using-spotipy
# https://medium.com/analytics-vidhya/discoverdaily-a-flask-web-application-built-with-the-spotify-api-and-deployed-on-google-cloud-6c046e6e731b


@app.route('/')
def verify():
    # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
    sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id = app.config['CLIENT_ID'],
                                           client_secret = app.config['CLIENT_SECRET'],
                                           redirect_uri = app.config['REDIRECT_URI'],
                                           scope = app.config['SCOPE'])
    auth_url = sp_oauth.get_authorize_url()
    print(auth_url)
    return redirect(auth_url)


# authorization-code-flow Step 2.
# Have your application request refresh and access tokens;
# Spotify returns access and refresh tokens
@app.route("/api_callback")
def api_callback():
    # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
    sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id = app.config['CLIENT_ID'],
                                           client_secret = app.config['CLIENT_SECRET'],
                                           redirect_uri = app.config['REDIRECT_URI'],
                                           scope = app.config['SCOPE'])
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)

    # Saving the access token along with all other token related info
    session["token_info"] = token_info

    return redirect("index")

# authorization-code-flow Step 3.
# Use the access token to access the Spotify Web API;
# Spotify returns requested data
@app.route("/go", methods=['POST'])
def go():
    session['token_info'], authorized = get_token(session)
    session.modified = True
    if not authorized:
        return redirect('/')
    data = request.form
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    response = sp.current_user_top_tracks(limit=data['num_tracks'], time_range=data['time_range'])

    # print(json.dumps(response))

    return render_template("results.html", data=data)

# Checks to see if token is valid and gets a new token if not
def get_token(session):
    token_valid = False
    token_info = session.get("token_info", {})

    # Checking if the session already has a token stored
    if not (session.get('token_info', False)):
        token_valid = False
        return token_info, token_valid

    # Checking if token has expired
    now = int(time.time())
    is_token_expired = session.get('token_info').get('expires_at') - now < 60

    # Refreshing token if it has expired
    if (is_token_expired):
        # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
        sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id = CLI_ID, client_secret = CLI_SEC, redirect_uri = REDIRECT_URI, scope = SCOPE)
        token_info = sp_oauth.refresh_access_token(session.get('token_info').get('refresh_token'))

    token_valid = True
    return token_info, token_valid

if __name__ == "__main__":
    app.run(debug=True)