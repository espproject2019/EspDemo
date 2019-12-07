from django.shortcuts import render
import base64, os
from django.utils import timezone
import datetime
#from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition, Signer, SignHere, Tabs, Recipients, Document
from app.models import LoanRequests, LoanInfo, BorrowerInfo
from django.http import HttpResponse
import django
from django.conf import settings
from django.core.mail import send_mail
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64
import email
import html2text
from email.mime.text import MIMEText
from sklearn import tree
import pandas as pd
import requests
import json
from django.conf import settings

access_token = getattr(settings, "DOCUSIGN_TOKEN", None)
account_id = getattr(settings, "DOCUSIGN_ACCOUNT_ID", None)
file_name_path = getattr(settings, "APPROVAL_TEMPLATE", None)
token_path = getattr(settings, "TOKEN_PATH", None)
csv_path = getattr(settings, "DATASET", None)
base_path = getattr(settings, "DOCUSIGN_URL_API", None)
loan_model_api = getattr(settings, "LOAN_MODEL_API", None)

APP_PATH = os.path.dirname(os.path.abspath(__file__))
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# views
def loans(request):
	paint_logout = False
	if 'samlUserdata' in request.session:
		paint_logout = True
		loans = LoanRequests.objects.all().filter(dateApproved__isnull=True).filter(dateDenied__isnull=True)
		loansList= {'loans': loans}
		return render(request, 'loans/approve.html', {'loans': loans, 'paint_logout': paint_logout})
	else:
		return render(request, 'sso/index.html')

def statistics(request):
	# get data for statistics
	paint_logout = False
	if 'samlUserdata' in request.session:
		paint_logout = True
		approved = getApproved()
		denied = getDenied()
		inprocess = getNotProcessed()
		chartdata = getChartData()
		return render(request, 'loans/statistics.html', {'approveddata': approved, 'denieddata': denied, 'inprocess' : inprocess, 'chartdata' : chartdata, 'paint_logout': paint_logout})
	else:
		return render(request, 'sso/index.html')


def submitForApproval(request):
	# all post request data
	data = request.POST.dict()
	# get loanNumber from request
	loanToBeApprovedDenied = data.get('loanNumber')
	# get loan info from database for requested loan
	loan = LoanRequests.objects.all().get(loanNumber=loanToBeApprovedDenied)
	# machine learning results,
	print(loan.borrower)

	#prediction
	try:
		ml_approved = decisionTreeForLoanApprovalRestAPI(loan)
		print('approved from rest api = ', ml_approved)
	except:
		ml_approved = decisionTreeForLoanApproval(loan)
		print('approved from method = ', ml_approved)

	if ml_approved == '1': # if loan is approved
		message_text_approved = 'This e-mail is to notify you that your loan is now Approved. Please check your e-mail and e-sign Approval letter.\n Thank you for trusting us!  Gryffindor MMS'
		sendMail(message_text_approved, loan)
		# update DateApproved in database
		loan.dateApproved=timezone.now()
		loan.save()

		# *** Docusign create envelop and send for e-sign ***
		signer_name = loan.borrower.firstName + ' ' + loan.borrower.lastName
		signer_email = loan.borrower.email

		# *** calling docusign api
		try:

			data={'loanid':loanToBeApprovedDenied,'name':signer_name, 'email':signer_email}
			j_data = json.dumps(data)
			headers = {'content-type': 'application/json', 'Accept-Charset': 'UTF-8'}
			resp = requests.post("http://ec2-13-52-212-244.us-west-1.compute.amazonaws.com/sendesign",data = json.dumps(data),headers=headers)

			#results = send_document_for_signing(signer_name, signer_email)
			# print("\nEnvelope status: " + results.status + ". Envelope ID: " + results.envelope_id + "\n")
		except:
	  		print('error calling docusign')
		response = 'The ' + loan.borrower.lastName + ' loan has been approved. Email has been sent to borrower with status update and request to electronically sign approval letter.'
	else: # if loan is denied
		loan.dateDenied=timezone.now()
		loan.save()
		message_text_denied = 'This email is to notify you that your loan has been denied. If you have any questions please contact us at (800) 888-00-00 \n Regards, Gryffindor MMS'
		sendMail(message_text_denied, loan)
		response = 'Loan ' + loan.borrower.lastName + ' was denied. Email has been to borrower with status update.'
	# get data for charts
	approved = getApproved()
	denied = getDenied()
	current = [[loan.loanInfo.fico, loan.loanInfo.income]]
	return render(request, 'loans/statusresponse.html', {'response': response,'current' : current, 'approved' : approved, 'denied' : denied} )

