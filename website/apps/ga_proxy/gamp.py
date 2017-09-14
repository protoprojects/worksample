class GampMessage(object):
    """
    Base class for Google Analytics Measurement Protocol
    All based on dicts for input.
    """

    def __init__(self, data, ga_tracking_id):
        """
        data:   keyvalue pairs matching GA event message
        """
        if not isinstance(data, dict):
            raise TypeError("Data must be a dict")

        self.tracking_id = ga_tracking_id
        self.data = data
        self.error_msg = None
        self.remote_ip = None
        self.remote_user_agent = None

    def _apply_proxy_values(self):
        if self.remote_ip:
            self.data['uip'] = self.remote_ip
        if self.remote_user_agent:
            self.data['ua'] = self.remote_user_agent

    def set_proxy_values(self, ip, ua):
        self.remote_ip = ip
        self.remote_user_agent = ua

    def get_error_message(self):
        return self.error_msg

    # pylint: disable=no-self-use
    @property
    def is_valid(self):
        return False

    @property
    def payload(self):
        return self.data


class GampRawTag(GampMessage):
    """
    Pass the tag values straight through, no manipulation
    """

    def __init__(self, data):
        super(GampRawTag, self).__init__(data, 'faketrack')

    @property
    def is_valid(self):
        return True

    @property
    def payload(self):
        self._apply_proxy_values()
        return self.data


class GampTag(GampMessage):
    """
    Pass tag values through, but include universal config and boilerplate
    """

    @property
    def is_valid(self):
        return True

    @property
    def payload(self):
        self._apply_proxy_values()
        self.data['v'] = '1'
        self.data['tid'] = self.tracking_id

        return self.data


class GampEvent(GampMessage):
    """
    Google Analytics Measurement Protocol
    Validate and Format Event Message
    v=1             // Version.
    &tid=UA-XXXX-Y  // Tracking ID / Property ID.
    &cid=555        // Anonymous Client ID.

    &t=event        // Event hit type
    &ec=video       // Event Category. Required.
    &ea=play        // Event Action. Required.
    &el=holiday     // Event label.
    &ev=300         // Event value.
    """

    @property
    def is_valid(self):
        required_params = {"cid", "ec", "ea"}
        keys = set(self.data)
        missing_params = required_params - keys
        if missing_params:
            self.error_msg = "Required Parameters Missing: %s" % (
                ','.join(sorted(missing_params)))
            return False

        return True

    @property
    def payload(self):
        self._apply_proxy_values()

        # override sent values
        self.data['v'] = '1'
        self.data['tid'] = self.tracking_id
        self.data['t'] = 'event'

        return self.data


class GampPageview(GampMessage):
    """
    Google Analytics Measurement Protocol
    Validate and Format Pageview Message

    v=1             // Version.
    &tid=UA-XXXX-Y  // Tracking ID / Property ID.
    &cid=555        // Anonymous Client ID.

    &t=pageview     // Pageview hit type.
    &dh=mydemo.com  // Document hostname.
    &dp=/home       // Page.
    &dt=homepage    // Title.

    For 'pageview' hits, either &dl or both &dh and &dp
        have to be specified for the hit to be valid.
    """

    @property
    def is_valid(self):
        if 'cid' not in self.data:
            self.error_msg = "Required Parameters Missing: (cid)"
            return False

        if 'dl' in self.data:
            return True
        elif 'dh' in self.data and 'dp' in self.data:
            return True
        else:
            self.error_msg = "Required Parameters Missing: (dl) or (dh and dp)"
            return False

    @property
    def payload(self):
        self._apply_proxy_values()

        # override sent values
        self.data[u'v'] = u'1'
        self.data[u'tid'] = self.tracking_id
        self.data[u't'] = u'pageview'

        return self.data
