import datetime
from django.test import TestCase
from django.urls import reverse
from app.models import LoanRequests, LoanInfo, BorrowerInfo

class LoansViewsTestCase(TestCase):
    fixtures = ['loans_views_testdata.json']
    def test_loans(self):
        resp = self.client.get(reverse('loans'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('loans' in resp.context)
        self.assertTrue([loan.pk for loan in resp.context['loans']], [4])
        loan_test = resp.context['loans'][0]
        self.assertEqual(loan_test.borrower.firstName, 'Anna')

    def test_submitForApproval(self):
        resp = self.client.post(reverse('submitForApproval'), {'loanNumber':7})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('response' in resp.context)
        self.assertTrue('chartdata' in resp.context)
