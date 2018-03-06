import jwt
import datetime
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions, views
from rest_framework_json_api.relations import ResourceRelatedField

from django.urls import path

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


def resource_relationships(name, view):
    """Add a path for an resource relationships."""
    return path(
        '%s/<int:pk>/relationships/<related_field>' % name,
        view,
        name='%s-relationships' % name,
    )


def resource_related_field(
    model,
    name,
    relationship,
    many=True,
    required=False,
    read_only=False,
):
    """Generate a ResourceRelatedField for given resource and relationship."""
    kwargs = {}
    if not read_only:
        kwargs['queryset'] = model.objects
    return ResourceRelatedField(
        many=many,
        related_link_view_name='%s-%s-%s' % (
            name,
            relationship,
            'list' if many else 'detail',
        ),
        related_link_url_kwarg='%s_pk' % name,
        required=required,
        read_only=read_only,
        **kwargs,
    )
