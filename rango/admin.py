from django.contrib import admin
from django.contrib.auth.models import User
from models import Category, Page, UserProfile

# Register your models here.

class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'url')

admin.site.register(Category)
admin.site.register(Page, PageAdmin)
admin.site.register(UserProfile)

