from django.apps import AppConfig
from django.db.models.signals import post_migrate

EDITOR_GROUP = 'Editor'


def sync_editor_group(sender, **kwargs):
    """Editor = every permission on core models. Re-synced on each migrate so new models are included."""
    from django.contrib.auth.models import Group, Permission

    group, _ = Group.objects.get_or_create(name=EDITOR_GROUP)
    group.permissions.add(*Permission.objects.filter(content_type__app_label='core'))


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        post_migrate.connect(sync_editor_group, sender=self)
