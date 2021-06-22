# Divide for Spotify
#### Video Demo:  https://youtu.be/XSvWu-vbwC4
#### Description:
Divide your Spotify Liked Songs over your playlists.
1. Select your Liked Songs, or any other playlist from which you want to divide songs.
2. Select all playlists you might want to move the songs to.
3. Divide! Per song, determine to which playlists you want to move the song.

##### About

I save new music on Spotify by liking songs. I listen to Discover Weekly, Release Radar, and a number of other favourite playlists, and just heart everything i like.

I do have a lot of personal playlists too, for different genres and moods for example. It’s how I collect music. However, I never got around to divide my liked songs over these playlists. It was just too much hassle, dragging and dropping each song to multiple playlists, sometimes 100+ songs. In addition, I wanted more information on the songs, like genre and bpm.

That’s why I created Divide for Spotify.

The app is reviewed and accepted by the Spotify Developer Platform team.

##### More details on use
###### Step 1
Step 1 is pretty straight forward: Select the playlist from which you want to divide your songs. Often this will be your Liked Songs, but you can also select any other playlist from which you want to divide songs. For example Discover Weekly or Release Radar, or any other playlist that contains many songs you want to add to your own playlists.

###### Step 2
This is an extra step to make your life easier in step 3. If you have a lot of playlists (like me), you probably don't want to add songs to most of them. Step 2 is a pre-selection for playlists that are available in Step 3. Of course you're free to use all of your playlists with 'Select all'!

Note that your playlists are already filtered. For Divide for Spotify to be able to add songs to a playlist, the playlist must be created by you (you must be the owner) and playlist can't be a collaborative playlist.

Another use case of Divide for Spotify is creating a playlist for a special occasion: Create a playlist in Spotify, Select it as target, and just go through your Liked Songs; Add the songs you want to add for the occasion, and simply skip the others.

###### Step 3
From left to right, top to bottom, we see:

1. The album artwork with a preview option below,
2. information of the track,
    - 'Released on' indicates the label on which the song was released.
    - BPM means Beats Per Minutes.
    - The musical key between parenthesis is the Camelot Key.
3. audio features of the track,
    - See https://divideforspotify.com/more_info
4. confirmation and navigation buttons, (from left to right)
    - previous song,
    - previous song and confirm,
    - next song and confirm and
    - next song.
    - The buttons with confirm peform the action selected below on this song to the playlist(s) selected below.
    - The buttons without confirmation are used for navigation (next or previous song) without performing any action.
5. the action you want to perform (move, copy or remove)
    - Move adds the song to the selected playlist(s) and deletes the song from source playlist, or 'Unlikes' the song if the source playlist you selected in Step 1 is your Liked Songs.
    - Copy adds the song to the selected playlist(s) and doesn't remove the song from the source playlist.
    - Remove only deletes from source playlists without adding it to a playlist (for if you just don't like the song anymore).
    - Note that for the Copy and Remove action, you must be the owner of the source playlist and the source playlist can't be a collaborative playlists. In that case the Copy and Remove option are automatically hidden.
6. and the list to select the playlists to which you want to add the song.

##### Feedback
I hope you enjoy using Divide for Spotify. If anything is unclear or not working, please let me know. If you just want to say hi or thanks, that's no problem too! Any feedback is welcome. Send feedback via: https://divideforspotify.com/more_info

##### Privacy and data
Divide for Spotify doesn't store or use your personal data in any way. Only the data Divide for Spotify needs is requested and used (these are: your username, your playlists and your liked songs). Your information will never be sold or shared with Third Parties. No information is stored longer than one day after your session. Use the 'Log Out'-button in the top right to clear your data and to disconnect your account from Divide for Spotify immediately.

##### About the development
Description of what each file does:
- The static folder contains my .css file, the required images (like empty playlist and liked songs album artwork) and all the logo's I created.
- The templates folder contains all the .html templates which are rendered using flask (so jinja-html combination). Layout.html contains the lay-out which is loaded in the other template files.
- Procfile contains the settings for the Heroku dyno.
- app.py contains the entire python/flask model. Here also spotipy is used as interface for the Spotify API. Each function has comments with the explanation what it does.
- config.py sets the settings and variables for Flask and Spotipy. It contains two different settings, to easily switch from development to production. Some variables like log-in secrets are read from the environment.
- favicon.ico is a fall back option for the icon for older browsers.
- manifest.json ensures correct display, icon, and use as web app on Android.
- requirements.txt contains the required python packages. Also needed for the Heroku dyno to load and install those packages.

##### Design choices

First of all I decided to create it as a web app available for everybody, as an extra challenge. So everything had to be fool-proof and intuitive. 

Spotify just introduced an approval-flow for new public apps using the Spotify API. In a way it was a help to do everything according to their developer requirements. It was approved today! (After changing the name from SpoDivide to Divide for Spotify.)

For the look and feel (colors and such) I tried to follow Spotify as much as possible.

Step 2 is actually an extra step, at first it's not so clear what it does, but it is required for step 3, to make step 3 more workable. I think as soon as you are in step 3 and have clicked through everything once, you understand why it's there. Not sure how to make it more clear. The Steps and the way it all works is difficult to describe, but at the same time I think it how you use the app is actually really easy, so I want people to just start use it.

For the deployment I first tried Google Cloud Application, but it was less stable, probably because of me using a local file system for the sessions. The 'tracks' information require a local file system, as it is quite some 'unorganized' information. I need to store it, as otherwise it needs to be reloaded in step 3 between each song, which would make the page-loads quite long. That's why I decided to keep everything as file-system session, and just switch to heroku for now. That actually works quite well so far, let's see how it goes with more traffic.

Finally, I'm currently paying for a hobby dyno on heroku. Let's see how much interest and traffic I get. I might monetize the app with ads in the future.

That's it! I'm really happy with how professional it looks and feels, proud of the result! Thanks for reading.
