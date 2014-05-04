
import requests
import json
import re


def get_tr_rides(member_id=None):
    payload = {"IsDescending":True,
               "PageSize":30,
               "PageNumber":0,
               "TotalCount":1,
               "SortProperty":"Newest",
               "SearchText":None,
               "MinimumTicks":0,
               "MemberId":member_id,
               "WorkoutId": None,
               "TeamIds":None}

    r = requests.post('http://www.trainerroad.com/api/rides', data=payload)
    d = json.loads(r.text)
    rides = d['Rides']
    return rides

def find_ride_of_member_id(member_id, ride_id):
    rides = get_tr_rides(member_id=member_id)
    def id_is(i):
        def f(ride):
            return str(ride['Id']) == i
        return f
    match = filter(id_is(ride_id), rides)
    if len(match) == 1:
        return match[0]
    else:
        raise Exception

def get_id_from_username(username):
    r = requests.get('http://www.trainerroad.com/career/%s' % username)
    match = re.search('MemberId: ([0-9]*)', r.text)
    if not match:
        return None
    member_id = match.group(1)
    return member_id

def download_tr_ride(ride):
    url = 'http://www.trainerroad.com/cycling/rides/download/%s' % ride['Id']
    r = requests.get(url, stream=True)
    filename = r.headers['content-disposition'].split('=')[1]
    with open(filename, 'wb') as file:
        for block in r.iter_content(1024):
            if not block:
                break
            file.write(block)
        return filename
    raise Exception
