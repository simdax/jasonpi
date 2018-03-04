import jwt
import datetime
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions, views

User = get_user_model()


def get_token(user):
    token = jwt.encode(
        {
            'exp': datetime.datetime.utcnow() +
            getattr(
                settings,
                'JASONPI_TOKEN_DURATION',
                datetime.timedelta(days=1),
            ),
            'user_id': user.id,
        },
        settings.SECRET_KEY,
        algorithm='HS256'
    )
    if type(token) == bytes:
        return token.decode('utf-8')
    else:
        return token


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = None
        authorization = request.META.get('HTTP_AUTHORIZATION', None)
        print('access_token' in request.COOKIES, request.COOKIES)
        if authorization is not None and authorization.find('Bearer ') == 0:
            token = authorization[7:]
        elif 'access_token' in request.COOKIES:
            token = request.COOKIES['access_token']
        if token is None:
            return None
        try:
            return (User.objects.get(
                pk=jwt.decode(
                    token,
                    settings.SECRET_KEY, algorithm='HS256'
                )['user_id']
            ), token)
        except Exception as e:
            raise exceptions.AuthenticationFailed('Invalid token')

    def authenticate_header(self, request):
        return 'Bearer'


def custom_exception_handler(exc, context):
    response = views.exception_handler(exc, context)

    if response is not None and response.status_code == 401:
        # we should delete the access_token cookie
        response.delete_cookie('access_token')

    return response
