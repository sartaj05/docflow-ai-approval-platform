from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import UserProfile, UserRole


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.is_superuser:
        role = UserRole.SUPER_ADMIN
    else:
        role = UserRole.STAFF

    UserProfile.objects.create(
        user=instance,
        role=role,
    )