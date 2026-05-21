from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    google_id = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=255, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.display_name or self.email
