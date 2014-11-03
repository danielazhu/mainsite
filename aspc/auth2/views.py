from urllib import urlencode
import urlparse
from django.http import HttpResponseRedirect, HttpResponseNotAllowed
from aspc import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import render
from django.contrib.auth.forms import AuthenticationForm

__all__ = ['guest_login', 'login', 'logout']

# On GET, renders a login form for guest accounts (i.e. users that are backed locally, not in the 5C CAS server)
# On POST, validates the login form, authenticates the user, and logins him in
def guest_login(request):
	if request.method == 'GET':
		form = AuthenticationForm()
		return render(request, 'auth2/guest_login.html', {'form': form})

	elif request.method == 'POST':
		from django.contrib import auth
		form = AuthenticationForm(data=request.POST)

		if form.is_valid():
			user = auth.authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])

			if user is not None:
				auth.login(request, user)
				return HttpResponseRedirect('/')
			else:
				return render(request, 'auth2/guest_login.html', {'form': form})
		else:
			return render(request, 'auth2/guest_login.html', {'form': form})

	else:
		return HttpResponseNotAllowed(['GET', 'POST'])

# Endpoint has two functions:
# 1) Forwards to CAS login URL upon first login
# 2) Validates a CAS ticket upon receipt from the CAS server
def login(request, next_page=None):
	if request.method == 'GET':
		next_page = next_page or _next_page_url(request)

		# If the user is already authenticated, simply redirect to the next_page
		if request.user.is_authenticated():
			return HttpResponseRedirect(next_page)

		ticket = request.GET.get('ticket')
		service_url = 'https://' + request.get_host() + request.path  # Required to authenticate over SSL

		# If there is already a ticket, perform validation on it
		if ticket:
			from django.contrib import auth
			user = auth.authenticate(ticket=ticket, service=service_url)

			if user is not None:
				# Ticket successfully validated and user data retrieved - perform login
				auth.login(request, user)
				return HttpResponseRedirect('https://staging.aspc.pomona.edu?' + user.username)
			else:
				# Some error in the ticket validation - try the login again
				return HttpResponseRedirect(_login_url(service_url))
		# Otherwise it is the first login - redirect to the CAS login URL
		else:
			return HttpResponseRedirect(_login_url(service_url))
	else:
		return HttpResponseNotAllowed(['GET'])

# Performs user logout
def logout(request, next_page=None):
	if request.method == 'GET':
		from django.contrib.auth import logout
		next_page = next_page or _next_page_url(request)
		is_guest = request.user.has_usable_password()

		# First logout the local Django user
		logout(request)

		# If the user is a guest (i.e. not backed by 5C CAS, but just in our local database) we're done
		if is_guest:
			return HttpResponseRedirect('/')
		# Otherwise, then perform a redirection to the CAS server to complete logout there
		else:
			return HttpResponseRedirect(_logout_url())
	else:
		return HttpResponseNotAllowed(['GET'])

# Redirects to referring page, or to the homepage if no referrer is set.
def _next_page_url(request):
	next_page = request.GET.get(REDIRECT_FIELD_NAME) or ''
	host = request.get_host()
	prefix = (('http://', 'https://')[request.is_secure()] + host)
	if next_page.startswith(prefix):
		next_page = next[len(prefix):]
	return next_page

# Builds CAS login URL
def _login_url(service_url):
	params = {
		'service': service_url
	}

	return urlparse.urljoin(settings.CAS_SETTINGS['SERVER_URL'], 'login') + '?' + urlencode(params)

# Builds CAS logout URL
def _logout_url():
	return urlparse.urljoin(settings.CAS_SETTINGS['SERVER_URL'], 'logout')