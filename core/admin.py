from django.contrib import admin
from django.contrib.postgres.search import SearchQuery, SearchVector, SearchRank
from .models import Author, Publisher, Category, Book, BookFormat, Comment
from django.contrib import admin

class BaseAdmin(admin.ModelAdmin):
    list_display = ['id', '__str__', 'created_at', 'is_deleted']
    list_filter = ['is_deleted']
    actions = ['soft_delete', 'restore']

    def get_queryset(self, request):
        """Filter out soft-deleted records by default."""
        qs = super().get_queryset(request)
        return qs.filter(is_deleted=False)

    @admin.action(description="Soft delete selected records")
    def soft_delete(self, request, queryset):
        queryset.update(is_deleted=True)
        self.message_user(request, f"Soft-deleted {queryset.count()} records.")

    @admin.action(description="Restore selected records")
    def restore(self, request, queryset):
        """Restore soft-deleted records."""
        queryset.update(is_deleted=False)
        self.message_user(request, f"Restored {queryset.count()} records.")


@admin.register(Author)
class AuthorAdmin(BaseAdmin):
    list_display = ['id', 'full_name', 'email', 'date_of_birth', 'is_deleted']
    search_fields = ['first_name', 'last_name', 'email', 'bio']
    list_filter = ['is_deleted', 'date_of_birth']
    list_per_page = 50  # Optimize for large datasets
    ordering = ['last_name', 'first_name']

    def get_search_results(self, request, queryset, search_term):
        """Use full-text search for better performance."""
        if search_term:
            search_query = SearchQuery(search_term)
            queryset = queryset.annotate(
                search=SearchVector('first_name', 'last_name', 'bio')
            ).filter(search=search_query)
            return queryset, False
        return super().get_search_results(request, queryset, search_term)


@admin.register(Publisher)
class PublisherAdmin(BaseAdmin):
    list_display = ['id', 'name', 'email', 'phone', 'website', 'is_deleted']
    search_fields = ['name', 'email', 'address']
    list_filter = ['is_deleted']
    list_per_page = 50
    ordering = ['name']
    readonly_fields = ['logo']  # Avoid direct file edits in admin
    fields = ['name', 'address', 'email', 'phone', 'website', 'logo', 'is_deleted']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'parent', 'description']
    search_fields = ['name', 'description']
    list_filter = ['parent']
    list_per_page = 50
    ordering = ['name']
    raw_id_fields = ['parent']  

    def get_queryset(self, request):
        """No soft delete for Category, but ensure optimized queryset."""
        return super().get_queryset(request).select_related('parent')


@admin.register(Book)
class BookAdmin(BaseAdmin):
    list_display = ['id', 'title', 'author', 'publisher', 'category', 'publication_date', 'is_deleted']
    search_fields = ['title', 'author__first_name', 'author__last_name']
    list_filter = ['is_deleted', 'publisher', 'category', 'publication_date']
    list_per_page = 50
    ordering = ['-created_at']
    raw_id_fields = ['author', 'publisher', 'category']  # Optimize for large datasets
    actions = ['soft_delete', 'restore', 'update_search_vector']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('author', 'publisher', 'category').prefetch_related('formats')

    def get_search_results(self, request, queryset, search_term):
        if search_term:
            search_query = SearchQuery(search_term)
            queryset = queryset.annotate(
                search=SearchVector('title', weight='A') + SearchVector('author__first_name', weight='B') + SearchVector('author__last_name', weight='B')
            ).filter(search=search_query)
            return queryset, False
        return super().get_search_results(request, queryset, search_term)

    @admin.action(description="Update search vectors")
    def update_search_vector(self, request, queryset):
        for book in queryset:
            book.search_vector = SearchVector('title', weight='A') + \
                                 SearchVector('author__first_name', weight='B') + \
                                 SearchVector('author__last_name', weight='B')
            book.save(update_fields=['search_vector'])
        self.message_user(request, f"Updated search vectors for {queryset.count()} books.")


@admin.register(BookFormat)
class BookFormatAdmin(BaseAdmin):
    list_display = ['id', 'book', 'format_type', 'price', 'stock', 'pdf_file', 'is_deleted']
    search_fields = ['book__title', 'format_type']
    list_filter = ['is_deleted', 'format_type']
    list_per_page = 50
    ordering = ['-created_at']
    raw_id_fields = ['book']  # Optimize for large datasets
    fields = ['book', 'format_type', 'price', 'stock', 'pdf_file', 'is_deleted']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('book__author', 'book__publisher')

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'format_type':
            kwargs['choices'] = BookFormat.FormatTypes.choices
        return super().formfield_for_choice_field(db_field, request, **kwargs)


class CommentReplyInline(admin.TabularInline):
    model = Comment
    fk_name = 'parent'
    fields = ['user', 'content', 'created_at']
    readonly_fields = ['id', 'content_preview', 'created_at']
    raw_id_fields = ['user']
    extra = 0

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'

@admin.register(Comment)
class CommentAdmin(BaseAdmin):
    list_display = ['id', 'book_title', 'user_username', 'content_preview', 'parent_id', 'created_at', 'is_deleted']
    search_fields = ['book__title', 'user__username', 'search_vector']
    list_filter = ['is_deleted', 'created_at']
    list_per_page = 20
    ordering = ['-created_at']
    raw_id_fields = ['book', 'user', 'parent']
    readonly_fields = ['created_at']
    inlines = [CommentReplyInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('book', 'user').filter(is_deleted=False)
        search_query = request.GET.get('q', '').strip()
        if search_query:
            search_q = SearchQuery(search_query, config='english')
            if 'search_vector' in [f.name for f in Comment._meta.get_fields()]:
                queryset = queryset.annotate(
                    rank=SearchRank('search_vector', search_q)
                ).filter(search_vector=search_q).order_by('-rank')
            else:
                queryset = queryset.annotate(
                    search_vector_temp=SearchVector('content', weight='A', config='english'),
                    rank=SearchRank('search_vector_temp', search_q)
                ).filter(search_vector_temp=search_q).order_by('-rank')
        return queryset

    def book_title(self, obj):
        return obj.book.title if obj.book else '-'
    book_title.short_description = 'Book'

    def user_username(self, obj):
        return obj.user.username if obj.user else '-'
    user_username.short_description = 'User'

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'

    def parent_id(self, obj):
        return obj.parent_id if obj.parent else '-'
    parent_id.short_description = 'Parent'