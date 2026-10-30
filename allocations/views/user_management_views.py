"""Views for managing users: a user's own account, and all users (superusers only)."""

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from allocations.forms import PasswordForm, ProfileForm, UserCreateForm, UserUpdateForm
from allocations.models import User

USERS_PER_PAGE = 10


def superuser_required(view_function):
    """Decorator for views that only superusers may use.

    Users who are not logged in are sent to the log in page. Users who are
    logged in, but are not superusers, get a "403 Forbidden" error.
    """

    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_function(request, *args, **kwargs)

    return wrapper


# The logged in user's own account

@login_required
def profile(request):
    """Let the logged in user edit their own profile."""
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('dashboard')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'profile.html', {'form': form})


@login_required
def password(request):
    """Let the logged in user change their own password."""
    if request.method == 'POST':
        form = PasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Changing the password would otherwise log the user out.
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed.')
            return redirect('dashboard')
    else:
        form = PasswordForm(request.user)
    return render(request, 'password.html', {'form': form})


# Managing users (superusers only)

@superuser_required
def user_list(request):
    """Show a list of all users, a page at a time."""
    paginator = Paginator(User.objects.all(), USERS_PER_PAGE)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'user_list.html', {'page': page})


@superuser_required
def user_detail(request, user_id):
    """Show the details of a single user."""
    # Templates already use the name "user" for the logged in user,
    # so the user being shown is called "shown_user" instead.
    shown_user = get_object_or_404(User, id=user_id)
    return render(request, 'user_detail.html', {'shown_user': shown_user})


@superuser_required
def user_create(request):
    """Create a new user."""
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            messages.success(request, f'User {new_user.username} has been created.')
            return redirect('user_detail', user_id=new_user.id)
    else:
        form = UserCreateForm()
    return render(request, 'user_form.html', {'form': form, 'title': 'Create user'})


@superuser_required
def user_update(request, user_id):
    """Update the details of an existing user."""
    shown_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=shown_user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User {shown_user.username} has been updated.')
            return redirect('user_detail', user_id=shown_user.id)
    else:
        form = UserUpdateForm(instance=shown_user)
    return render(request, 'user_form.html', {'form': form, 'title': 'Update user'})


@superuser_required
def user_delete(request, user_id):
    """Ask for confirmation, then delete a user."""
    shown_user = get_object_or_404(User, id=user_id)
    if shown_user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('user_detail', user_id=shown_user.id)
    if request.method == 'POST':
        shown_user.delete()
        messages.success(request, f'User {shown_user.username} has been deleted.')
        return redirect('user_list')
    return render(request, 'user_confirm_delete.html', {'shown_user': shown_user})
