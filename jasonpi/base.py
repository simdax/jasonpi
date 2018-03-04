from django.contrib.auth.models import (
    BaseUserManager,
    AbstractUser,
)
from django.db import models
from django.utils.translation import ugettext_lazy as _


class ExtraTimeFields(object):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class UserEmailManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class BaseUser(AbstractUser, ExtraTimeFields):
    objects = UserEmailManager()

    REQUIRED_FIELDS = []
    USERNAME_FIELD = 'email'

    username = None
    email = models.EmailField(_('email address'), unique=True)
    birthday = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return '%s %s <%s>' % (self.first_name, self.last_name, self.email)

    class Meta:
        abstract = True
