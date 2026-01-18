import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ActivityForm, PackingItemForm, TripForm, TripPackingItemForm
from .models import Activity, Destination, PackingItem, Trip, TripPackingItem
from .services import get_forecast


def _trip_queryset_for_user(user):
    if user.is_authenticated:
        return Trip.objects.select_related('destination', 'owner').filter(
            Q(is_public=True) | Q(owner=user)
        )
    return Trip.objects.select_related('destination', 'owner').filter(is_public=True)


def trip_list(request):
    qs = _trip_queryset_for_user(request.user)
    q = (request.GET.get('q') or '').strip()
    sort = (request.GET.get('sort') or 'new').strip()
    dest_raw = (request.GET.get('dest') or '').strip()

    dest_id = None
    if dest_raw.isdigit():
        dest_id = int(dest_raw)

    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(destination__name__icontains=q)
            | Q(destination__country__icontains=q)
        )

    if dest_id:
        qs = qs.filter(destination_id=dest_id)

    if sort == 'new':
        qs = qs.order_by('-created_at')
    elif sort == 'budget':
        qs = qs.order_by('-budget', '-created_at')
    elif sort == 'start':
        qs = qs.order_by('start_date', '-created_at')
    else:
        sort = 'new'
        qs = qs.order_by('-created_at')

    destinations = (
        Destination.objects.filter(trips__in=qs).distinct().order_by('country', 'name')
    )

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page') or 1)

    params = request.GET.copy()
    params.pop('page', None)
    qs_params = params.urlencode()

    context = {
        'trips': page_obj,
        'page_obj': page_obj,
        'q': q,
        'sort': sort,
        'destinations': destinations,
        'dest_id': dest_id,
        'qs_params': qs_params,
    }
    return render(request, 'planner/trip_list.html', context)


@login_required
def dashboard(request):
    trips = Trip.objects.filter(owner=request.user).select_related('destination')
    trip_stats = trips.aggregate(
        trips_total=Count('id'),
        public_total=Count('id', filter=Q(is_public=True)),
        private_total=Count('id', filter=Q(is_public=False)),
        total_budget=Sum('budget'),
        avg_budget=Avg('budget'),
    )

    activities = Activity.objects.filter(trip__owner=request.user)
    activity_stats = activities.aggregate(
        total_spent=Sum('cost'),
        avg_activity_cost=Avg('cost'),
    )

    top_destinations = (
        trips.values('destination__name', 'destination__country')
        .annotate(trips_count=Count('id'), budget_sum=Sum('budget'))
        .order_by('-trips_count', '-budget_sum')[:5]
    )

    top_tags = (
        activities.values('tags__name')
        .annotate(total=Sum('cost'), uses=Count('id'))
        .order_by('-total')[:5]
    )

    context = {
        'trip_stats': trip_stats,
        'activity_stats': activity_stats,
        'top_destinations': top_destinations,
        'top_tags': top_tags,
    }
    return render(request, 'planner/dashboard.html', context)


