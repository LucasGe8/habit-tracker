from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
import json

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
    
    # Campos para el temporizador
    timer_state = models.CharField(max_length=20, default='stopped')  # stopped, running, paused
    timer_started_at = models.DateTimeField(null=True, blank=True)
    accumulated_time = models.FloatField(default=0.0)  # tiempo acumulado en segundos
    last_paused_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.name
    
    def formatted_created_at(self):
        return self.created_at.strftime("%d/%m/%Y")
    
    @property
    def current_streak(self):
        """
        Cuenta días consecutivos hacia atrás que cumplen la meta.
        Usa timezone.localdate() para coherencia con el resto de la app.
        Los días 'excluded' no rompen la racha (se saltan).
        """
        logs_manager = self.habitlog_set  # relacionado estándar
        if logs_manager is None:
            return 0

        def get_log_for(day):
            return logs_manager.filter(date=day).order_by('-id').first()

        count = 0
        today = timezone.localdate()

        # Si no hay log válido hoy (no excluido), empezar desde ayer; si hay solo excluded, el bucle lo saltará.
        if not logs_manager.filter(date=today).exists():
            current_day = today - timedelta(days=1)
        else:
            current_day = today

        while True:
            log = get_log_for(current_day)
            if not log:
                break

            if getattr(log, 'excluded', False):
                current_day -= timedelta(days=1)
                continue

            try:
                value = float(getattr(log, 'value', 0) or 0)
            except Exception:
                value = 0

            if self.goal_type == 'boolean':
                completed = value >= 1
            else:
                try:
                    target = float(self.target or 0)
                except Exception:
                    target = 0
                completed = value >= target

            if completed:
                count += 1
                current_day -= timedelta(days=1)
                continue
            break

        return count
    
    def is_completed_today(self):
        today = timezone.localdate()
        try:
            log = HabitLog.objects.get(habit=self, date=today)
            if log.excluded:
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
    
    # Métodos para el temporizador
    def get_current_elapsed_time(self):
        """Obtiene el tiempo transcurrido actual en segundos"""
        if self.timer_state == 'running' and self.timer_started_at:
            current_elapsed = (timezone.now() - self.timer_started_at).total_seconds()
            return self.accumulated_time + current_elapsed
        elif self.timer_state == 'paused':
            return self.accumulated_time
        else:
            return 0.0
    
    def get_remaining_time(self):
        """Obtiene el tiempo restante en segundos"""
        target_seconds = self.target * 60  # convertir minutos a segundos
        elapsed = self.get_current_elapsed_time()
        return max(0, target_seconds - elapsed)
    
    def is_timer_complete(self):
        """Verifica si el temporizador ha completado la meta"""
        return self.get_current_elapsed_time() >= (self.target * 60)
    
    def format_time(self, seconds):
        """Formatea segundos a MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    @property
    def formatted_target_time(self):
        """Tiempo objetivo formateado (MM:SS) basado en self.target (minutos)"""
        try:
            total_seconds = int(self.target * 60)
        except Exception:
            total_seconds = 0
        return self.format_time(total_seconds)

class HabitLog(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    value = models.FloatField(default=0.0)
    excluded = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['habit', 'date']
    
    def __str__(self):
        status = " (excluido)" if self.excluded else ""
        return f"{self.habit.name} - {self.date}{status}"