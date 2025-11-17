from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.utils import timezone
from django.contrib import messages
from .models import Habit, HabitLog
from .forms import HabitForm, UserRegisterForm

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '¡Cuenta creada exitosamente! Bienvenido/a.')
            return redirect('habit_list')
    else:
        form = UserRegisterForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def habit_list(request):
    habits = Habit.objects.filter(user=request.user)
    today = timezone.now().date()
    
    for habit in habits:
        try:
            habit.today_log = HabitLog.objects.get(habit=habit, date=today)
        except HabitLog.DoesNotExist:
            habit.today_log = None
    
    return render(request, 'habits/habit_list.html', {'habits': habits, 'today': today})

@login_required
def habit_create(request):
    if request.method == 'POST':
        form = HabitForm(request.POST)
        if form.is_valid():
            habit = form.save(commit=False)
            habit.user = request.user
            habit.save()
            messages.success(request, 'Hábito creado exitosamente!')
            return redirect('habit_list')
    else:
        form = HabitForm()
    return render(request, 'habits/habit_form.html', {'form': form})

@login_required
def habit_edit(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    if request.method == 'POST':
        form = HabitForm(request.POST, instance=habit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hábito actualizado exitosamente!')
            return redirect('habit_list')
    else:
        form = HabitForm(instance=habit)
    return render(request, 'habits/habit_form.html', {'form': form})

@login_required
def habit_delete(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    if request.method == 'POST':
        habit.delete()
        messages.success(request, 'Hábito eliminado exitosamente!')
        return redirect('habit_list')
    return render(request, 'habits/habit_confirm_delete.html', {'habit': habit})

@login_required
def log_habit(request, habit_id):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    today = timezone.now().date()
    
    if request.method == 'POST':
        value = request.POST.get('value', 1.0)
        
        if habit.goal_type == 'boolean':
            value = 1.0 if value else 0.0
        else:
            try:
                value = float(value)
            except ValueError:
                value = 0.0
        
        # Si se envía un valor positivo, quitar la exclusión
        log, created = HabitLog.objects.update_or_create(
            habit=habit,
            date=today,
            defaults={'value': value, 'excluded': False}  # Quitar exclusión
        )
        
        if value > 0:
            messages.success(request, f'Registro guardado para {habit.name}!')
        else:
            messages.info(request, f'Día reactivado para {habit.name}.')
    
    return redirect('habit_list')

@login_required
def statistics(request):
    habits = Habit.objects.filter(user=request.user)
    stats = []
    today = timezone.now().date()
    
    for habit in habits:
        logs = HabitLog.objects.filter(habit=habit).order_by('date')
        total_registros = logs.count()
        
        # Calcular días desde la creación del hábito
        dias_desde_creacion = (today - habit.created_at.date()).days + 1
        
        # Calcular días completados
        if habit.goal_type == 'boolean':
            completados = logs.filter(value__gte=1).count()
        else:
            completados = logs.filter(value__gte=habit.target).count()
        
        # Calcular tasas
        tasa_exito = (completados / total_registros * 100) if total_registros > 0 else 0
        tasa_registro = (total_registros / dias_desde_creacion * 100) if dias_desde_creacion > 0 else 0
        
        stats.append({
            'habit': habit,
            'dias_desde_creacion': dias_desde_creacion,
            'total_registros': total_registros,
            'completados': completados,
            'tasa_exito': round(tasa_exito, 1),
            'tasa_registro': round(tasa_registro, 1),
            'current_streak': habit.current_streak(),
        })
    
    return render(request, 'habits/statistics.html', {'stats': stats})

@login_required
def exclude_day(request, habit_id):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    today = timezone.now().date()
    
    if request.method == 'POST':
        # Marcar el log de hoy como excluido
        log, created = HabitLog.objects.update_or_create(
            habit=habit,
            date=today,
            defaults={'excluded': True, 'value': 0}
        )
        
        messages.success(request, f'Día excluido para {habit.name}. Tu racha se mantiene.')
    
    return redirect('habit_list')