def send_document_for_signing(signer_name, signer_email):
    # Create the component objects for the envelope definition...
    with open(os.path.join(APP_PATH, file_name_path), "rb") as file:
        content_bytes = file.read()
    base64_file_content = base64.b64encode(content_bytes).decode('ascii')

    document = Document( # create the DocuSign document object
        document_base64 = base64_file_content,
        name = 'Example document', # can be different from actual file name
        file_extension = 'pdf', # many different document types are accepted
        document_id = 1 # a label used to reference the doc
    )

    # Create the signer recipient model
    signer = Signer( # The signer
        email = signer_email, name = signer_name, recipient_id = "1", routing_order = "1")

    # Create a sign_here tab (field on the document)
    sign_here = SignHere( # DocuSign SignHere field/tab
        document_id = '1', page_number = '1', recipient_id = '1', tab_label = 'SignHereTab',
        x_position = '195', y_position = '147')

    # Add the tabs model (including the sign_here tab) to the signer
    signer.tabs = Tabs(sign_here_tabs = [sign_here]) # The Tabs object wants arrays of the different field/tab types

    # Next, create the top level envelope definition and populate it.
    envelope_definition = EnvelopeDefinition(
        email_subject = "Please sign this Approval Letter for your loan.",
        documents = [document], # The order in the docs array determines the order in the envelope
        recipients = Recipients(signers = [signer]), # The Recipients object wants arrays for each recipient type
        status = "sent" # requests that the envelope be created and sent.
    )

	# send envelope request
    api_client = ApiClient()
    api_client.host = base_path
    api_client.set_default_header("Authorization", "Bearer " + access_token)

    envelope_api = EnvelopesApi(api_client)
    results = envelope_api.create_envelope(account_id, envelope_definition=envelope_definition)
    return results

def sendMail(message_text, loan):
	print("inside send mail")
	creds = None
	tokenPath = os.path.join(APP_PATH, token_path)
	if os.path.exists(tokenPath):
	    with open(os.path.join(APP_PATH, token_path), "rb") as token:
	        creds = pickle.load(token)
	if not creds or not creds.valid:
	    if creds and creds.expired and creds.refresh_token:
	        creds.refresh(Request())
	    else:
	        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
	        creds = flow.run_local_server(port=0)
	    with open('token.pickle', 'wb') as token:
	        pickle.dump(creds, token)

	service = build('gmail', 'v1', credentials=creds)

	message = MIMEText(message_text)
	message['to'] = loan.borrower.email
	message['from'] = 'espproject2019@gmail.com'
	message['subject'] = 'Loan Approval'
	raw = base64.urlsafe_b64encode(message.as_bytes())
	raw = raw.decode()
	body = {'raw': raw}
	message = (service.users().messages().send(userId='me', body=body).execute())
	print(message)

def decisionTreeForLoanApproval(loan):
	print(loan.loanInfo.amount,loan.loanInfo.income ,loan.loanInfo.fico)
	csvPath = os.path.join(APP_PATH, csv_path)
	dataset = csvPath
	loanData = pd.read_csv(dataset)

	clf = tree.DecisionTreeClassifier()
	X = loanData.iloc[:, 0:3].values
	y = loanData.iloc[:, 3].values

	clf = clf.fit(X, y)
	dot_data = tree.export_graphviz(clf, feature_names=['LoanAmount', 'Income', 'Fico'], class_names=['0', '1'], filled=True, rounded=True)
	prediction = clf.predict([[loan.loanInfo.amount, loan.loanInfo.income, loan.loanInfo.fico]])
	print('Prediction ', prediction[0])
	if prediction == 0:
	    print("not Approved!")
	else:
	    print("Approved!")
	return str(prediction[0])

def decisionTreeForLoanApprovalRestAPI(loan):
	print(loan.loanInfo.amount,loan.loanInfo.income ,loan.loanInfo.fico)
	data=[[loan.loanInfo.amount, loan.loanInfo.income, loan.loanInfo.fico]]
	j_data = json.dumps(data)
	headers = {'content-type': 'application/json', 'Accept-Charset': 'UTF-8'}
	resp = requests.post(loan_model_api,data = json.dumps(data),headers=headers)
	prediction = resp.text
	print('Prediction ', prediction)
	if prediction == '0':
	    print("not Approved!")
	else:
	    print("Approved!")
	return prediction

def getChartData():
	approved = (LoanRequests
		.objects
		.all()
		.filter(dateApproved__gt=datetime.date(2019, 1, 3))
		.count())
	denied = LoanRequests.objects.all().filter(dateDenied__gt=datetime.date(2019, 1, 3)).count()
	inprocess = LoanRequests.objects.all().filter(dateApproved__isnull=True).filter(dateDenied__isnull=True).count()
	print(approved,denied, inprocess)
	return [approved, denied, inprocess]

def getApproved():
	approved = (LoanRequests
		.objects
		.all()
		.filter(dateApproved__gt=datetime.date(2019, 1, 3))
		)
	approveddata = []
	for loan in approved:
		approveddata.append([loan.loanInfo.fico, loan.loanInfo.income])
	return  approveddata

def getDenied():
	denied = LoanRequests.objects.all().filter(dateDenied__gt=datetime.date(2019, 1, 3))
	denieddata = []
	for loan in denied:
		denieddata.append([loan.loanInfo.fico, loan.loanInfo.income])
	return denieddata

def getNotProcessed():
	inprocess = LoanRequests.objects.all().filter(dateApproved__isnull=True).filter(dateDenied__isnull=True)
	inprocessdata = []
	for loan in inprocess:
		inprocessdata.append([loan.loanInfo.fico, loan.loanInfo.income])
	return inprocessdata
