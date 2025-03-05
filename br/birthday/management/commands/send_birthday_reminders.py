# birthday/management/commands/send_birthday_reminders.py
import smtplib
from datetime import timedelta
from django.utils import timezone
from email.message import EmailMessage
from birthday.models import Birthday, ReminderRun
from django.core.management.base import BaseCommand


def email_alert(messages):
    """
    Send multiple email messages using a single SMTP connection.

    Args:
        messages (list): List of dicts with 'subject', 'body', and 'to' keys

    Returns:
        int: Number of emails sent successfully
    """
    if not messages:
        print("No messages to send")
        return 0

    sent_count = 0
    try:
        # Setting up Gmail account
        username = YOUR_EMIAL_ADDRESS
        password = YOUR_API_KEY

        # Create SMTP connection
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(username, password)

        # Send each message
        for message in messages:
            try:
                msg = EmailMessage()
                msg.set_content(message['body'])
                msg['subject'] = message['subject']
                msg['to'] = message['to']
                msg['from'] = username
                server.send_message(msg)
                print(f"Email sent successfully to {message['to']}")
                sent_count += 1
            except Exception as e:
                print(f"Failed to send email to {message['to']}: {e}")

        # Close connection
        server.quit()

    except Exception as e:
        print(f"SMTP connection error: {e}")

    return sent_count


class Command(BaseCommand):
    help = 'Sends email reminders for upcoming birthdays'

    def handle(self, *args, **options):
        # Check if it should run today
        if not ReminderRun.should_run_today():
            self.stdout.write(self.style.WARNING('Reminders already sent today'))
            return

        messages = []
        today = timezone.now()
        upcoming = today + timedelta(days=7)
        birthdays = Birthday.objects.filter(
            birthday__month__in=[today.month, upcoming.month],
            birthday__day__in=[today.day, upcoming.day]
        ).select_related('owner')

        if not birthdays:
            self.stdout.write(self.style.SUCCESS('No birthdays to remind today'))
            ReminderRun.mark_run()
            return

        for b in birthdays:
            if b.owner.email:  # Check for valid email
                if b.company == "itself":
                    subject = "Happy Birthday"
                    body = f"Happy Birthday, {b.celebrant}! Wishing you a fantastic day filled with joy and celebration!"
                elif b.birthday.month == today.month and b.birthday.day == today.day:
                    subject = f"{b.celebrant}'s Birthday"
                    body = f"Woohoo! Your {b.company}, {b.celebrant}’s birthday is TODAY - party time!"
                else:
                    subject = "Upcoming Birthday"
                    body = f"Get ready! Your {b.company}, {b.celebrant}'s birthday is coming up on {b.get_date()} - time to plan something special!"

                messages.append({
                    "subject": subject,
                    "to": b.owner.email,
                    "body": body
                })

        sent_count = email_alert(messages)

        # Mark as run today
        ReminderRun.mark_run()
        self.stdout.write(self.style.SUCCESS(f'Sent {sent_count} reminders'))
