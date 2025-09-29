# catalog/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector
from django.db import transaction

from .models import Book

@receiver(post_save, sender=Book)
def update_book_search_vector(sender, instance: Book, **kwargs):
    """
    Update materialized search_vector column after Book is saved.
    This keeps the column up-to-date for fast searching.
    For very high write rates prefer a DB trigger or background job.
    """
    # Build weighted vector (similar weights as SearchService)
    vector = (
        SearchVector("title", weight="A", config="english")
        + SearchVector("author__first_name", weight="B", config="english")
        + SearchVector("author__last_name", weight="B", config="english")
        + SearchVector("publisher__name", weight="C", config="english")
        + SearchVector("category__name", weight="C", config="english")
        + SearchVector("description", weight="D", config="english")
    )

    # Save using update to avoid recursion; use transaction.on_commit to ensure FK relations exist
    def _update():
        Book.objects.filter(pk=instance.pk).update(search_vector=vector)
    transaction.on_commit(_update)
