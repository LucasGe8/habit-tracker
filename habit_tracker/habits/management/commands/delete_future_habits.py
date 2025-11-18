from django.utils import timezone
from habits.models import Habit, HabitLog

# Eliminar todos los logs futuros de todos los hábitos
today = timezone.localdate()
future_logs = HabitLog.objects.filter(date__gt=today)

print(f"Encontrados {future_logs.count()} logs en fechas futuras:")
for log in future_logs:
    print(f"  - {log.habit.name} - {log.date}: valor={log.value}")

# Eliminarlos
if future_logs.exists():
    future_logs.delete()
    print("¡Logs futuros eliminados!")
else:
    print("No hay logs futuros para eliminar")