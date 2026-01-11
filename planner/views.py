import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import ActivityForm, PackingItemForm, TripForm, TripPackingItemForm
from .models import Activity, PackingItem, Tag, Trip, TripPackingItem
from .services import get_forecast


def _trip_queryset_for_user(user):
    if user.is_authenticated:
        return Trip.objects.select_related('destination', 'owner').filter(Q(is_public=True) | Q(owner=user))
    return Trip.objects.select_related('destination', 'owner').filter(is_public=True)


def trip_list(request):
    qs = _trip_queryset_for_user(request.user)
    q = (request.GET.get('q') or '').strip()
    sort = (request.GET.get('sort') or '').strip()

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(destination__name__icontains=q) | Q(destination__country__icontains=q))

    if sort == 'date_asc':
        qs = qs.order_by('start_date')
    elif sort == 'date_desc':
        qs = qs.order_by('-start_date')

    return render(request, 'planner/trip_list.html', {'trips': qs, 'q': q, 'sort': sort})


def trip_detail(request, pk: int):
    trip = get_object_or_404(_trip_queryset_for_user(request.user), pk=pk)

    total_cost = trip.activities.aggregate(total=Sum('cost'))['total'] or 0
    remaining = (trip.budget or 0) - total_cost

    by_day = (
        trip.activities.values('date')
        .annotate(total=Sum('cost'))
        .order_by('date')
    )

    by_tag = (
        trip.activities.values('tags__name')
        .annotate(total=Sum('cost'))
        .order_by('-total')
    )

    chart_days = [str(x['date']) for x in by_day]
    chart_day_totals = [float(x['total'] or 0) for x in by_day]

    chart_tags = [x['tags__name'] or 'Без тега' for x in by_tag]
    chart_tag_totals = [float(x['total'] or 0) for x in by_tag]

    forecast = None
    if trip.destination.latitude is not None and trip.destination.longitude is not None:
        forecast = get_forecast(float(trip.destination.latitude), float(trip.destination.longitude))

    packing_links = trip.packing_links.select_related('item').all()

    context = {
        'trip': trip,
        'total_cost': total_cost,
        'remaining': remaining,
        'forecast': forecast,
        'packing_links': packing_links,
        'chart_days_json': json.dumps(chart_days),
        'chart_day_totals_json': json.dumps(chart_day_totals),
        'chart_tags_json': json.dumps(chart_tags),
        'chart_tag_totals_json': json.dumps(chart_tag_totals),
    }
    return render(request, 'planner/trip_detail.html', context)


@login_required
def trip_create(request):
    if request.method == 'POST':
        form = TripForm(request.POST)
        if form.is_valid():
            trip = form.save(commit=False)
            trip.owner = request.user
            trip.save()
            messages.success(request, 'Поездка создана.')
            return redirect('trip_detail', pk=trip.pk)
    else:
        form = TripForm()
    return render(request, 'planner/form.html', {'title': 'Новая поездка', 'form': form})


@login_required
def trip_edit(request, pk: int):
    trip = get_object_or_404(Trip, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = TripForm(request.POST, instance=trip)
        if form.is_valid():
            form.save()
            messages.success(request, 'Поездка обновлена.')
            return redirect('trip_detail', pk=trip.pk)
    else:
        form = TripForm(instance=trip)
    return render(request, 'planner/form.html', {'title': 'Редактирование поездки', 'form': form})


@login_required
def trip_delete(request, pk: int):
    trip = get_object_or_404(Trip, pk=pk, owner=request.user)
    if request.method == 'POST':
        trip.delete()
        messages.success(request, 'Поездка удалена.')
        return redirect('trip_list')
    return render(request, 'planner/confirm_delete.html', {'object': trip})


@login_required
def activity_create(request, trip_pk: int):
    trip = get_object_or_404(Trip, pk=trip_pk, owner=request.user)
    if request.method == 'POST':
        form = ActivityForm(request.POST, trip=trip, owner=request.user)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.trip = trip
            activity.save()
            form.save_m2m()
            messages.success(request, 'Активность добавлена.')
            return redirect('trip_detail', pk=trip.pk)
    else:
        form = ActivityForm(trip=trip, owner=request.user)
    return render(request, 'planner/form.html', {'title': 'Новая активность', 'form': form, 'back_url': reverse('trip_detail', args=[trip.pk])})


@login_required
def activity_edit(request, pk: int):
    activity = get_object_or_404(Activity.objects.select_related('trip'), pk=pk)
    if activity.trip.owner != request.user:
        raise Http404
    trip = activity.trip
    if request.method == 'POST':
        form = ActivityForm(request.POST, instance=activity, trip=trip, owner=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Активность обновлена.')
            return redirect('trip_detail', pk=trip.pk)
    else:
        form = ActivityForm(instance=activity, trip=trip, owner=request.user)
    return render(request, 'planner/form.html', {'title': 'Редактирование активности', 'form': form, 'back_url': reverse('trip_detail', args=[trip.pk])})


@login_required
def activity_delete(request, pk: int):
    activity = get_object_or_404(Activity.objects.select_related('trip'), pk=pk)
    if activity.trip.owner != request.user:
        raise Http404
    trip = activity.trip
    if request.method == 'POST':
        activity.delete()
        messages.success(request, 'Активность удалена.')
        return redirect('trip_detail', pk=trip.pk)
    return render(request, 'planner/confirm_delete.html', {'object': activity, 'back_url': reverse('trip_detail', args=[trip.pk])})


@login_required
def packing_item_create(request):
    if request.method == 'POST':
        form = PackingItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            messages.success(request, 'Предмет создан.')
            return redirect('packing_items')
    else:
        form = PackingItemForm()
    return render(request, 'planner/form.html', {'title': 'Новый предмет', 'form': form, 'back_url': reverse('packing_items')})


@login_required
def packing_items(request):
    items = PackingItem.objects.filter(owner=request.user).order_by('category', 'name')
    return render(request, 'planner/packing_items.html', {'items': items})


@login_required
def trip_packing_add(request, trip_pk: int):
    trip = get_object_or_404(Trip, pk=trip_pk, owner=request.user)
    if request.method == 'POST':
        form = TripPackingItemForm(request.POST, owner=request.user)
        if form.is_valid():
            link = form.save(commit=False)
            link.trip = trip
            link.save()
            messages.success(request, 'Добавлено в список вещей.')
            return redirect('trip_detail', pk=trip.pk)
    else:
        form = TripPackingItemForm(owner=request.user)
    return render(request, 'planner/form.html', {'title': 'Добавить в список вещей', 'form': form, 'back_url': reverse('trip_detail', args=[trip.pk])})


@login_required
def trip_packing_toggle(request, pk: int):
    link = get_object_or_404(TripPackingItem.objects.select_related('trip'), pk=pk)
    if link.trip.owner != request.user:
        raise Http404
    link.is_packed = not link.is_packed
    link.save(update_fields=['is_packed'])
    return redirect('trip_detail', pk=link.trip.pk)


@login_required
def trip_packing_remove(request, pk: int):
    link = get_object_or_404(TripPackingItem.objects.select_related('trip'), pk=pk)
    if link.trip.owner != request.user:
        raise Http404
    trip_pk = link.trip.pk
    link.delete()
    messages.success(request, 'Удалено из списка вещей.')
    return redirect('trip_detail', pk=trip_pk)
