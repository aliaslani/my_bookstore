from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.conf import settings
from common.models import BaseModel
from datetime import date

class Author(BaseModel):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    date_of_death = models.DateField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.first_name + ' ' + self.last_name


    @property
    def full_name(self):
        return self.first_name + ' ' + self.last_name

class Publisher(BaseModel):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to='publishers/', blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Publisher'
        verbose_name_plural = 'Publishers'

class Category(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

class Book(BaseModel):
    title = models.CharField(max_length=255)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books")
    description = models.TextField()
    publication_date = models.DateField(null=True)
    search_vector = SearchVectorField(null=True)
    publisher = models.ForeignKey('Publisher', on_delete=models.PROTECT, related_name='books')
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)
    class Meta:
        indexes = [
            GinIndex(fields=["search_vector"]),
            models.Index(fields=["title", "author"]),
            models.Index(fields=["created_at"]),  
        ]


class BookFormat(BaseModel):

    class FormatTypes(models.TextChoices):
        PHYSICAL = 'PHYSICAL', 'PHYSICAL'
        PDF = 'PDF', 'PDF'
        EPUB = 'EPUB', 'EPUB'
        AUDIO = 'AUDIO', 'AUDIO'

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='formats')
    format_type = models.CharField(max_length=20, choices=FormatTypes.choices)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    pdf_file = models.FileField(upload_to='pdfs/', null=True, blank=True)

    class Meta:
        unique_together = ("book", "format_type")
        indexes = [
            models.Index(fields=["format_type"]),
            models.Index(fields=["created_at"]),  
        ]


class Comment(BaseModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')

    class Meta:
        indexes = [
            models.Index(fields=["book", "created_at"]),
            models.Index(fields=["parent"]),
        ]