def trip_detail(request, pk: int):
    trip = get_object_or_404(_trip_queryset_for_user(request.user), pk=pk)

    activities = trip.activities.prefetch_related('tags').all()

    total_cost = activities.aggregate(total=Sum('cost'))['total'] or 0
    remaining = (trip.budget or 0) - total_cost

    by_day = list(
        activities.values('date').annotate(total=Sum('cost')).order_by('date')
    )

    by_tag = list(
        activities.values('tags__name').annotate(total=Sum('cost')).order_by('-total')
    )

    chart_days = [str(x['date']) for x in by_day]
    chart_day_totals = [float(x['total'] or 0) for x in by_day]

    chart_tags = [x['tags__name'] or 'Без тега' for x in by_tag]
    chart_tag_totals = [float(x['total'] or 0) for x in by_tag]

    forecast = None
    if trip.destination.latitude is not None and trip.destination.longitude is not None:
        forecast = get_forecast(
            float(trip.destination.latitude), float(trip.destination.longitude)
        )

    weather_rows = []
    if forecast and forecast.ok:
        daily = (forecast.data or {}).get('daily') or {}
        times = daily.get('time') or []
        tmax = daily.get('temperature_2m_max') or []
        tmin = daily.get('temperature_2m_min') or []
        pop = daily.get('precipitation_probability_max') or []
        n = min(len(times), len(tmax), len(tmin), len(pop), 7)
        for i in range(n):
            weather_rows.append(
                {
                    'date': times[i],
                    'tmax': tmax[i],
                    'tmin': tmin[i],
                    'pop': pop[i],
                }
            )

    packing_links = trip.packing_links.select_related('item').all()
    packed_count = packing_links.filter(is_packed=True).count()
    total_packing = packing_links.count()

    packed_pct = None
    if total_packing:
        packed_pct = round((packed_count / total_packing) * 100, 1)

    most_expensive_activity = activities.order_by('-cost', '-date').first()

    most_expensive_day = None
    if by_day:
        most_expensive_day = max(by_day, key=lambda x: x['total'] or 0)

    budget_pct = None
    if trip.budget and float(trip.budget) > 0:
        budget_pct = round((float(total_cost) / float(trip.budget)) * 100, 1)

    context = {
        'trip': trip,
        'activities': activities,
        'total_cost': total_cost,
        'remaining': remaining,
        'budget_pct': budget_pct,
        'most_expensive_activity': most_expensive_activity,
        'most_expensive_day': most_expensive_day,
        'forecast': forecast,
        'weather_rows': weather_rows,
        'packing_links': packing_links,
        'packed_count': packed_count,
        'total_packing': total_packing,
        'packed_pct': packed_pct,
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
    return render(
        request,
        'planner/form.html',
        {'title': 'Редактирование поездки', 'form': form},
    )


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
    return render(
        request,
        'planner/form.html',
        {
            'title': 'Новая активность',
            'form': form,
            'back_url': reverse('trip_detail', args=[trip.pk]),
        },
    )


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
    return render(
        request,
        'planner/form.html',
        {
            'title': 'Редактирование активности',
            'form': form,
            'back_url': reverse('trip_detail', args=[trip.pk]),
        },
    )


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
    return render(
        request,
        'planner/confirm_delete.html',
        {'object': activity, 'back_url': reverse('trip_detail', args=[trip.pk])},
    )


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
    return render(
        request,
        'planner/form.html',
        {'title': 'Новый предмет', 'form': form, 'back_url': reverse('packing_items')},
    )


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
    return render(
        request,
        'planner/form.html',
        {
            'title': 'Добавить в список вещей',
            'form': form,
            'back_url': reverse('trip_detail', args=[trip.pk]),
        },
    )


@login_required
def trip_packing_toggle(request, pk: int):
    link = get_object_or_404(TripPackingItem.objects.select_related('trip'), pk=pk)
    if link.trip.owner != request.user:
        raise Http404
    link.is_packed = not link.is_packed
    link.save(update_fields=['is_packed'])
    return redirect('trip_detail', pk=link.trip.pk)


@require_POST
@login_required
def trip_packing_toggle_api(request, pk: int):
    link = get_object_or_404(TripPackingItem.objects.select_related('trip'), pk=pk)
    if link.trip.owner != request.user:
        raise Http404
    link.is_packed = not link.is_packed
    link.save(update_fields=['is_packed'])
    packed_count = TripPackingItem.objects.filter(trip=link.trip, is_packed=True).count()
    total_count = TripPackingItem.objects.filter(trip=link.trip).count()
    return JsonResponse(
        {
            'ok': True,
            'is_packed': link.is_packed,
            'packed_count': packed_count,
            'total_count': total_count,
        }
    )


@login_required
def trip_packing_remove(request, pk: int):
    link = get_object_or_404(TripPackingItem.objects.select_related('trip'), pk=pk)
    if link.trip.owner != request.user:
        raise Http404
    trip_pk = link.trip.pk
    link.delete()
    messages.success(request, 'Удалено из списка вещей.')
    return redirect('trip_detail', pk=trip_pk)
