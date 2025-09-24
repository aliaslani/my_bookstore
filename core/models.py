from django.db import models
from common.models import  BaseModel
from django.conf import settings
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

    # In Author model
    from datetime import date

    def calculate_age(self,born, today):
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def current_age(self):
        if not self.date_of_birth:
            return None

        end_date = self.date_of_death or date.today()
        return self.calculate_age(self.date_of_birth, end_date)
    @property
    def full_name(self):
        return self.first_name + ' ' + self.last_name

class Publisher(BaseModel):
    name = models.CharField(max_length=200)
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
    name = models.CharField(max_length=200)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

class Book(BaseModel):
    title = models.CharField(max_length=500, db_index=True) # db_index برای جستجوی سریعتر
    authors = models.ManyToManyField(Author, related_name='books')
    description = models.TextField()
    publication_date = models.DateField(null=True, blank=True)
    publisher = models.ForeignKey(Publisher, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.title

    @property
    def authors_indexing(self):
        """Returns a string of all author names for full-text search."""
        return [author.full_name for author in self.authors.all()]

    @property
    def has_pdf_indexing(self):
        """Returns True if a PDF format exists for this book."""
        return self.formats.filter(format_type='PDF').exists()

    class Meta:
        ordering = ['title']
        verbose_name = 'Book'
        verbose_name_plural = 'Books'


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
        unique_together = ('book', 'format_type')
        verbose_name = 'Book Format'
        verbose_name_plural = 'Book Formats'

    def __str__(self):
        return f"{self.book.title} ({self.get_format_type_display()})"


class Comment(BaseModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.user} on {self.book}"
