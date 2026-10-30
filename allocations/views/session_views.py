"""Views for starting and ending a session: logging in and logging out."""

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from allocations.forms import LogInForm


def home(request):
    """Show the home page, or the dashboard if the user is logged in."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')


def log_in(request):
    """Show the log in form and log the user in."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LogInForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    else:
        form = LogInForm(request)
    return render(request, 'log_in.html', {'form': form})


@require_POST
def log_out(request):
    """Log the user out. Only POST requests are allowed (see base.html)."""
    logout(request)
    return redirect('home')


@login_required
def dashboard(request):
    """Show the page users see after logging in."""
    return render(request, 'dashboard.html')
