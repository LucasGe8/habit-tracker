# habits/management/commands/check_habits.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from habits.models import Habit, HabitLog
from django.db.models import Count

class Command(BaseCommand):
    help = 'Verifica y corrige problemas en los hábitos'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Corregir automáticamente los duplicados',
        )
    
    def handle(self, *args, **options):
        self.stdout.write("=== VERIFICANDO HÁBITOS ===")
        
        for habit in Habit.objects.all():
            self.stdout.write(f"\nHábito: {habit.name}")
            
            # Buscar duplicados
            dates_with_duplicates = HabitLog.objects.filter(habit=habit).values('date').annotate(
                count=Count('id')
            ).filter(count__gt=1)
            
            if dates_with_duplicates:
                self.stdout.write(self.style.WARNING("¡ENCONTRADOS DUPLICADOS!"))
                for date_info in dates_with_duplicates:
                    date = date_info['date']
                    duplicates = HabitLog.objects.filter(habit=habit, date=date).order_by('-id')
                    self.stdout.write(f"  Fecha {date}: {duplicates.count()} registros")
                    
                    if options['fix']:
                        for duplicate in duplicates[1:]:
                            duplicate.delete()
                            self.stdout.write(f"    Eliminado registro duplicado")
            else:
                self.stdout.write(self.style.SUCCESS("No hay duplicados"))