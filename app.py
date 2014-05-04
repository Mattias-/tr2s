from flask import Flask, session, redirect, url_for, render_template, jsonify
from flask_oauth import OAuth
import os
import tr2s
import requests

def main(args):
    app.secret_key = args[1]
    strava.consumer_key = args[2]
    strava.consumer_secret = args[3]
    app.run(host='0.0.0.0', debug=True)


app = Flask(__name__)
oauth = OAuth()
strava = oauth.remote_app('strava',
                  base_url='https://www.strava.com/api/v3/',
                  request_token_url=None,
                  access_token_url='https://www.strava.com/oauth/token',
                  access_token_method='POST',
                  authorize_url='https://www.strava.com/oauth/authorize',
                  consumer_key='',
                  consumer_secret='',
                  request_token_params={'response_type':'code',
                                        'scope':'view_private,write'})


@app.route('/')
def index():
    strava_token = get_strava_token()
    log = None
    strava_authed = False
    strava_athlete = None
    tr_authed = False
    tr_id = None
    ride_list = []

    tr_username = session.get('tr_username', None)
    if tr_username:
        tr_id = tr2s.get_id_from_username(tr_username)
        tr_authed = (tr_id is not None)

    if strava_token:
        athlete = strava.request('athlete', data={'access_token':strava_token})
        if athlete.status == 200:
            strava_authed = True
            strava_athlete = athlete.data
            log = strava_athlete

    if tr_authed and strava_authed:
        tr_rides = tr2s.get_tr_rides(tr_id)
        for ride in tr_rides:
            d = {'tr_name': ride['WorkoutName'],
                 'start_date': ride['WorkoutDate'],
                 'tr_id': ride['Id'],
                 'uploaded_to_strava': False}
            ride_list.append(d)
        payload = {'access_token': strava_token,
                   'per_page': 30  #TODO arbitrary number, be smart?
                  }
        r = strava.request('athlete/activities', data=payload)
        if r.status == 200:
            strava_authed = True
            strava_rides = r.data
            for strava_ride in strava_rides:
                for ride in ride_list:
                    # Compare with stripped trailing Z in strava timestamp
                    if ride['start_date'] == strava_ride['start_date_local'][:-1]:
                        ride['uploaded_to_strava'] = True
                        ride['start_date_utc'] = strava_ride['start_date']
                        ride['strava_name'] = strava_ride['name']
                        ride['strava_id'] = strava_ride['id']
                        ride['strava_file'] = strava_ride['external_id']

    return render_template('app.html', strava_authed=strava_authed,
                           strava_athlete=strava_athlete, ride_list=ride_list,
                           log=log, tr_member_id=tr_id, tr_username=tr_username,
                           tr_authed=tr_authed)

@app.route('/set_tr/<username>')
def set_tr(username):
    tr_id = tr2s.get_id_from_username(username)
    res = {'username': username,
            'result': False}
    if tr_id is not None:
        session['tr_username'] = username
        res['result'] = True
    return jsonify(**res)

@app.route('/upload/<member_id>/<ride_id>')
def upload(member_id, ride_id):
    ride = tr2s.find_ride_of_member_id(member_id, ride_id)
    name = ride['WorkoutName']
    filename = tr2s.download_tr_ride(ride)
    file_content = open(filename).read()
    payload = {'access_token': get_strava_token()[0],
               'activity_type': 'ride',
               'data_type': 'tcx',
               'private': 1,
               'name': name,
               'stationary': 1,
               'external_id': filename}
    url = strava.base_url + 'uploads'
    r = requests.post(url, data=payload, files={'file': open(filename, 'rb')})
    os.remove(filename)
    print r
    return r.text


@strava.tokengetter
def get_strava_token(token=None):
    return session.get('strava_token')

@app.route('/login')
def login():
    app_url = 'http://precise2:5000'
    callback_url = app_url + url_for('oauth_authorized')
    return strava.authorize(callback=callback_url)

@app.route('/oauth-authorized')
@strava.authorized_handler
def oauth_authorized(resp):
    session['strava_token'] = (resp['access_token'], '')
    return redirect(url_for('index'))

if __name__ == '__main__':
    import sys
    main(sys.argv)

