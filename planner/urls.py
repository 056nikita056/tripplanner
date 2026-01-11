from django.urls import path

from . import views

urlpatterns = [
    path('', views.trip_list, name='trip_list'),

    path('trips/create/', views.trip_create, name='trip_create'),
    path('trips/<int:pk>/', views.trip_detail, name='trip_detail'),
    path('trips/<int:pk>/edit/', views.trip_edit, name='trip_edit'),
    path('trips/<int:pk>/delete/', views.trip_delete, name='trip_delete'),

    path('trips/<int:trip_pk>/activities/add/', views.activity_create, name='activity_create'),
    path('activities/<int:pk>/edit/', views.activity_edit, name='activity_edit'),
    path('activities/<int:pk>/delete/', views.activity_delete, name='activity_delete'),

    path('packing/items/', views.packing_items, name='packing_items'),
    path('packing/items/add/', views.packing_item_create, name='packing_item_create'),

    path('trips/<int:trip_pk>/packing/add/', views.trip_packing_add, name='trip_packing_add'),
    path('packing/<int:pk>/toggle/', views.trip_packing_toggle, name='trip_packing_toggle'),
    path('packing/<int:pk>/remove/', views.trip_packing_remove, name='trip_packing_remove'),
]
