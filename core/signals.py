from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .models import Book
from .tasks import update_search_vector_task  


@receiver(post_save, sender=Book)
def schedule_search_update(sender, instance, **kwargs):
    # Schedule async task only after transaction is committed
    transaction.on_commit(
        lambda: update_search_vector_task.delay(instance.pk)
    )
