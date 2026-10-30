from django.urls import reverse

from allocations.models import User

PASSWORD = 'Allocation123'


def create_user(username='johndoe', first_name='John', last_name='Doe', is_superuser=False):
    """Create a user with the given details and the password PASSWORD."""
    return User.objects.create_user(
        username=username,
        first_name=first_name,
        last_name=last_name,
        email=f'{username}@example.org',
        password=PASSWORD,
        is_superuser=is_superuser,
    )


def create_superuser():
    """Create the superuser Jane Doe, as in the seed command."""
    return create_user('janedoe', 'Jane', 'Doe', is_superuser=True)


def logged_in_user_id(client):
    """Return the id of the user logged in on a test client, or None."""
    user_id = client.session.get('_auth_user_id')
    if user_id is None:
        return None
    return int(user_id)


def log_in_url_for(url):
    """Return the log in URL that @login_required redirects to from url."""
    return f"{reverse('log_in')}?next={url}"


def messages_in(response):
    """Return the texts of the messages shown in a response."""
    return [str(message) for message in response.context['messages']]
