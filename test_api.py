import csv
import io
import unittest
from unittest.mock import patch

from app import app
from scraper import BUSINESS_TYPES


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_regions_route_returns_known_regions(self):
        response = self.client.get('/regions')

        self.assertEqual(response.status_code, 200)
        self.assertIn('Worldwide', response.get_json())

    def test_categories_route_returns_supported_business_types(self):
        response = self.client.get('/categories')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), list(BUSINESS_TYPES))

    def test_search_requires_category(self):
        response = self.client.post('/search', json={'category': ''})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['error'], 'Business type is required.')

    @patch('app.search_region')
    @patch('app.list_contacted', return_value={})
    def test_search_coerces_invalid_max_cities_and_returns_counts(self, _list_contacted_mock, search_region_mock):
        search_region_mock.return_value = [
            {'lead_id': 'a', 'name': 'A', 'priority': 'HOT', 'has_contact': True},
            {'lead_id': 'b', 'name': 'B', 'priority': 'LOW', 'has_contact': False},
        ]

        response = self.client.post('/search', json={
            'category': 'barber',
            'region': 'Unknown',
            'max_cities': 'not-a-number',
        })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['hot'], 1)
        self.assertEqual(payload['with_contact'], 1)
        search_region_mock.assert_called_once_with('barber', 'Worldwide', 2)

    @patch('app.search_region')
    @patch('app.list_contacted', return_value={})
    def test_search_can_return_non_actionable_leads(self, _list_contacted_mock, search_region_mock):
        search_region_mock.return_value = [
            {'lead_id': 'a', 'name': 'A', 'priority': 'HOT', 'has_contact': True, 'email': 'a@example.com'},
            {'lead_id': 'b', 'name': 'B', 'priority': 'WARM', 'has_contact': False},
            {'lead_id': 'c', 'name': 'C', 'priority': 'LOW', 'has_contact': True},
        ]

        response = self.client.post('/search', json={
            'category': 'barber',
            'actionable_only': False,
        })

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['total'], 3)
        self.assertEqual(payload['warm'], 1)
        self.assertEqual(payload['low'], 1)
        self.assertEqual(payload['with_email'], 1)

    @patch('app.search_region')
    @patch('app.list_contacted', return_value={'a': {'lead_id': 'a'}})
    def test_search_hides_contacted_by_default(self, _list_contacted_mock, search_region_mock):
        search_region_mock.return_value = [
            {'lead_id': 'a', 'name': 'A', 'priority': 'HOT', 'has_contact': True},
            {'lead_id': 'b', 'name': 'B', 'priority': 'HOT', 'has_contact': True},
        ]

        response = self.client.post('/search', json={'category': 'barber'})
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['contacted_count'], 1)
        self.assertEqual(payload['leads'][0]['lead_id'], 'b')

    @patch('app.mark_contacted')
    def test_mark_contacted_route(self, mark_contacted_mock):
        mark_contacted_mock.return_value = {'lead_id': 'a'}

        response = self.client.post('/contacted', json={'lead': {'lead_id': 'a', 'name': 'A'}})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        mark_contacted_mock.assert_called_once()

    @patch('app.unmark_contacted', return_value={'lead_id': 'a'})
    def test_unmark_contacted_route(self, unmark_contacted_mock):
        response = self.client.delete('/contacted/a')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['removed'])
        unmark_contacted_mock.assert_called_once_with('a')

    def test_export_writes_csv(self):
        response = self.client.post('/export', json={'leads': [
            {'lead_id': 'abc', 'name': 'Lead One', 'phone': '123'},
        ]})

        self.assertEqual(response.status_code, 200)
        reader = csv.DictReader(io.StringIO(response.get_data(as_text=True)))
        rows = list(reader)
        self.assertEqual(rows[0]['lead_id'], 'abc')
        self.assertEqual(rows[0]['name'], 'Lead One')
        self.assertEqual(rows[0]['phone'], '123')

    def test_index_renders_business_type_suggestions(self):
        response = self.client.get('/')
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('datalist id="businessTypeList"', html)
        self.assertIn('value="barber"', html)


if __name__ == '__main__':
    unittest.main()

