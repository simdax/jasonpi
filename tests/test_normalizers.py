import datetime

from jasonpi.normalizers import facebook_profile, google_profile


def test_facebook_profile():
    """
    Test that facebook_profile computes
    a correct profile received from facebook oauth.
    """
    data = {
        'email': 'some@email.com',
        'first_name': 'Alfred',
        'last_name': 'Dupont',
        'gender': 'male',
        'birthday': '02/25/1970'
    }
    profile = facebook_profile(data)
    assert profile['email'] == data['email']
    assert profile['first_name'] == data['first_name']
    assert profile['last_name'] == data['last_name']
    assert profile['gender'] == data['gender']
    assert profile['birthday'] == datetime.date(1970, 2, 25)


def test_google_profile():
    """
    Test that google_profile computes
    a correct profile received from google oauth.
    """
    data = {
        'emailAddresses': [{'value': 'some@email.com'}],
        'names': [{'givenName': 'Alfred', 'familyName': 'Dupont'}],
        'genders': [{'value': 'male'}],
        'birthdays': [{'date': {'year': 1970, 'month': 2, 'day': 25}}]
    }
    profile = google_profile(data)
    assert profile['email'] == data['emailAddresses'][0]['value']
    assert profile['first_name'] == data['names'][0]['givenName']
    assert profile['last_name'] == data['names'][0]['familyName']
    assert profile['gender'] == data['genders'][0]['value']
    assert profile['birthday'] == datetime.date(1970, 2, 25)
