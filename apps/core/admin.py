from django.contrib import admin
from .models import SchoolUnit

@admin.register(SchoolUnit)
class SchoolUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone_number', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'email')
    ordering = ('name',)
