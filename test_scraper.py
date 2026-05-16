import unittest
from unittest.mock import Mock, patch

import scraper


class ScraperTests(unittest.TestCase):
    def _session(self, side_effect):
        session = Mock()
        session.post.side_effect = side_effect
        return session

    def _response(self, elements):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {'elements': elements}
        return response

    def test_get_bbox_returns_known_city(self):
        self.assertEqual(scraper._get_bbox('Manchester'), (53.34, 53.55, -2.35, -2.10))

    @patch('scraper.time.sleep', return_value=None)
    @patch('scraper._build_session')
    def test_search_city_tries_second_tag_and_normalizes_website(self, build_session_mock, _sleep_mock):
        session = self._session([
            self._response([
                {'type': 'node', 'id': 101, 'tags': {
                    'name': 'Clip Joint',
                    'website': 'clipjoint.example',
                    'phone': '1234',
                    'contact:instagram': 'clipjointcuts',
                    'facebook': 'clipjointbarbers'
                }}
            ]),
            self._response([
                {'type': 'way', 'id': 202, 'tags': {'name': 'Fade House', 'contact:phone': '5678'}}
            ]),
        ])
        build_session_mock.return_value = session

        leads = scraper._search_city('barber', 'Manchester', 'UK')

        self.assertEqual(len(leads), 2)
        self.assertEqual(session.post.call_count, 2)
        self.assertEqual(leads[0]['website'], 'https://clipjoint.example')
        self.assertEqual(leads[0]['priority'], 'LOW')
        self.assertEqual(leads[0]['instagram'], 'https://www.instagram.com/clipjointcuts')
        self.assertEqual(leads[0]['facebook'], 'https://www.facebook.com/clipjointbarbers')
        self.assertEqual(leads[1]['priority'], 'HOT')
        self.assertTrue(leads[1]['has_contact'])
        self.assertTrue(leads[1]['profile_link'].startswith('https://www.openstreetmap.org/'))

    @patch('scraper.time.sleep', return_value=None)
    @patch('scraper._build_session')
    def test_business_email_domain_counts_as_likely_website(self, build_session_mock, _sleep_mock):
        session = self._session([
            self._response([
                {'type': 'node', 'id': 1, 'tags': {'name': 'North Studio', 'email': 'hello@northstudio.co.uk', 'phone': '1234'}}
            ]),
        ])
        build_session_mock.return_value = session

        leads = scraper._search_city('cafe', 'Manchester', 'UK')

        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]['website'], 'https://northstudio.co.uk')
        self.assertEqual(leads[0]['website_source'], 'email_domain')
        self.assertEqual(leads[0]['priority'], 'LOW')

    def test_extract_socials_uses_phone_for_whatsapp_and_normalizes_profiles(self):
        socials = scraper._extract_socials({
            'contact:telegram': '@northstudio',
            'instagram': 'northstudiocuts',
            'contact:tiktok': 'northstudio'
        }, '+234 801 234 5678')

        self.assertEqual(socials['whatsapp'], 'https://wa.me/2348012345678')
        self.assertEqual(socials['telegram'], 'https://t.me/northstudio')
        self.assertEqual(socials['instagram'], 'https://www.instagram.com/northstudiocuts')
        self.assertEqual(socials['tiktok'], 'https://www.tiktok.com/@northstudio')

    @patch('scraper.time.sleep', return_value=None)
    @patch('scraper._build_session')
    def test_search_city_falls_back_to_http_endpoint(self, build_session_mock, _sleep_mock):
        session = self._session([
            scraper.requests.exceptions.SSLError('bad cert'),
            self._response([
                {'tags': {'name': 'North Cafe'}}
            ]),
        ])
        build_session_mock.return_value = session

        leads = scraper._search_city('cafe', 'Manchester', 'UK')

        self.assertEqual(len(leads), 1)
        first_url = session.post.call_args_list[0].args[0]
        second_url = session.post.call_args_list[1].args[0]
        self.assertTrue(first_url.startswith('https://'))
        self.assertTrue(second_url.startswith('http://'))

    @patch('scraper.time.sleep', return_value=None)
    @patch('scraper._search_city')
    def test_search_region_keeps_same_name_in_different_cities(self, search_city_mock, _sleep_mock):
        search_city_mock.side_effect = [
            [{'name': 'The Workshop', 'city': 'London', 'address': '1 King St', 'priority': 'HOT'}],
            [{'name': 'The Workshop', 'city': 'New York', 'address': '10 Main St', 'priority': 'HOT'}],
        ]

        leads = scraper.search_region('builder', 'Worldwide', max_cities=2)

        self.assertEqual(len(leads), 2)


if __name__ == '__main__':
    unittest.main()
