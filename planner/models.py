from django.conf import settings
from django.db import models


class Destination(models.Model):
    name = models.CharField(max_length=120)
    country = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True)
    longitude = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True)

    def __str__(self):
        if self.country:
            return f"{self.name}, {self.country}"
        return self.name


class Trip(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trips')
    title = models.CharField(max_length=160)
    destination = models.ForeignKey(Destination, on_delete=models.PROTECT, related_name='trips')
    start_date = models.DateField()
    end_date = models.DateField()
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Tag(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=40)

    class Meta:
        unique_together = [('owner', 'name')]
        ordering = ['name']

    def __str__(self):
        return self.name


class Activity(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='activities')
    title = models.CharField(max_length=160)
    date = models.DateField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='activities')

    class Meta:
        ordering = ['date', 'title']

    def __str__(self):
        return self.title


class PackingItem(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='packing_items')
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=80, blank=True)

    class Meta:
        unique_together = [('owner', 'name')]
        ordering = ['name']

    def __str__(self):
        return self.name


class TripPackingItem(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='packing_links')
    item = models.ForeignKey(PackingItem, on_delete=models.CASCADE, related_name='trip_links')
    quantity = models.PositiveIntegerField(default=1)
    is_packed = models.BooleanField(default=False)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = [('trip', 'item')]
        ordering = ['item__name']

    def __str__(self):
        return f"{self.trip}: {self.item}"
