# birthday/models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    birthdate = models.DateField(null=True, blank=True)
    first_name = models.CharField(max_length=150, blank=False, null=False)
    last_name = models.CharField(max_length=150, blank=False, null=False)

    def get_date(self):
        return self.birthdate.strftime("%b %d, %Y") if self.birthdate else "Not set"

    get_date.short_description = "Birthdate"


class Birthday(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="birthdates")
    celebrant = models.CharField(max_length=150, blank=False, null=False)
    company = models.CharField(max_length=150, blank=True, null=True)
    birthday = models.DateField(null=False, blank=False)

    def get_date(self):
        return self.birthday.strftime("%b %d, %Y")

    get_date.short_description = "Birthday"

    def __str__(self):
        return f"{self.celebrant}'s birthdate ({self.get_date()}) created by {self.owner.username}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'celebrant', 'birthday'],
                name='unique_owner_celebrant_birthday'
            )
        ]


class ReminderRun(models.Model):
    last_run = models.DateField(unique=True)  # Tracks the date of the last run

    @classmethod
    def should_run_today(cls):
        today = timezone.now().date()
        last_run = cls.objects.first()  # Get the latest run (should be only one due to unique)
        return not last_run or last_run.last_run < today

    @classmethod
    def mark_run(cls):
        today = timezone.now().date()
        cls.objects.update_or_create(last_run=today, defaults={'last_run': today})
