from datetime import datetime, date, timezone
import os
import hashlib
import base64
import hmac
import json
import uuid
import boto3
import re

from django.http import HttpResponseBadRequest
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string
from django.contrib.auth import get_user_model
from rest_framework import \
    viewsets, \
    exceptions, \
    parsers, \
    mixins, \
    renderers as default_renderers
from rest_framework.decorators import \
    api_view, \
    permission_classes, \
    renderer_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_json_api import renderers, parsers as jsonapi_parsers

from jasonpi.serializers import \
    UserSerializer as JPIUserSerializer, \
    ProviderSerializer
from jasonpi.auth import get_token

User = get_user_model()

if hasattr(settings, 'USER_SERIALIZER'):
    UserSerializer = import_string(settings.USER_SERIALIZER)
else:
    UserSerializer = JPIUserSerializer

if hasattr(settings, 'S3_KEY_GETTER'):
    s3_key_getter = import_string(settings.S3_KEY_GETTER)
else:
    def s3_key_getter(request, ext):
        return 'u%d/misc/%s_%s.%s' % (
            request.user.id,
            date.today().strftime('%Y-%m-%d'),
            uuid.uuid4(),
            ext
        )


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
        user_serializer = UserSerializer(user, context={'request': request})
        response = Response(user_serializer.data)
        response.set_cookie(
            'access_token',
            token,
            secure=not settings.DEBUG,
            httponly=True
        )
        user_serializer.token = token
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
        try:
            provider_serializer = ProviderSerializer(
                data=request.data,
                context={'request': request}
            )
            provider_serializer.is_valid(raise_exception=True)
            provider_serializer.save()
            user = provider_serializer.instance
            token = get_token(user)
            print('AuthProviderView token =', token)
            user.last_login = datetime.now(timezone.utc)
            user.save()
            user_serializer = UserSerializer(
                user,
                context={'request': request},
            )
            response = Response(user_serializer.data)
            response.set_cookie(
                'access_token',
                token,
                secure=not settings.DEBUG,
                httponly=True
            )
            user_serializer.token = token
            return response
        except Exception as e:
            raise e


class AuthRegisterView(mixins.CreateModelMixin,
                       viewsets.GenericViewSet):
    parser_classes = (jsonapi_parsers.JSONParser, )
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
@renderer_classes([default_renderers.JSONRenderer])
def s3_get_presigned_url(request):
    s3 = boto3.client('s3')
    object_name = request.GET.get('objectName')
    ext = object_name.split('.')[-1]
    key = s3_key_getter(request, ext)
    bucket = settings.BUCKET
    user_id = request.user.id
    regex = re.compile(
        r'u?%d/(assets|misc)/[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9a-z-]+\.[^\.]+' %
        user_id,
    )
    if not regex.match(key):
        raise HttpResponseBadRequest({'error': 'Wrong S3 Key'})
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


@api_view(['POST'])
@renderer_classes([default_renderers.JSONRenderer])
def s3_sign_policy_document(request):
    request_payload = json.loads(request.body)
    headers = request_payload.get('headers', None)
    if headers:
        # The presence of the 'headers' property in the request payload
        # means this is a request to sign a REST/multipart request
        # and NOT a policy document
        response_data = sign_headers(headers)
    else:
        response_data = sign_policy_document(request_payload)
    return Response(response_data)


def sign_headers(headers):
    """ Sign and return the headers for a chunked upload. """
    return {
        'signature': base64.b64encode(hmac.new(
            os.environ.get('AWS_SECRET_ACCESS_KEY').encode('utf-8'),
            headers.encode('utf-8'),
            hashlib.sha1,
        ).digest()).decode('utf-8'),
    }


def sign_policy_document(policy_document):
    """ Sign and return the policy doucument for a simple upload.
    http://aws.amazon.com/articles/1434/#signyours3postform
    """
    policy = base64.b64encode(json.dumps(policy_document).encode('utf-8'))
    signature = base64.b64encode(hmac.new(
        os.environ.get('AWS_SECRET_ACCESS_KEY').encode('utf-8'),
        policy,
        hashlib.sha1,
    ).digest())
    return {
        'policy': policy.decode('utf-8'),
        'signature': signature.decode('utf-8'),
    }
