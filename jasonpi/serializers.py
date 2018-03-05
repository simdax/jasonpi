from datetime import datetime, timezone
import httplib2

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
import django.contrib.auth.password_validation as validators
from django.core import exceptions as core_exceptions
from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions

from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField

from oauth2client.client import \
    AccessTokenCredentials, \
    AccessTokenCredentialsError
from googleapiclient.discovery import build

import facebook

from jasonpi.models import Provider
from jasonpi.normalizers import facebook_profile, google_profile

User = get_user_model()


def assign(instance, profile):
    for key in profile:
        if hasattr(instance, key) and (
                getattr(instance, key) is None or getattr(instance, key) == ''
        ):
            setattr(instance, key, profile[key])


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')


class ProviderSerializer(serializers.HyperlinkedModelSerializer):
    access_token = serializers.CharField(max_length=1025, write_only=True)

    def __init__(self, *args, **kwargs):
        self.user = None
        if 'context' in kwargs and \
                'request' in kwargs['context'] and \
                hasattr(kwargs['context']['request'], 'user'):
            user = kwargs['context']['request'].user
            if user.is_authenticated:
                self.user = user
        super(ProviderSerializer, self).__init__(*args, **kwargs)

    def validate_google(self, access_token, uid):
        try:
            credential = AccessTokenCredentials(
                access_token,
                'jasonpi/1.0'
            )
        except AccessTokenCredentialsError:
            raise exceptions.ValidationError(_('Invalid access token'))
        http = httplib2.Http()
        http = credential.authorize(http)
        service = build("people", "v1", http=http)
        user = service.people().get(
            resourceName='people/me',
            personFields='addresses,emailAddresses,names,genders,birthdays'
        ).execute()
        user_id = user['resourceName'].split('/')[1]
        if uid != user_id:
            raise exceptions.ValidationError(
                _('Google user id doesn\'t match'))
        return google_profile(user)

    def validate_facebook(self, access_token, uid):
        graph = facebook.GraphAPI(access_token=access_token)
        user = graph.get_object(
            id='me',
            fields='picture,first_name,last_name,name,birthday,gender,email',
        )
        if user['id'] != uid:
            raise exceptions.ValidationError(
                _('Facebook user id doesn\'t match'))
        return facebook_profile(user)

    def get_unique_together_validators(self):
        return []

    def validate(self, data):
        access_token = data.get('access_token')
        uid = data.get('uid')
        provider = data.get('provider')
        if provider == 'google':
            profile = self.validate_google(access_token, uid)
        elif provider == 'facebook':
            profile = self.validate_facebook(access_token, uid)
        else:
            raise exceptions.ValidationError(_('Provider not supported'))
        data['profile'] = profile
        if self.user is None:
            return super(ProviderSerializer, self).validate(data)
        try:
            pu = Provider.objects.get(
                uid=uid,
                provider=provider,
            )
            if pu.user != self.user:
                pass
                raise exceptions.ValidationError(
                    _('The social account you\'re to trying to use '
                      'is already linked to another user.')
                )
        except Provider.DoesNotExist:
            pass
        try:
            email_user = User.objects.get(email=profile['email'])
            if email_user != self.user:
                raise exceptions.ValidationError(
                    _('The email address for this social account is used by '
                      'another user.')
                )
        except User.DoesNotExist:
            pass
        return super(ProviderSerializer, self).validate(data)

    def save(self):
        current_user = self.user
        profile = self.validated_data['profile']
        uid = self.validated_data['uid']
        provider = self.validated_data['provider']

        try:
            up = Provider.objects.get(
                uid=uid,
                provider=provider
            )
            self.instance = up.user
            return
        except Provider.DoesNotExist:
            pass

        if current_user:
            user = current_user
        else:
            try:
                user = User.objects.get(email=profile['email'])
            except User.DoesNotExist:
                kwargs = init_kwargs(User, profile)
                user = User(**kwargs)
        assign(user, profile)
        user.save()
        Provider.objects.create(
            user=user,
            uid=uid,
            provider=provider
        )
        self.instance = user

    class Meta:
        model = Provider
        fields = ('url', 'uid', 'provider', 'access_token')


class UserSerializer(serializers.HyperlinkedModelSerializer):
    groups = ResourceRelatedField(
        queryset=Group.objects,
        many=True,
        related_link_view_name='user-groups-list',
        related_link_url_kwarg='user_pk',
        self_link_view_name='user-relationships',
        required=False,
    )

    providers = ResourceRelatedField(
        queryset=Provider.objects,
        many=True,
        related_link_view_name='user-providers-list',
        related_link_url_kwarg='user_pk',
        self_link_view_name='user-relationships',
        required=False,
    )

    included_serializers = {
        'groups': GroupSerializer,
        'providers': ProviderSerializer,
    }

    password = serializers.CharField(write_only=True)
    old_password = serializers.CharField(write_only=True, required=False)

    def validate(self, data):
        if self.instance:
            user = self.instance
        else:
            user = User(**data)

        password = data.get('password')
        if password is None:
            # if password is None it means it is not required
            # e.g. PATCH request
            return super(UserSerializer, self).validate(data)

        errors = dict()
        try:
            validators.validate_password(password=password, user=user)
        except core_exceptions.ValidationError as e:
            errors['password'] = list(e.messages)
        except Exception as e:
            raise e
        if self.instance and \
                not self.instance.check_password(data.get('old_password')):
            errors['old_password'] = _('Old password isn\'t valid.')

        if errors:
            raise serializers.ValidationError(errors)

        return super(UserSerializer, self).validate(data)

    def create(self, validated_data):
        user = User(**validated_data)
        user.last_login = datetime.now(timezone.utc)
        user.set_password(validated_data['password'])
        user.save()
        return user

    def update(self, instance, validated_data):
        instance = super(UserSerializer, self).update(instance, validated_data)
        password = validated_data.get('password')
        if password is not None:
            instance.set_password(password)
            instance.save()
        return instance

    def get_root_meta(self, resource, many):
        if hasattr(self, 'token'):
            return {
                'access_token': self.token
            }
        elif many:
            return {
                'size': len(resource)
            }
        return {}

    def get_fields(self):
        fields = super(UserSerializer, self).get_fields()
        limited_fields = getattr(self.Meta, 'limited_fields', fields)
        request = self.context.get('request', None)
        instance = self.instance
        if (
                instance and
                request is not None and
                hasattr(request, 'user') and
                request.user != instance
        ) or type(instance) == list:
            result = fields.copy()
            for field in fields:
                if field not in limited_fields:
                    result.pop(field)
            return result
        return fields

    class Meta:
        model = User
        fields = ('url', 'email', 'password', 'old_password', 'groups')


def init_kwargs(model, kwargs):
    return {
        k: v for k, v in kwargs.items() if k in [
            f.name for f in model._meta.get_fields()
        ]
    }
