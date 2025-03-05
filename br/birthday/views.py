import re
from datetime import datetime
from django.urls import reverse
from django.utils import timezone
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from .models import User, Birthday, ReminderRun
from django.core.management import call_command
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout


MONTHS = [
    ("01", "January"),
    ("02", "February"),
    ("03", "March"),
    ("04", "April"),
    ("05", "May"),
    ("06", "June"),
    ("07", "July"),
    ("08", "August"),
    ("09", "September"),
    ("10", "October"),
    ("11", "November"),
    ("12", "December"),
]


def index(request):
    today = datetime.today()
    birthdates = Birthday.objects.filter(birthday__month=today.month, birthday__day=today.day)
    uniques = {}

    for b in birthdates:
        key = (b.celebrant, b.birthday)
        if key not in uniques:
            b.age = today.year - b.birthday.year - ((today.month, today.day) < (b.birthday.month, b.birthday.day))
            uniques[key] = b

    # Trigger reminders if not run today
    if ReminderRun.should_run_today():
        call_command('send_birthday_reminders')

    return render(request, "birthday/index.html", {
        "today": today,
        "birthdates": list(uniques.values())
    })


def about(request):
    return render(request, "birthday/about.html")


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            next_url = request.POST.get("next", request.GET.get("next", reverse("index")))
            return redirect(next_url)
        else:
            return render(request, "birthday/login.html", {
                "status": "danger",
                "message": "Invalid username and/or password.",
                "title": "Declined"
            })
    else:
        next_url = request.GET.get("next", "")
        return render(request, "birthday/login.html", {"next": next_url})


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def is_valid(email):
    if re.search(r"^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$", email, re.IGNORECASE):
        return True
    return False


def register(request):
    if request.method == "POST":
        username = request.POST["username"].strip()
        email = request.POST["email"].strip()
        first_name = request.POST["first_name"].strip().title()
        last_name = request.POST["last_name"].strip().title()
        birthdate = request.POST["birthdate"].strip()
        password = request.POST["password"].strip()
        confirmation = request.POST["confirmation"].strip()

        # Check if all required fields are provided
        required_fields = {
            "Username": username,
            "Email": email,
            "First Name": first_name,
            "Last Name": last_name,
            "Password": password,
            "Confirm Password": confirmation
        }
        for key, value in required_fields.items():
            if not value:
                return render(request, "birthday/register.html", {
                    "status": "warning",
                    "message": f"{key} is required.",
                    "title": "Missing Information"
                })

        # Ensure password matches confirmation
        if password != confirmation:
            return render(request, "birthday/register.html", {
                "status": "warning",
                "message": "Passwords must match.",
                "title": "Warning"
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                birthdate=birthdate if birthdate else None
            )
            user.save()

            if birthdate:
                try:
                    birthday = Birthday.objects.create(
                        owner=user,
                        celebrant=f"{first_name} {last_name}",
                        birthday=birthdate,
                        company="itself"
                    )
                    birthday.save()
                except IntegrityError:
                    return render(request, "birthday/register.html", {
                        "status": "danger",
                        "message": "An error occurred during registration.",
                        "title": "Declined"
                    })

        except IntegrityError:
            if User.objects.filter(username=username).exists():
                message = "Username already taken."
            elif User.objects.filter(email=email).exists():
                message = "Email already in use."
            elif not is_valid(email):
                message = "Invalid email address."
            else:
                message = "An error occurred during registration."
            return render(request, "birthday/register.html", {
                "status": "danger",
                "message": message,
                "title": "Declined"
            })

        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "birthday/register.html")


def is_leap_year(year):
    """Check if a year is a leap year."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


@login_required
def add(request):
    # Common context data
    context = {
        "days": range(1, 32),
        "months": MONTHS,
        "years": range(timezone.now().year - 100, timezone.now().year + 1)
    }

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip().title()
        last_name = request.POST.get("last_name", "").strip().title()
        company = request.POST.get("company", "").strip()
        day = request.POST.get("birthdate_day", "").strip()
        month = request.POST.get("birthdate_month", "").strip()
        year = request.POST.get("birthdate_year", "").strip()

        # Check required fields
        required_fields = {
            "First Name": first_name,
            "Last Name": last_name,
            "Birthdate Day": day,
            "Birthdate Month": month,
            "Birthdate Year": year
        }
        for key, value in required_fields.items():
            if not value:
                context.update({
                    "status": "danger",
                    "message": f"{key} is required.",
                    "title": "Missing Information"
                })
                return render(request, "birthday/add.html", context)

        # Validate birthdate
        try:
            day = int(day)
            year = int(year)
            max_days = {
                "01": 31, "02": 29 if is_leap_year(year) else 28, "03": 31,
                "04": 30, "05": 31, "06": 30, "07": 31, "08": 31,
                "09": 30, "10": 31, "11": 30, "12": 31
            }.get(month)

            if not max_days or day < 1 or day > max_days:
                raise ValueError(f"Invalid day ({day}) for {month}/{year}")

            birthdate = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d").date()
            if birthdate > timezone.now().date():
                raise ValueError("Birthdate cannot be in the future")

        except ValueError as e:
            context.update({
                "status": "warning",
                "message": str(e) if "Invalid" in str(e) else "Invalid birthdate format",
                "title": "Invalid Date"
            })
            return render(request, "birthday/add.html", context)

        # Create Birthday object
        celebrant = f"{first_name} {last_name}"
        try:
            Birthday.objects.create(
                owner=request.user,
                celebrant=celebrant,
                company=company,
                birthday=birthdate
            )
            # No need for .save() - create() already saves
            return redirect("index")
        except IntegrityError:
            context.update({
                "status": "info",
                "message": "You’ve already added this celebrant with this birthday.",
                "title": "Duplicate Entry"
            })
            return render(request, "birthday/add.html", context)

    return render(request, "birthday/add.html", context)


@login_required
def remove(request):
    if request.method == "POST":
        birthdate_id = request.POST.get("birthdate_id")
        if birthdate_id:
            try:
                birthdate = Birthday.objects.get(id=birthdate_id, owner=request.user)
                birthdate.delete()
            except Birthday.DoesNotExist:
                # Silent fail if birthdate doesn’t exist or isn’t owned by user
                pass
        return redirect("remove")

    # GET request: Show user's birthdates
    birthdates = Birthday.objects.filter(owner=request.user).order_by('birthday')
    return render(request, "birthday/remove.html", {"birthdates": birthdates})
