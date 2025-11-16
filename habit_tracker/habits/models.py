from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Habit(models.Model):
    GOAL_TYPES = [
        ('boolean', 'Sí/No'),
        ('numeric', 'Numérico'),
        ('time', 'Tiempo'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    goal_type = models.CharField(max_length=10, choices=GOAL_TYPES, default='boolean')
    target = models.FloatField(default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def current_streak(self):
        logs = self.habitlog_set.order_by('-date')
        if not logs:
            return 0
            
        streak = 0
        today = timezone.now().date()
        current_date = today
        
        for log in logs:
            if log.date == current_date:
                if (self.goal_type == 'boolean' and log.value >= 1) or \
                   (self.goal_type in ['numeric', 'time'] and log.value >= self.target):
                    streak += 1
                    current_date -= timezone.timedelta(days=1)
                else:
                    break
            else:
                break
                
        return streak

class HabitLog(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    value = models.FloatField(default=0.0)
    
    class Meta:
        unique_together = ['habit', 'date']
    
    def __str__(self):
        return f"{self.habit.name} - {self.date}"