# books/serializers.py
from rest_framework import serializers
from core.models import Author, Publisher, Category, Book, BookFormat, Comment


class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ['id', 'name', 'website', 'logo']

class AuthorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Author
        fields = ['id', 'full_name', 'bio', 'date_of_birth']


class RecursiveField(serializers.Serializer):

    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data

class CategorySerializer(serializers.ModelSerializer):

    children = RecursiveField(many=True, read_only=True, source='category_set')

    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'children']

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    replies = RecursiveField(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'content', 'created_at', 'parent', 'replies']
        read_only_fields = ['user', 'created_at', 'replies']

class BookFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookFormat
        fields = ['id', 'format_type', 'price', 'stock']


class BookListSerializer(serializers.ModelSerializer):
    """A lightweight serializer for list views."""
    authors = serializers.StringRelatedField(many=True)
    publisher = serializers.StringRelatedField()

    class Meta:
        model = Book
        fields = ['id', 'title', 'authors', 'publisher', 'publication_date']

class BookDetailSerializer(serializers.ModelSerializer):
    """A rich serializer for the detail view."""
    authors = AuthorSerializer(many=True, read_only=True)
    publisher = PublisherSerializer(read_only=True)
    formats = BookFormatSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'description', 'publication_date',
            'authors', 'publisher', 'formats', 'comments'
        ]


class BookWriteSerializer(serializers.ModelSerializer):
    """
    A simple serializer for creating/updating books using IDs.
    """
    authors = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(), many=True
    )
    publisher = serializers.PrimaryKeyRelatedField(
        queryset=Publisher.objects.all(), allow_null=True
    )

    class Meta:
        model = Book
        fields = ['title', 'description', 'publication_date', 'authors', 'publisher']
