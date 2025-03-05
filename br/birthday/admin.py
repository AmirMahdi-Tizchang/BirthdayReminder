from django.contrib import admin
from .models import User, Birthday, ReminderRun


class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "first_name", "last_name", "email", "last_login")


admin.site.register(User, UserAdmin)
admin.site.register(Birthday)
admin.site.register(ReminderRun)
