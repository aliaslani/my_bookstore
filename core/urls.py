# urls.py
from django.urls import path
from core.views import BookSearchView

urlpatterns = [

    path('search/', BookSearchView.as_view(), name='book-search'),
]
