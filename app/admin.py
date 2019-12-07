from django.contrib import admin
from .models import LoanRequests, BorrowerInfo, LoanInfo, PropertyInfo


# Register your models here.
admin.site.register(LoanRequests)
admin.site.register(BorrowerInfo)
admin.site.register(LoanInfo)
admin.site.register(PropertyInfo)
