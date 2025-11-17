from django.contrib import admin
from .models import Habit, HabitLog

@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'goal_type', 'target', 'created_at', 'formatted_created_at']
    list_filter = ['goal_type', 'created_at']
    search_fields = ['name', 'user__username']
    
    def formatted_created_at(self, obj):
        return obj.formatted_created_at()
    formatted_created_at.short_description = 'Creado el'

@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    list_display = ['habit', 'date', 'value']
    list_filter = ['date']
    search_fields = ['habit__name']