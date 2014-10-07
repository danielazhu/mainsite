import logging
from django.conf import settings
import ldap
from django.contrib.auth.models import User, check_password

class ImproperlyConfigured(Exception):
    pass

class SimpleLDAPBackend(object):
    """
    Authenticate against an LDAP directory server.

    Set LDAP_SERVER = ('hostname', port) in your settings.
    """
    def authenticate(
            self,
            username=None,
            password=None,
            college=settings.AUTH_LDAP_DEFAULT_COLLEGE):
        try:
            ldap_info = settings.AUTH_LDAP[college]
        except KeyError:
            raise ImproperlyConfigured("Missing AUTH_LDAP setting in settings.py")
        try:
            l = ldap.initialize("ldap://{0}:{1}/".format(ldap_info['server'], ldap_info['port']))
            l.protocol_version = ldap.VERSION3
            l.simple_bind_s(
                ldap_info['bind_as'].format(username).encode('utf-8'),
                password.encode('utf-8')
            )
        except ldap.LDAPError, e:
            # most likely (but not definitely) because credentials were incorrect
            # return None because this is all we know.
            return None

        # let LDAPError propagate

        ldap_result_id = l.search(ldap_info['base_dn'], ldap.SCOPE_SUBTREE, ldap_info['filter'].format(username), None)
        result = None
        while not result:
            result_type, result_data = l.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    result = result_data

        user_data = result[0][1]
        try:
            user = User.objects.get(username=user_data['cn'][0])
        except User.DoesNotExist:

            # Some users are in ActiveDirectory without all their info. We don't
            # want to get an error email for each login attempt, but we don't
            # just want to log them in without info, so we just fail to
            # authenticate.

            if not all((
                user_data.get('cn', False),
                user_data.get('givenName', False),
                user_data.get('sn', False),
                user_data.get('mail', False)
            )):
                return None

            user = User(
                username=user_data['cn'][0],
                first_name=user_data['givenName'][0],
                last_name=user_data['sn'][0],
                email=user_data['mail'][0],
            )
            user.set_unusable_password()
            user.save()
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None