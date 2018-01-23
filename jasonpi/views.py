from datetime import datetime, date, timezone
import uuid
import boto3
import os

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string
from django.contrib.auth import get_user_model
from rest_framework import \
    viewsets, \
    exceptions, \
    parsers, \
    mixins, \
    renderers as defaultRenderers
from rest_framework.decorators import \
    api_view, \
    permission_classes, \
    renderer_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_json_api import renderers, parsers as JsonAPIParsers

from jasonpi.serializers import \
    UserSerializer as JPIUserSerializer, \
    ProviderSerializer
from jasonpi.utils import get_token

User = get_user_model()

if hasattr(settings, 'USER_SERIALIZER'):
    UserSerializer = import_string(settings.USER_SERIALIZER)
else:
    UserSerializer = JPIUserSerializer


class AuthSignInView(APIView):
    parser_classes = (parsers.JSONParser, )
    permission_classes = (AllowAny, )
    renderer_classes = (renderers.JSONRenderer, )
    resource_name = 'users'

    def post(self, request):
        msg = _('Invalid credentials')
        try:
            email = request.data.get('email')
            password = request.data.get('password')
        except AttributeError:
            raise exceptions.ValidationError(msg)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise exceptions.ValidationError(msg)
        if not user.check_password(password):
            raise exceptions.ValidationError(msg)
        token = get_token(user)
        user.last_login = datetime.now(timezone.utc)
        user.save()
        userSerializer = UserSerializer(user, context={'request': request})
        response = Response(userSerializer.data)
        response.set_cookie(
            'access_token',
            token,
            secure=not settings.DEBUG,
            httponly=True
        )
        userSerializer.token = token
        return response


@api_view()
@permission_classes([AllowAny])
def signout(request):
    response = Response(status=204)
    response.delete_cookie('access_token')
    return response


class AuthProviderView(APIView):
    parser_classes = (parsers.JSONParser, )
    permission_classes = (AllowAny, )
    renderer_classes = (renderers.JSONRenderer, )
    resource_name = 'users'

    def post(self, request):
        providerSerializer = ProviderSerializer(
            data=request.data,
            context={'request': request}
        )
        providerSerializer.is_valid(raise_exception=True)
        providerSerializer.save()
        user = providerSerializer.instance
        token = get_token(user)
        user.last_login = datetime.now(timezone.utc)
        user.save()
        userSerializer = UserSerializer(user, context={'request': request})
        response = Response(userSerializer.data)
        response.set_cookie(
            'access_token',
            token,
            secure=not settings.DEBUG,
            httponly=True
        )
        userSerializer.token = token
        return response


class AuthRegisterView(mixins.CreateModelMixin,
                       viewsets.GenericViewSet):
    parser_classes = (JsonAPIParsers.JSONParser, )
    serializer_class = UserSerializer
    permission_classes = (AllowAny, )
    resource_name = 'users'

    def create(self, request, *args, **kwargs):
        response = super(AuthRegisterView, self).create(
            request,
            *args,
            **kwargs
        )
        token = get_token(response.data.serializer.instance)
        response.set_cookie(
            'access_token',
            token,
            secure=not settings.DEBUG,
            httponly=True
        )
        response.data.serializer.token = token
        return response


@api_view()
@renderer_classes([defaultRenderers.JSONRenderer])
def s3_get_presigned_url(request):
    s3 = boto3.client('s3')
    type = request.GET.get('type', 'profile')
    objectName = request.GET.get('objectName')
    ext = objectName.split('.')[-1]
    if type == 'profile':
        key = '%d/profile/%s_%s.%s' % (
            request.user.id,
            date.today().strftime('%Y-%m-%d'),
            uuid.uuid4(),
            ext
        )
    bucket = os.environ.get('BUCKET', 'kincube-development')
    params = {
        'Bucket': bucket,
        'Key': key,
        'ACL': 'public-read',
    }
    content_type = request.GET.get('contentType', None)
    if content_type is not None:
        params['ContentType'] = content_type
    url = s3.generate_presigned_url(
        'put_object',
        Params=params,
        ExpiresIn=3600
    )
    return Response({'signedUrl': url})
