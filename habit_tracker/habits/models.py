from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

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
    
    def formatted_created_at(self):
        return self.created_at.strftime("%d/%m/%Y")
    
    def current_streak(self):
        logs = self.habitlog_set.filter(excluded=False).order_by('-date')  # Excluir logs marcados
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
    
    def is_completed_today(self):
        today = timezone.now().date()
        try:
            log = HabitLog.objects.get(habit=self, date=today)
            if log.excluded:  # Si está excluido, no cuenta como completado
                return False
            if self.goal_type == 'boolean':
                return log.value >= 1
            else:
                return log.value >= self.target
        except HabitLog.DoesNotExist:
            return False
    
    def hours_until_midnight(self):
        now = timezone.now()
        tomorrow = now + timedelta(days=1)
        midnight = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        time_left = midnight - now
        return int(time_left.total_seconds() // 3600), int((time_left.total_seconds() % 3600) // 60)

class HabitLog(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    value = models.FloatField(default=0.0)
    excluded = models.BooleanField(default=False)  # NUEVO: Para excluir días
    
    class Meta:
        unique_together = ['habit', 'date']
    
    def __str__(self):
        status = " (excluido)" if self.excluded else ""
        return f"{self.habit.name} - {self.date}{status}"