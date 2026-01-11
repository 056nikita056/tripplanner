import random
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from planner.models import Activity, Destination, PackingItem, Tag, Trip, TripPackingItem


class Command(BaseCommand):
    help = 'Seed database with demo data (10-15+ records)'

    def handle(self, *args, **options):
        demo, _ = User.objects.get_or_create(username='demo')
        if not demo.has_usable_password():
            demo.set_password('demo12345')
            demo.save()

        Destination.objects.all().delete()

        destinations = [
            Destination.objects.create(name='Berlin', country='Germany', latitude=52.52000, longitude=13.40500, description='Capital city'),
            Destination.objects.create(name='Munich', country='Germany', latitude=48.13512, longitude=11.58198, description='Bavaria'),
            Destination.objects.create(name='Prague', country='Czechia', latitude=50.07554, longitude=14.43780, description='Old Town'),
            Destination.objects.create(name='Vienna', country='Austria', latitude=48.20817, longitude=16.37382, description='Museums'),
        ]

        tags = []
        for t in ['Food', 'Transport', 'Museum', 'Walk', 'Hotel', 'Shopping']:
            tags.append(Tag.objects.get_or_create(owner=demo, name=t)[0])

        packing_items = []
        for name, cat in [
            ('Passport', 'Documents'),
            ('Phone charger', 'Electronics'),
            ('T-shirt', 'Clothes'),
            ('Toothbrush', 'Hygiene'),
            ('Sneakers', 'Clothes'),
            ('Powerbank', 'Electronics'),
        ]:
            packing_items.append(PackingItem.objects.get_or_create(owner=demo, name=name, category=cat)[0])

        Trip.objects.filter(owner=demo).delete()

        base = date.today() - timedelta(days=60)
        trips = []
        for i in range(4):
            start = base + timedelta(days=i * 12)
            end = start + timedelta(days=random.randint(3, 7))
            trips.append(
                Trip.objects.create(
                    owner=demo,
                    title=f'Demo trip #{i+1}',
                    destination=destinations[i % len(destinations)],
                    start_date=start,
                    end_date=end,
                    budget=round(random.uniform(250, 1200), 2),
                    is_public=True,
                )
            )

        Activity.objects.filter(trip__in=trips).delete()

        for trip in trips:
            days = (trip.end_date - trip.start_date).days + 1
            for d in range(days):
                dt = trip.start_date + timedelta(days=d)
                for _ in range(random.randint(2, 4)):
                    a = Activity.objects.create(
                        trip=trip,
                        title=random.choice(['Coffee', 'Metro', 'Museum ticket', 'Lunch', 'Walk', 'Hotel night']),
                        date=dt,
                        cost=round(random.uniform(3, 90), 2),
                        notes='Demo activity',
                    )
                    a.tags.set(random.sample(tags, k=random.randint(0, 2)))

            for item in random.sample(packing_items, k=random.randint(3, 5)):
                TripPackingItem.objects.get_or_create(
                    trip=trip,
                    item=item,
                    defaults={'quantity': random.randint(1, 2), 'is_packed': random.choice([True, False])},
                )

        self.stdout.write(self.style.SUCCESS('Seeded demo data. Login: demo / demo12345'))
