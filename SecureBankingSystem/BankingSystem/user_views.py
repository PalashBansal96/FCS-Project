from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404

from BankingSystem.models import Transactions, Payments
from BankingSystem.utils import do_get, custom_redirect, BankingException
from django.contrib.auth import authenticate, login


# External user dashboard
@login_required()
@permission_required('BankingSystem.user_operations', raise_exception=True)
def dashboard_external(request):
	print request.user
	fields = {
		'username': request.user.username,
		'redirect_info': do_get(request.GET, 'info'),  # Like already logged in
		'redirect_success': do_get(request.GET, 'success'),  # Like login successful
		'redirect_error': do_get(request.GET, 'error'),  # Generic site error
		'error': '',
		'has_perm_user_operations': request.user.has_perm('BankingSystem.user_operations'),
		'has_perm_create_payments': request.user.has_perm('BankingSystem.create_payments'),  # check if user is Company
		'accounts': request.user.profile.account_set.all()
	}

	return render(request, 'dashboard_external_user.html', fields)


# Transfer money from one account to another
@login_required()
@permission_required('BankingSystem.user_operations', raise_exception=True)
def make_transactions(request):
	fields = {
		'username': request.user.username,
		'error': '',
		'has_perm_view_critical_transactions': request.user.has_perm('BankingSystem.view_critical_transactions'),
		'has_perm_create_payments': request.user.has_perm('BankingSystem.create_payments'),
		'accounts': request.user.profile.account_set.all()
	}
	if request.method != 'POST':
		return render(request, 'make_transactions.html', fields)
	sender_account_number = do_get(request.POST, 'sender_account_number')
	receiver_account_number = do_get(request.POST, 'receiver_account_number')
	amount = do_get(request.POST, 'amount')
	try:
		transaction = Transactions.create(Transactions.TYPE_TRANSACTION, request.user, sender_account_number,
		                                  receiver_account_number, amount)
	except BankingException as e:
		fields['error'] = e.message
		return render(request, 'make_transactions.html', fields)
	return redirect("transaction_confirmation", transaction_id=transaction.id)


# Get OTP from the user, verifies and sends transaction for approval
def transaction_confirmation(request, transaction_id):
	transaction = get_object_or_404(Transactions, pk=transaction_id)
	fields = {
		'authentication_error': '',
		'username': request.user.username,
		'transaction_id': transaction.id,
		'error': '',
		'has_perm_user_operations': request.user.has_perm('BankingSystem.view_user_operations'),
		'has_perm_create_payments': request.user.has_perm('BankingSystem.create_payments'),
	}

	if request.method != 'POST':
		return render(request, 'transaction_confirmation_otp.html', fields)
	otp = do_get(request.POST, 'otp')
	try:
		transaction.verify_otp(otp)
		if not transaction.is_cash and transaction.amount < Transactions.CRITICAL_LIMIT:
			transaction.process_transaction()
			return custom_redirect("dashboard", success="Successfully processed transaction")
		else:
			return custom_redirect("dashboard", info='Transaction will be processed after approval from ' + str(
				transaction.employee))
	except BankingException as e:
		fields['error'] = e.message
		return render(request, 'transaction_confirmation_otp.html', fields)


# Show complete transaction history
@login_required()
@permission_required('BankingSystem.user_operations', raise_exception=True)
def passbook(request):
	accounts = request.user.profile.account_set.all()
	account_transactions = []
	for i in accounts:
		account_transactions.extend(map(lambda x: str(x).split(), list(i.from_account.all())))
		account_transactions.extend(map(lambda x: str(x).split(), list(i.to_account.all())))
	account_transactions.sort(cmp=lambda x, y: int(y[0]) - int(x[0]))
	fields = {
		'username': request.user.username,
		'error': '',
		'account_transactions': account_transactions,
		'has_perm_user_operations': request.user.has_perm('BankingSystem.user_operations'),
		'has_perm_create_payments': request.user.has_perm('BankingSystem.create_payments'),
	}

	return render(request, 'passbook.html', fields)


