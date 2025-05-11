from django import template
from social_django.models import UserSocialAuth

register = template.Library()

@register.filter
def has_social_auth(user, provider):
    if user.is_authenticated:
        try:
            user.social_auth.get(provider=provider)
            return True
        except UserSocialAuth.DoesNotExist:
            return False
    return False