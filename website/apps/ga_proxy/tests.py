from django.test import TestCase
from ga_proxy.views import GampEvent, GampPageview, GampTag

# Create your tests here.


class GampMessageTests(TestCase):

    def test_valid_event_message(self):
        valid_event = {'ec': 'video',
                       'ea': 'play',
                       'el': 'holiday',
                       'ev': '300',
                       'cid': 'XXX-XXX-XXX'}

        event_msg = GampEvent(valid_event, 'TRACKID')
        payload = event_msg.payload
        self.assertTrue(event_msg.is_valid)
        self.assertEqual(len(payload), 8)
        self.assertIn('tid', payload)
        self.assertEqual(payload['tid'], 'TRACKID')
        self.assertIn('cid', payload)
        self.assertIn('ec', payload)
        self.assertIn('ea', payload)

    def test_missing_event_category(self):
        invalid_event = {'ea': 'play',
                         'el': 'holiday',
                         'ev': '300',
                         'cid': 'XXX-XXX-XXX'}
        event_msg = GampEvent(invalid_event, 'TRACKID')
        self.assertFalse(event_msg.is_valid)
        self.assertEqual(len(event_msg.payload), 7)

    def test_missing_event_action(self):
        invalid_event = {'ec': 'video',
                         'el': 'holiday',
                         'ev': '300'}
        event_msg = GampEvent(invalid_event, 'TRACKID')
        self.assertFalse(event_msg.is_valid)
        self.assertEqual(len(event_msg.payload), 6)

    def test_valid_pageview_message(self):
        """
        For 'pageview' hits, either &dl or both &dh and &dp
            have to be specified for the hit to be valid.
        """

        pvs = [{'dh': 'mydemo.com',
                'dp': '/home',
                'dt': 'homepage',
                'cid': 'XXX-XXX-XXX'},

               {'dl': 'http://mydemo.com/home',
                'dt': 'homepage',
                'd': 'yes',
                'cid': 'XXX-XXX-XXX'}]

        for pv in pvs:
            pv_msg = GampPageview(pv, 'TRACKID')
            payload = pv_msg.payload
            self.assertTrue(pv_msg.is_valid)
            self.assertEqual(len(payload), 7)
            self.assertIn('tid', payload)
            self.assertEqual(payload['tid'], 'TRACKID')
            self.assertIn('cid', payload)
            self.assertIn('dt', payload)

    def test_missing_pageview_link(self):
        invalid_pv = {'dh': 'mydemo.com',
                      'dt': 'homepage'}
        pv_msg = GampPageview(invalid_pv, 'TRACKID')
        self.assertFalse(pv_msg.is_valid)
        self.assertEqual(len(pv_msg.payload), 5)

    def test_valid_tag(self):
        tag = {'a': 'alpha',
               'b': 'beta',
               'c': 'charlie'}
        msg = GampTag(tag, 123)
        self.assertTrue(msg.is_valid)
        self.assertEqual(len(msg.payload), 5)

    def test_strange_tag(self):
        t = "this is a strange tag"
        with self.assertRaisesMessage(TypeError, "Data must be a dict"):
            GampTag(t, 123)