# Doing transaction for cash transactions
@login_required()
@permission_required('BankingSystem.user_operations', raise_exception=True)
def debit_credit(request):
	fields = {
		'accounts': request.user.profile.account_set.all(),
		'username': request.user.username,
		'error': '',
	}
	if request.method != 'POST':
		return render(request, 'debit_credit.html', fields)

	account = do_get(request.POST, 'account')
	transaction_type = do_get(request.POST, 'debit_or_credit')  # Whether Debit or Credit transaction
	pref_employee = do_get(request.POST, 'preferred_employee')
	amount = do_get(request.POST, 'amount')
	try:
		if transaction_type == "debit":
			transaction = Transactions.create(Transactions.TYPE_DEBIT, request.user, account, None, amount,
			                                  pref_employee)
		elif transaction_type == "credit":
			transaction = Transactions.create(Transactions.TYPE_CREDIT, request.user, None, account, amount,
			                                  pref_employee)
		else:
			raise BankingException('Invalid request')
	except BankingException as e:
		fields['error'] = e.message
		return render(request, 'debit_credit.html', fields)
	return redirect("transaction_confirmation", transaction_id=transaction.id)


@login_required()
@permission_required('BankingSystem.create_payments', raise_exception=True)
def create_payment(request):
	fields = {
		'error': '',
		'username': request.user.username,
		'has_perm_user_operations': request.user.has_perm('BankingSystem.user_operations'),
		'has_perm_create_payments': request.user.has_perm('BankingSystem.create_payments'),
	}
	if request.method != 'POST':
		return render(request, 'create_payment.html', fields)
	payee_account = do_get(request.POST, 'payee_account')
	amount = do_get(request.POST, 'amount')
	try:
		Payments.create(request.user, payee_account, amount)
	except BankingException as e:
		fields['error'] = e.message
		return render(request, 'create_payment.html', fields)
	return custom_redirect('dashboard', success="Payment requested from the user.")


@login_required()
@permission_required('BankingSystem.user_operations')
def approve_payments_for_users(request):
	payments = []
	for account in request.user.profile.account_set.all():
		payments.extend(list(account.payment_user.all()))
	fields = {
		'redirect_info': do_get(request.GET, 'info'),  # Like already logged in
		'redirect_success': do_get(request.GET, 'success'),  # Like login successful
		'redirect_error': do_get(request.GET, 'error'),  # Generic site error
		'payments': payments,
		'username': request.user.username,
		'has_perm_user_operations': request.user.has_perm('BankingSystem.user_operations'),
	}
	return render(request, 'approve_payments_for_users.html', fields)


@login_required()
@permission_required('BankingSystem.user_operations')
def approve_payment_id(request, payment_id):
	payment = get_object_or_404(Payments, pk=payment_id)
	try:
		payment.approve(request.user)
		if payment.transaction.status == 'P':
			return custom_redirect('user_payments', success="Payment processed")
		if payment.transaction.status == 'A':
			return custom_redirect('user_payments', info="Payment is sent for approval")
	except BankingException as e:
		return custom_redirect('user_payments', error=e.message)
	return custom_redirect('user_payments', error="Unknown error")


@login_required()
@permission_required('BankingSystem.user_operations')
def reject_payment_id(request, payment_id):
	payment = get_object_or_404(Payments, pk=payment_id)
	try:
		payment.reject(request.user)
		if payment.transaction.status == 'R':
			return custom_redirect('user_payments', success="Payment rejected")
	except BankingException as e:
		return custom_redirect('user_payments', error=e.message)
	return custom_redirect('user_payments', error="Unknown error")


@login_required()
@permission_required('BankingSystem.user_operations', raise_exception=True)
def reset_2fa(request):
	fields = {
		'username': request.user.username,
		'redirect_info': do_get(request.GET, 'info'),  # Like already logged in
		'redirect_success': do_get(request.GET, 'success'),  # Like login successful
		'redirect_error': do_get(request.GET, 'error'),  # Generic site error
		'error': '',
		'token_url': request.user.profile.regenerate_totp_seed()
	}

	return render(request, 'reset_2fa.html', fields)


@login_required()
@permission_required('BankingSystem.user_operations')
def technical_accounts_access(request):
	fields = {
		'error': "",
		'username': request.user.username,
		'has_perm_user_operations': request.user.has_perm('BankingSystem.user_operations'),
	}
	if request.method != 'POST':
		return render(request, 'technical_accounts_access.html', fields)
	employee_username = do_get(request.POST, 'employee_username')

	try:
		employee = User.objects.filter(groups__name='Employees').get(username=employee_username)
	except:
		fields['error'] = 'No such employee.'
		return render(request, 'technical_accounts_access.html', fields)
	if employee is None:
		fields['error'] = 'No such employee'
		return render(request, 'technical_accounts_access.html', fields)
	request.user.profile.ticket_employee = employee.profile
	request.user.profile.save()
	return custom_redirect('dashboard', success="Employee given access to your account.")
