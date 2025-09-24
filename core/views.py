from rest_framework import viewsets
from core.models import Book, Publisher, Author, BookFormat, Comment
from core.serializers import BookListSerializer, BookWriteSerializer, BookDetailSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions
from rest_framework.views import APIView

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookListSerializer

    def get_queryset(self):
        """Optimize queries based on the action."""
        queryset = super().get_queryset()
        if self.action == 'list':
            return queryset.select_related('publisher').prefetch_related('authors')
        if self.action == 'retrieve':
            return queryset.select_related('publisher').prefetch_related(
                'authors', 'formats', 'comments__user', 'comments__replies'
            )
        return queryset

    def get_serializer_class(self):
        """Choose serializer based on the action."""
        if self.action in ['create', 'update', 'partial_update']:
            return BookWriteSerializer
        if self.action == 'retrieve':
            return BookDetailSerializer
        return self.serializer_class # Default is BookListSerializer


class BookSearchView(APIView):
    def get(self, request):
        # 1. Get search query and filters from request URL
        # e.g., /api/search/?q=dune&has_pdf=true
        query = request.query_params.get('q', '')
        has_pdf_filter = request.query_params.get('has_pdf')

        # 2. Build the search query for Elasticsearch
        search = BookDocument.search()

        if query:
            # A "multi_match" query searches the 'query' string in multiple fields
            search = search.query(
                "multi_match",
                query=query,
                fields=['title', 'description', 'authors'],
                fuzziness='AUTO' # Handles typos
            )

        if has_pdf_filter:
            # A "filter" is faster than a query because it doesn't calculate relevance scores
            search = search.filter('term', has_pdf__raw=has_pdf_filter.lower() == 'true')

        # 3. Execute the search
        response = search.execute()

        # 4. Serialize the results for the API response
        # The response object contains the Book model instances
        book_ids = [hit.id for hit in response.hits]
        books = Book.objects.filter(id__in=book_ids).select_related('publisher').prefetch_related('authors')
        serializer = BookListSerializer(books, many=True)

        return Response(serializer.data)
