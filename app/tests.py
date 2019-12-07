from django.test import TestCase
from django.urls import reverse
from app.models import LoanRequests, LoanInfo, BorrowerInfo

class AppViewsTestCase(TestCase):
    fixtures = ['app_views_testdata.json']
    def test_app(self):
        resp = self.client.get(reverse('apply'))
        self.assertEqual(resp.status_code, 200)
