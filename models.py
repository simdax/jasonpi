from django.contrib.auth import get_user_model
from django.db import models


class Provider(models.Model):
    uid = models.CharField(max_length=255)
    provider = models.CharField(max_length=255)
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='providers',
    )

    class Meta:
        unique_together = (('uid', 'provider'), )
