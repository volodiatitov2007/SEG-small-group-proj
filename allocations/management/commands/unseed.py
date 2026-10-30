from django.core.management.base import BaseCommand

from allocations.models import User


class Command(BaseCommand):
    help = 'Delete all users from the database.'

    def handle(self, *args, **options):
        count = User.objects.count()
        User.objects.all().delete()
        self.stdout.write(f'Deleted {count} users.')
