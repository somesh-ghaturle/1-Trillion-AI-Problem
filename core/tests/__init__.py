from django.contrib.auth.models import Group, User

from core.apps import EDITOR_GROUP


def make_editor(username='tester'):
    user = User.objects.create_user(username)
    user.groups.add(Group.objects.get(name=EDITOR_GROUP))
    return user
