from django.conf import settings
from .gamp import GampEvent
from .gamp_transport import send


def prequal_completed(anon_user_id, hostname, remote_ip, user_agent):
    event_data = {'an': 'PreQual',
                  'ec': 'application',
                  'ea': 'completed',
                  'dh': hostname,
                  'cid': anon_user_id}

    ga_msg = GampEvent(event_data, settings.GA_PROXY_TRACKING_ID)
    ga_msg.set_proxy_values(ip=remote_ip, ua=user_agent)

    if ga_msg.is_valid:
        send(ga_msg.payload)
        return True

    return False
