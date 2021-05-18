from flask import Flask, render_template, redirect, request, session, make_response,session,redirect
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
def hello_world():
    session.clear()
    session['token'] = util.prompt_for_user_token("",
                                                 scope=app.config['SCOPE'],
                                                 client_id=app.config['CLIENT_ID'],
                                                 client_secret=app.config['CLIENT_SECRET'],
                                                 redirect_uri="http://127.0.0.1:5000/index")
    return redirect("/index")


@app.route('/authorize')
def authorize():
    client_id = app.config['CLIENT_ID']
    redirect_uri = app.config['REDIRECT_URI']
    scope = app.config['SCOPE']
    state_key = createStateKey(15)
    session['state_key'] = state_key

    authorize_url = 'https://accounts.spotify.com/en/authorize?'
    params = {'response_type': 'code', 'client_id': client_id,
            'redirect_uri': redirect_uri, 'scope': scope,
            'state': state_key}
    query_params = urlencode(params)
    response = make_response(redirect(authorize_url + query_params))
    return response