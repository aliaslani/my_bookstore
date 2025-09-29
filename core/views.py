from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import Author, Publisher, Category, Book, BookFormat, Comment
from .serializers import (
    AuthorSerializer, PublisherSerializer, CategorySerializer,
    BookListSerializer, BookDetailSerializer, BookCreateUpdateSerializer, 
    BookFormatSerializer, CommentSerializer
)
from rest_framework import serializers
from rest_framework.views import APIView
from django.core.paginator import Paginator, EmptyPage
import logging
from core.search import SearchService

logger = logging.getLogger(__name__)

User = get_user_model()

class StandardPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100  

class AuthorViewSet(viewsets.ModelViewSet):
    
    queryset = Author.objects.all().order_by('last_name', 'first_name')
    serializer_class = AuthorSerializer
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name']
    ordering_fields = ['last_name', 'first_name', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(Author, 'objects') and hasattr(Author.objects, 'filter'):
            queryset = queryset.filter(is_deleted=False) if hasattr(queryset.model, 'is_deleted') else queryset
        return queryset

    


class PublisherViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Publishers: CRUD operations.
    Optimized for queries with ordering on name.
    """
    queryset = Publisher.objects.all().order_by('name')
    serializer_class = PublisherSerializer
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'address', 'email']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(Publisher, 'objects') and hasattr(Publisher.objects, 'filter'):
            queryset = queryset.filter(is_deleted=False) if hasattr(queryset.model, 'is_deleted') else queryset
        return queryset



class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Categories: CRUD with self-referential parent.
    Supports hierarchical filtering.
    """
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(Category, 'is_deleted'):
            queryset = queryset.filter(is_deleted=False)
        return queryset

class BookViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Books: Full CRUD with search and filtering.
    Optimized for 300k+ books with full-text search, partitioning, and prefetching.
    Uses different serializers for list, detail, and create/update operations.
    """
    queryset = Book.objects.select_related('author', 'publisher', 'category')
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['title', 'publication_date', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return different serializers based on action."""
        if self.action == 'list' or self.action == 'search':
            return BookListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return BookCreateUpdateSerializer
        else:
            return BookDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        if hasattr(Book, 'is_deleted'):
            queryset = queryset.filter(is_deleted=False)
        
        if self.action == 'list' or self.action == 'search':
            queryset = queryset.prefetch_related('formats', 'comments')
        elif self.action == 'retrieve':
            queryset = queryset.prefetch_related('formats', 'comments__user', 'comments__replies__user')
        
        search_query = self.request.query_params.get('search', '').strip()
        if search_query:
            search_q = SearchQuery(search_query, config='english')
            if 'search_vector' in [f.name for f in Book._meta.get_fields()]:
                queryset = queryset.annotate(
                    rank=SearchRank('search_vector', search_q)
                ).filter(search_vector=search_q)
            else:
                queryset = queryset.annotate(
                    search_vector_temp=SearchVector('title', weight='A', config='english') +
                                     SearchVector('author__first_name', weight='B', config='english') +
                                     SearchVector('author__last_name', weight='B', config='english') +
                                     SearchVector('description', weight='C', config='english'),
                    rank=SearchRank('search_vector_temp', search_q)
                ).filter(search_vector_temp=search_q)
            queryset = queryset.order_by('-rank')
        
        format_filter = self.request.query_params.get('format', '').upper()
        if format_filter in [choice[0] for choice in BookFormat.FormatTypes.choices]:
            queryset = queryset.filter(formats__format_type=format_filter).distinct()
        
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        publisher_id = self.request.query_params.get('publisher')
        if publisher_id:
            queryset = queryset.filter(publisher_id=publisher_id)
        
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price or max_price:
            price_q = Q()
            if min_price:
                price_q &= Q(formats__price__gte=min_price)
            if max_price:
                price_q &= Q(formats__price__lte=max_price)
            queryset = queryset.filter(price_q).distinct()
        
        author_id = self.request.query_params.get('author')
        if author_id:
            queryset = queryset.filter(author_id=author_id)
        
        pub_year = self.request.query_params.get('publication_year')
        if pub_year:
            queryset = queryset.filter(publication_date__year=pub_year)
        
        if self.request.query_params.get('available') == 'true':
            queryset = queryset.filter(formats__stock__gt=0).distinct()
        
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            book = serializer.save()
            detail_serializer = BookDetailSerializer(book, context={'request': request})
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            book = serializer.save()
            detail_serializer = BookDetailSerializer(book, context={'request': request})
            return Response(detail_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def formats(self, request, pk=None):
        book = self.get_object()
        formats = book.formats.filter(is_deleted=False)
        page = self.paginate_queryset(formats)
        if page is not None:
            serializer = BookFormatSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = BookFormatSerializer(formats, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def available(self, request):
        queryset = self.get_queryset().filter(formats__stock__gt=0).distinct()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        book = self.get_object()
        comments = book.comments.filter(is_deleted=False, parent__isnull=True).select_related('user').prefetch_related('replies__user').order_by('-created_at')
        page = self.paginate_queryset(comments)
        if page is not None:
            serializer = CommentSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = CommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        /books/search/?q=...&author=...&publisher=...&category=...&page=1&per_page=20
        Returns ranked results using Postgres full-text search and fuzzy fallback.
        """
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response({"error": "q parameter required"}, status=status.HTTP_400_BAD_REQUEST)

        # Base queryset: filter out deleted, select_related for serialization speed
        base_qs = self.get_queryset().filter(is_deleted=False).select_related("author", "publisher", "category").distinct()

        # Apply optional filters (author, publisher, category, year, format, price)
        author = request.query_params.get("author")
        publisher = request.query_params.get("publisher")
        category = request.query_params.get("category")
        pub_year = request.query_params.get("publication_year")
        if author:
            if author.isdigit():
                base_qs = base_qs.filter(author_id=int(author))
            else:
                base_qs = base_qs.filter(Q(author__first_name__icontains=author) | Q(author__last_name__icontains=author))
        if publisher:
            if publisher.isdigit():
                base_qs = base_qs.filter(publisher_id=int(publisher))
            else:
                base_qs = base_qs.filter(publisher__name__icontains=publisher)
        if category:
            if category.isdigit():
                base_qs = base_qs.filter(category_id=int(category))
            else:
                base_qs = base_qs.filter(category__name__icontains=category)
        if pub_year:
            try:
                base_qs = base_qs.filter(publication_date__year=int(pub_year))
            except ValueError:
                return Response({"error": "Invalid publication_year"}, status=status.HTTP_400_BAD_REQUEST)

        # Use SearchService to get ranked queryset
        ranked_qs = SearchService.full_text_search(base_qs, q, use_materialized_vector=True, trigram_fallback=True)

        # paginate using DRF pagination if you prefer, here simple paginator example:
        page = int(request.query_params.get("page", 1))
        per_page = int(request.query_params.get("per_page", 20))
        paginator = Paginator(ranked_qs.distinct(), per_page)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            return Response({"results": [], "count": 0, "num_pages": paginator.num_pages, "current_page": page})

        serializer = BookListSerializer(page_obj.object_list, many=True, context={"request": request})
        return Response({
            "results": serializer.data,
            "count": paginator.count,
            "num_pages": paginator.num_pages,
            "current_page": page,
        }, status=status.HTTP_200_OK)
    
    

class BookFormatViewSet(viewsets.ModelViewSet):
    """
    ViewSet for BookFormats: CRUD for physical/PDF/EPUB/AUDIO variants.
    Optimized with prefetching and unique constraints.
    """
    queryset = BookFormat.objects.select_related('book__author', 'book__publisher')
    serializer_class = BookFormatSerializer
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['book__title', 'format_type']
    ordering_fields = ['price', 'stock', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(BookFormat, 'is_deleted'):
            queryset = queryset.filter(is_deleted=False)
        book_id = self.request.query_params.get('book')
        if book_id:
            queryset = queryset.filter(book_id=book_id)
        return queryset

    def perform_create(self, serializer):
        """Ensure book exists and is not deleted."""
        book_id = serializer.validated_data['book'].id
        book = get_object_or_404(Book, id=book_id, is_deleted=False if hasattr(Book, 'is_deleted') else True)
        serializer.save(book=book)


class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Comments: Threaded replies with authentication.
    Optimized for scalability with prefetching and limits on replies.
    """
    queryset = Comment.objects.select_related('user', 'book__author').prefetch_related('replies__user')
    serializer_class = CommentSerializer
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(Comment, 'is_deleted'):
            queryset = queryset.filter(is_deleted=False)
        book_id = self.request.query_params.get('book')
        if book_id:
            queryset = queryset.filter(book_id=book_id)
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        return queryset

    def perform_create(self, serializer):
        """Set user and validate parent book match."""
        book = serializer.validated_data['book']
        parent = serializer.validated_data.get('parent')
        if parent and parent.book != book:
            raise serializers.ValidationError("Reply must be to a comment on the same book.")
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Ensure authenticated user for creating comments."""
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def replies(self, request, pk=None):
        """Get direct replies to this comment."""
        comment = self.get_object()
        replies = comment.replies.filter(is_deleted=False).order_by('created_at')[:50]  # Limit for scalability
        page = self.paginate_queryset(replies)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(replies, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def top_level(self, request):
        """Get top-level comments for a book (no parent)."""
        book_id = request.query_params.get('book')
        if not book_id:
            return Response({'error': 'Book ID required.'}, status=status.HTTP_400_BAD_REQUEST)
        comments = self.get_queryset().filter(book_id=book_id, parent__isnull=True)
        page = self.paginate_queryset(comments)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(comments, many=True, context={'request': request})
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """Only allow comment owner to update."""
        instance = self.get_object()
        if instance.user != request.user:
            return Response({'error': 'You can only edit your own comments.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)
    def destroy(self, request, *args, **kwargs):
        """Only allow comment owner to delete."""
        instance = self.get_object()
        if instance.user != request.user:
            return Response({'error': 'You can only delete your own comments.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)