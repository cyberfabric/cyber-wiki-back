"""
URL routing for source provider endpoints.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('content', views.get_content, name='source-content'),
    path('tree', views.get_tree, name='source-tree'),
]
