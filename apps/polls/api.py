from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from adhocracy4.polls.api import PollViewSet as BasePollViewSet
from apps.captcha.utils import verify_token


class PollViewSet(BasePollViewSet):
    def check_captcha(self):
        token = self.request.data.get("captcha", "")
        if not token:
            raise ValidationError(_("Please complete the captcha."))
        if not verify_token(token):
            raise ValidationError(_("Captcha verification failed. Please try again."))
