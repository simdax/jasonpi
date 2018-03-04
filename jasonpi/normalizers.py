import datetime


def google_profile(data):
    print(data)
    profile = {
        'email': data['emailAddresses'][0]['value'],
        'first_name': data['names'][0]['givenName'],
        'last_name': data['names'][0]['familyName'],
        'gender': data['genders'][0]['value'],
    }
    if 'birthdays' in data and len(data['birthdays']) > 0:
        bd = data['birthdays'][0]['date']
        profile['birthday'] = datetime.date(bd['year'], bd['month'], bd['day'])
    return profile


def facebook_profile(data):
    profile = data.copy()
    print(profile)
    try:
        profile['birthday'] = \
            datetime.datetime.strptime(data['birthday'], "%m/%d/%Y").date()
    except ValueError:
        pass
    if 'picture' in data:
        if type(data['picture']) == dict:
            profile['picture'] = data['picture']['data']['url']
    return profile
