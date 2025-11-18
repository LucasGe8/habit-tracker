from zoneinfo import ZoneInfo
from datetime import datetime, time
from django.db import transaction
from habits.models import HabitLog

# CONFIG
local_tz = ZoneInfo('America/Asuncion')
utc_tz = ZoneInfo('UTC')
DRY_RUN = True  # True = solo PREVIEW, False = aplicar cambios

def main():
    updated_logs = 0
    merged = 0
    merged_details = []

    print("Starting fix_habitlog_dates.py")
    print("DRY_RUN =", DRY_RUN)
    with transaction.atomic():
        for log in HabitLog.objects.select_for_update().order_by('id'):
            stored = log.date  # date field stored as YYYY-MM-DD
            mid_utc = datetime.combine(stored, time(0, 0, 0)).replace(tzinfo=utc_tz)
            new_date = mid_utc.astimezone(local_tz).date()
            if new_date == stored:
                continue

            # Si ya existe otro log para el mismo habit+new_date -> fusionar conservadoramente
            other = HabitLog.objects.filter(habit=log.habit, date=new_date).exclude(pk=log.pk).first()
            if other:
                print(f"Conflict: log {log.id} (habit {log.habit_id}) {stored} -> {new_date}  (keeps {other.id})")
                if DRY_RUN:
                    merged += 1
                    continue
                # fusionar sumando valores (útil para hábitos tipo 'time')
                try:
                    other_val = float(other.value or 0)
                except Exception:
                    other_val = 0.0
                try:
                    log_val = float(log.value or 0)
                except Exception:
                    log_val = 0.0

                other.value = other_val + log_val
                other.excluded = bool(other.excluded) or bool(log.excluded)
                other.save(update_fields=['value', 'excluded'])
                merged_details.append((log.id, log.habit_id, stored, new_date, other.id))
                if not DRY_RUN:
                    log.delete()
                merged += 1
                continue

            # No hay conflicto -> actualizar la fecha
            print(f"Update: log {log.id} (habit {log.habit_id}) {stored} -> {new_date}")
            if not DRY_RUN:
                log.date = new_date
                log.save(update_fields=['date'])
            updated_logs += 1

    print(f"Done. Updated habit logs: {updated_logs}, Merged duplicates: {merged}")
    if merged_details:
        print("Merged details (deleted_log_id, habit_id, old_date, new_date, kept_log_id):")
        for d in merged_details:
            print(d)

if __name__ == '__main__':
    main()