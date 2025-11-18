from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.utils import timezone
from django.contrib import messages
from .models import Habit, HabitLog
from .forms import HabitForm, UserRegisterForm
from django.http import JsonResponse
import json

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
    today = timezone.localdate()
    
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
    today = timezone.localdate()
    
    if request.method == 'POST':
        raw = request.POST.get('value', '1')
        try:
            value = float(raw)
        except Exception:
            value = 0.0

        # Normalizar booleano
        if habit.goal_type == 'boolean':
            value = 1.0 if value >= 1 else 0.0

        # Si el día ya existe y está excluido, y vienen a "reactivar" con value == 0,
        # eliminamos el registro para restaurar el estado anterior (no romper racha).
        existing = HabitLog.objects.filter(habit=habit, date=today).first()
        if value == 0.0 and existing and existing.excluded:
            existing.delete()
            messages.info(request, f'Día reactivado para {habit.name}. Registro eliminado.')
            return redirect('habit_list')

        # Crear / actualizar log normal (quita exclusión)
        log, created = HabitLog.objects.update_or_create(
            habit=habit,
            date=today,
            defaults={'value': value, 'excluded': False}
        )

        if value > 0:
            messages.success(request, f'Registro guardado para {habit.name}!')
        else:
            messages.info(request, f'Día registrado como no completado para {habit.name}.')
    
    return redirect('habit_list')

@login_required
def statistics(request):
    habits = Habit.objects.filter(user=request.user)
    stats = []
    # usar fecha local para evitar desfases por timezone
    today = timezone.localdate()
    
    for habit in habits:
        # considerar solo logs no excluidos para estadísticas de registros/completados
        logs = HabitLog.objects.filter(habit=habit, excluded=False).order_by('date')
        total_registros = logs.count()

        # Calcular días desde la creación del hábito usando la fecha local del created_at
        created_date = timezone.localtime(habit.created_at).date()
        dias_desde_creacion = (today - created_date).days + 1
        
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
            'current_streak': habit.current_streak,
        })
    
    return render(request, 'habits/statistics.html', {'stats': stats})

@login_required
def exclude_day(request, habit_id):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    today = timezone.localdate()
    
    if request.method == 'POST':
        # Marcar el log de hoy como excluido
        log, created = HabitLog.objects.update_or_create(
            habit=habit,
            date=today,
            defaults={'excluded': True, 'value': 0}
        )
        
        messages.success(request, f'Día excluido para {habit.name}. Tu racha se mantiene.')
    
    return redirect('habit_list')

@login_required
def timer_action(request, habit_id):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        
        if action == 'start':
            # Iniciar temporizador
            habit.timer_state = 'running'
            habit.timer_started_at = timezone.now()
            habit.save()
            
            return JsonResponse({
                'status': 'started',
                'elapsed': habit.get_current_elapsed_time(),
                'remaining': habit.get_remaining_time()
            })
            
        elif action == 'pause':
            # Pausar temporizador
            if habit.timer_state == 'running' and habit.timer_started_at:
                current_elapsed = (timezone.now() - habit.timer_started_at).total_seconds()
                habit.accumulated_time += current_elapsed
                habit.timer_state = 'paused'
                habit.timer_started_at = None
                habit.save()
            
            return JsonResponse({
                'status': 'paused',
                'elapsed': habit.get_current_elapsed_time(),
                'remaining': habit.get_remaining_time()
            })
            
        elif action == 'resume':
            # Reanudar temporizador
            habit.timer_state = 'running'
            habit.timer_started_at = timezone.now()
            habit.save()
            
            return JsonResponse({
                'status': 'resumed',
                'elapsed': habit.get_current_elapsed_time(),
                'remaining': habit.get_remaining_time()
            })
            
        elif action == 'stop':
            # Detener y completar el hábito
            today = timezone.localdate()
            elapsed_minutes = habit.get_current_elapsed_time() / 60  # convertir a minutos
            
            # Crear registro del hábito
            log, created = HabitLog.objects.update_or_create(
                habit=habit,
                date=today,
                defaults={'value': elapsed_minutes, 'excluded': False}
            )
            
            # Resetear temporizador
            habit.timer_state = 'stopped'
            habit.timer_started_at = None
            habit.accumulated_time = 0.0
            habit.save()
            
            return JsonResponse({
                'status': 'completed',
                'value': elapsed_minutes,
                'message': f'¡Hábito completado! Tiempo: {elapsed_minutes:.1f} minutos'
            })
            
        elif action == 'reset':
            # Resetear temporizador
            habit.timer_state = 'stopped'
            habit.timer_started_at = None
            habit.accumulated_time = 0.0
            habit.save()
            
            return JsonResponse({'status': 'reset'})
    
    return JsonResponse({'status': 'error', 'message': 'Acción no válida'})

@login_required
def timer_status(request, habit_id):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    
    return JsonResponse({
        'state': habit.timer_state,
        'elapsed': habit.get_current_elapsed_time(),
        'remaining': habit.get_remaining_time(),
        'is_complete': habit.is_timer_complete(),
        'target_minutes': habit.target
    })