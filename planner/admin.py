from django.contrib import admin

from .models import Activity, Destination, PackingItem, Tag, Trip, TripPackingItem


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ('name', 'country')
    search_fields = ('name', 'country')


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'destination', 'start_date', 'end_date', 'budget', 'is_public')
    list_filter = ('is_public', 'destination__country')
    search_fields = ('title', 'owner__username', 'destination__name')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner')
    search_fields = ('name', 'owner__username')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'trip', 'date', 'cost')
    list_filter = ('date',)
    search_fields = ('title', 'trip__title')


@admin.register(PackingItem)
class PackingItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'owner')
    list_filter = ('category',)
    search_fields = ('name', 'category', 'owner__username')


@admin.register(TripPackingItem)
class TripPackingItemAdmin(admin.ModelAdmin):
    list_display = ('trip', 'item', 'quantity', 'is_packed')
    list_filter = ('is_packed',)
    search_fields = ('trip__title', 'item__name')
