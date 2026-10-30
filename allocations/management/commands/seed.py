from django.core.management.base import BaseCommand

from allocations.models import User

FIRST_NAMES = ['Alice', 'Ben', 'Chloe', 'Daniel', 'Emma', 'Farah', 'George', 'Hana', 'Ivan', 'Jade']
LAST_NAMES = ['Ahmed', 'Brown', 'Chen', 'Doe', 'Evans', 'Garcia', 'Khan', 'Novak', 'Patel', 'Smith']
PASSWORD = 'Allocation123'


class Command(BaseCommand):
    help = 'Fill the database with sample users. Run "python manage.py unseed" to remove them.'

    def handle(self, *args, **options):
        self.create_user('janedoe', 'Jane', 'Doe', is_superuser=True)
        self.create_user('johndoe', 'John', 'Doe')
        for first_name in FIRST_NAMES:
            for last_name in LAST_NAMES:
                username = f'{first_name}.{last_name}'.lower()
                self.create_user(username, first_name, last_name)
        self.stdout.write(f'The database now contains {User.objects.count()} users.')
        self.stdout.write(f'Log in as "janedoe" (superuser) or "johndoe", with password "{PASSWORD}".')

    def create_user(self, username, first_name, last_name, is_superuser=False):
        if User.objects.filter(username=username).exists():
            return
        User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=f'{username}@example.org',
            password=PASSWORD,
            is_superuser=is_superuser,
            is_staff=is_superuser,
        )
