from django.db import models
from datetime import datetime
from django.utils import timezone

# Create your models here.
class BorrowerInfo(models.Model):
    firstName = models.CharField(max_length=100,null=True)
    lastName = models.CharField(max_length=100,null=True)
    email = models.CharField(max_length=200, null=True)

class LoanInfo(models.Model):
    program = models.CharField(max_length=30,null=True)
    amount = models.FloatField(default=0)
    fico = models.IntegerField(default=0)
    income = models.FloatField(default=0)

class PropertyInfo(models.Model):
    address = models.CharField(max_length=200,null=True)
    country = models.CharField(max_length=200, default='United States',null=True)
    state = models.CharField(max_length=100,null=True)
    zip = models.CharField(max_length=10,null=True)

class LoanRequests(models.Model):
    loanNumber = models.AutoField(primary_key=True)
    userID = models.IntegerField(default=0)
    dateCreated = models.DateField(default=timezone.now)
    dateApproved = models.DateField(null=True, blank=True)
    dateSubmitted = models.DateField(null=True, blank=True)
    dateDenied = models.DateField(null=True, blank=True)
    borrower = models.ForeignKey(BorrowerInfo,
        on_delete=models.CASCADE, blank=True, null=True)
    loanInfo = models.ForeignKey(LoanInfo,
        on_delete=models.CASCADE, blank=True, null=True)
    property = models.ForeignKey(PropertyInfo,
        on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return str(self.loanNumber)
