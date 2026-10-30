from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A user of the group allocation application.

    AbstractUser already provides username, first_name, last_name, email,
    password and is_superuser (amongst others). We redefine first_name,
    last_name and email so that they are required, and so that no two users
    can share an email address.
    """

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.get_full_name()} ({self.username})'
