# users/management/commands/setup_permissions.py
from django.core.management.base import BaseCommand
from utils.permissions_setup import setup_permissions

class Command(BaseCommand):
    help = 'Set up user groups and permissions'

    def handle(self, *args, **kwargs):
        self.stdout.write("Setting up groups and permissions...")
        setup_permissions()
        self.stdout.write(self.style.SUCCESS("Successfully set up groups and permissions!"))