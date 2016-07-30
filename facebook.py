import json
import logging
from google.appengine.api import urlfetch


FACEBOOK_APP_ID = ''
FACEBOOK_APP_SECRET = ''


class FacebookAPI(object):

    def __init__(self):
        self.base_url = 'https://graph.facebook.com'

    @property
    def app_token(self):
        return '%s|%s' % (
            FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)

    def _fetch(self, method, path, data=None):  # noqa pragma: no cover
        data = data or {}
        url = '%s%s&access_token=%s' % (
            self.base_url, path, self.app_token)
        headers = {
            'Accept': 'application/json;',
            'Content-Type': 'text/html; charset=utf-8',
        }
        return urlfetch.Fetch(
            url,
            payload=json.dumps(data),
            method=method,
            headers=headers)

    def check_user_token(self, facebook_profile_id, facebook_access_token):
        try:
            res = self._fetch(
                'GET', '/debug_token?input_token=%s' % facebook_access_token)

            if res.status_code != 200:  # pragma: no cover
                logging.error(res.content)
                logging.error(res.content)
            data = json.loads(res.content)
            correct_app = (str(data['data']['app_id']) ==
                           FACEBOOK_APP_ID)
            correct_user = (str(data['data']['user_id']) ==
                            facebook_profile_id)
            return correct_app and correct_user

        except Exception as e:  # pragma: no cover
            logging.error(str(e))
            return False
