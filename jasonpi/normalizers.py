import datetime


def getGoogleProfile(user):
    profile = {
        'email': user['emailAddresses'][0]['value'],
        'first_name': user['names'][0]['givenName'],
        'last_name': user['names'][0]['familyName'],
        'gender': user['genders'][0]['value'],
    }
    if 'birthdays' in user and len(user['birthdays']) > 0:
        bd = user['birthdays'][0]['date']
        profile['birthday'] = datetime.date(bd['year'], bd['month'], bd['day'])
    return profile


def getFacebookProfile(user):
    profile = user.copy()
    try:
        profile['birthday'] = \
            datetime.datetime.strptime(user['birthday'], "%m/%d/%Y").date()
    except ValueError:
        pass
    return profile
