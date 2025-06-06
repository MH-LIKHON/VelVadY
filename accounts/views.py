from .models import CustomUser
from django.contrib import messages
from django.urls import reverse_lazy
from products.models import Purchase
from django.views.generic import TemplateView
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import render, redirect, get_object_or_404
from .forms import ProfileUpdateForm, CustomUserRegistrationForm





# =======================================================
# LOGIN VIEW
# =======================================================

# Handles login views for users
def login_view(request):
    """
    Handles the login functionality for users. Authenticates user credentials,
    sets session messages, and redirects based on login status.
    """

    # If user is already authenticated, redirect to dashboard
    if request.user.is_authenticated:
        return redirect("dashboard")

    # Displays a message if the user was redirected from a Stripe checkout attempt
    if 'next' in request.GET and 'checkout-session' in request.GET['next']:
        messages.info(request, "Please log in or create an account to continue with your purchase.")

    # Shows account creation success message if flagged in session
    if request.session.pop('new_account', None):
        messages.success(request, "Your account has been created. You can now log in.")

    # Handle login form submission
    if request.method == "POST":
        # Extract submitted email and password
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Attempt to authenticate user with provided credentials
        user = authenticate(request, username=email, password=password)

        if user is not None:
            # Log the user in and show welcome message
            login(request, user)
            messages.success(request, "Welcome back!")

            # Safely handle redirection based on original destination
            next_url = request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                # Block redirecting to sensitive POST-only Stripe routes
                if not next_url.startswith("/products/create-checkout-session/"):
                    return redirect(next_url)

            # Default fallback if no safe redirect target
            return redirect("dashboard")
        else:
            # If login fails, show error
            messages.error(request, "Invalid email or password. Please try again.")

    # Display the login form
    return render(request, 'accounts/login.html')





# =======================================================
# REGISTER VIEW
# =======================================================

# Handles new user registration
def register_view(request):
    """
    Processes the registration form, validates user input,
    and creates a new user account if all fields are valid.
    """

    # Prevent logged-in users from accessing the registration page
    if request.user.is_authenticated:
        return redirect("dashboard")

    # Remove any existing new account flag from session
    request.session.pop('new_account', None)

    if request.method == "POST":
        # Populate the form with submitted POST data
        form = CustomUserRegistrationForm(request.POST)

        # Validate form input
        if form.is_valid():
            # Save the user and flag session for login success message
            form.save()
            request.session['new_account'] = True
            return redirect("login")
        else:
            # Show error message if form is invalid
            messages.error(request, "Please correct the errors below.")
    else:
        # Initialise an empty registration form on GET request
        form = CustomUserRegistrationForm()

    # Display Registration Page
    return render(request, 'accounts/register.html', {"form": form})





# =======================================================
# LOGOUT VIEW
# =======================================================

# Logs the user out and clears session
def logout_view(request):
    """
    Logs out the currently authenticated user, clears the session,
    and redirects them to the home page with a success message.
    """

    # Terminate the user's session and log them out
    logout(request)

    # Display a logout confirmation message
    messages.success(request, "You have been logged out successfully.")

    # Redirect to the home page
    return redirect("home")





# =======================================================
# DASHBOARD VIEW
# =======================================================

# Handles user dashboard and displays purchase history
class DashboardView(LoginRequiredMixin, TemplateView):
    # Specifies the HTML template to render for the dashboard
    template_name = 'accounts/dashboard.html'

    # Adds user-specific context data including purchase records
    def get_context_data(self, **kwargs):
        """
        Extends the default dashboard context to include actual purchase history
        alongside placeholder values for subscription and credit tracking.
        """
        # Get the base context from the parent TemplateView
        context = super().get_context_data(**kwargs)

        # Query all purchases made by the currently logged-in user
        user_purchases = Purchase.objects.filter(user=self.request.user).select_related('service')

        # Add real purchases and dashboard mock data to context
        context['purchases'] = user_purchases
        context['active_subscriptions'] = 2
        context['last_order_date'] = '28 May 2025'
        context['remaining_credits'] = 18

        return context





# =======================================================
# PROFILE VIEW
# =======================================================

# Shows current user's profile information
@login_required
def profile_view(request):
    """
    Displays the logged-in user's profile page.
    The view is protected to ensure only authenticated users can access it.
    """
    return render(request, "accounts/profile.html")

# Handles profile update form submission and display
@login_required
def profile_update_view(request):
    """
    Handles both the display and processing of the profile update form.
    Loads the user's current information and updates it if valid data is submitted.
    """
    # Retrieves the currently logged-in user's object
    user = get_object_or_404(CustomUser, pk=request.user.pk)

    if request.method == 'POST':
        # Binds form data to the user instance for validation and saving
        form = ProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Pre-fills the form with the user's existing information for editing
        form = ProfileUpdateForm(instance=user)

    # Renders the profile update form page with the current form state
    return render(request, 'accounts/profile_update.html', {'form': form})





# =======================================================
# PASSWORD CHANGE VIEW
# =======================================================

# Handles password update for logged-in users
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

# Password change views
class CustomPasswordChangeView(PasswordChangeView):
    """
    Displays the password change form to authenticated users and handles validation.
    Uses a custom template and redirects to a confirmation page upon success.
    """

    template_name = 'accounts/password_change.html'

    # Redirects user after successful password change
    success_url = reverse_lazy('password_change_done')

    def form_valid(self, form):
        """
        Adds a success message once the password has been changed successfully.
        """
        messages.success(self.request, "Your password has been changed successfully.")
        return super().form_valid(form)