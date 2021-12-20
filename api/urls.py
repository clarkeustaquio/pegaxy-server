from django.urls import path
from . import views

urlpatterns = [
    path('lookup/', views.lookup, name='lookup'),
    path('renthistory/', views.rent_history, name='rent_history'),
    path('manage-asset/', views.manage_asset, name='manage_asset'),
    path('chart/', views.vis_chart, name='vis_chart')
]
