# books/documents.py
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from core.models import Book
from django.db import models
@registry.register_document
class BookDocument(Document):

    authors = fields.TextField(
        attr='authors_indexing' # We will define this method on the model
    )

    has_pdf = fields.BooleanField(attr='has_pdf_indexing')

    class Index:
        name = 'books'

    class Django:
        model = Book
        fields = [
            'id',
            'title',
            'description',
        ]
        related_models = ['Author', 'BookFormat']
