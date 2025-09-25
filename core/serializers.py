from rest_framework import serializers
from .models import Author, Publisher, Category, Book, BookFormat, Comment
from django.contrib.auth import get_user_model

User = get_user_model()

class AuthorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = Author
        fields = ['id', 'first_name', 'last_name', 'full_name', 'email', 'date_of_birth', 'date_of_death', 'bio']

class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ['id', 'name', 'address', 'email', 'phone', 'website', 'logo']

class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), allow_null=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'description']

class BookFormatSerializer(serializers.ModelSerializer):
    format_type = serializers.ChoiceField(choices=BookFormat.FormatTypes.choices)
    
    def validate(self, data):
        format_type = data.get('format_type')
        pdf_file = data.get('pdf_file')
        
        if format_type == BookFormat.FormatTypes.PDF and not pdf_file:
            raise serializers.ValidationError("pdf_file is required for PDF format.")
        if format_type != BookFormat.FormatTypes.PDF and pdf_file:
            raise serializers.ValidationError("pdf_file should only be provided for PDF format.")
        return data
    
    class Meta:
        model = BookFormat
        fields = ['id', 'book', 'format_type', 'price', 'stock', 'pdf_file']

# Lightweight serializer for comment summaries
class CommentSummarySerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'user', 'content', 'created_at']

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    replies = serializers.SerializerMethodField()
    
    def get_replies(self, obj):
        """Recursively serialize replies, limiting depth to avoid performance issues."""
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all()[:10], many=True, context=self.context).data
        return []
    
    def validate_parent(self, value):
        """Ensure parent comment belongs to the same book."""
        if value and value.book != self.initial_data.get('book'):
            raise serializers.ValidationError("Parent comment must belong to the same book.")
        return value
    
    class Meta:
        model = Comment
        fields = ['id', 'book', 'user', 'content', 'parent', 'replies', 'created_at']
        read_only_fields = ['id','user', 'created_at']
    
    def create(self, validated_data):
        """Set the user from the request context."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

# Lightweight serializers for nested data
class AuthorSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = Author
        fields = ['id', 'full_name']

class PublisherSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ['id', 'name']

class CategorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class BookFormatSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookFormat
        fields = ['id', 'format_type', 'price', 'stock']

# Optimized list serializer - minimal data for performance
class BookListSerializer(serializers.ModelSerializer):
    author = AuthorSummarySerializer(read_only=True)
    publisher = PublisherSummarySerializer(read_only=True)
    category = CategorySummarySerializer(read_only=True)
    formats_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    min_price = serializers.SerializerMethodField()
    available_formats = serializers.SerializerMethodField()
    
    def get_formats_count(self, obj):
        """Get count of available formats."""
        return obj.formats.filter(is_deleted=False).count()
    
    def get_comments_count(self, obj):
        """Get count of comments."""
        return obj.comments.filter(is_deleted=False).count()
    
    def get_min_price(self, obj):
        """Get minimum price across all formats."""
        formats = obj.formats.filter(is_deleted=False)
        if formats.exists():
            return min(f.price for f in formats)
        return None
    
    def get_available_formats(self, obj):
        """Get list of available format types."""
        return list(obj.formats.filter(is_deleted=False, stock__gt=0).values_list('format_type', flat=True).distinct())
    
    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'publisher', 'category', 
            'publication_date', 'formats_count', 'comments_count',
            'min_price', 'available_formats', 'created_at'
        ]
        read_only_fields = ['created_at']

# Detailed serializer - full data for single book view
class BookDetailSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    publisher = PublisherSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    formats = BookFormatSerializer(many=True, read_only=True)
    recent_comments = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()  # If you add ratings later
    
    def get_recent_comments(self, obj):
        """Get recent top-level comments (non-replies) for preview."""
        recent_comments = obj.comments.filter(
            is_deleted=False, 
            parent__isnull=True
        ).order_by('-created_at')[:5]
        return CommentSummarySerializer(recent_comments, many=True).data
    
    def get_comments_count(self, obj):
        """Get total count of all comments (including replies)."""
        return obj.comments.filter(is_deleted=False).count()
    
    def get_average_rating(self, obj):
        """Placeholder for future rating system."""
        # You can implement this when you add a rating system
        return None
    
    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'description', 'publication_date',
            'publisher', 'category', 'formats', 'recent_comments',
            'comments_count', 'average_rating', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_author(self, value):
        """Ensure author is not soft-deleted."""
        if hasattr(value, 'is_deleted') and value.is_deleted:
            raise serializers.ValidationError("Cannot assign a deleted author to a book.")
        return value
    
    def validate_publisher(self, value):
        """Ensure publisher is not soft-deleted."""
        if hasattr(value, 'is_deleted') and value.is_deleted:
            raise serializers.ValidationError("Cannot assign a deleted publisher to a book.")
        return value

# Create/Update serializer - for write operations
class BookCreateUpdateSerializer(serializers.ModelSerializer):
    author_id = serializers.UUIDField(write_only=True)
    publisher_id = serializers.UUIDField(write_only=True)
    category_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Book
        fields = [
            'id', 'title', 'description', 'publication_date',
            'author_id', 'publisher_id', 'category_id'
        ]
        read_only_fields = ['id']
    
    def validate_author_id(self, value):
        """Ensure author exists and is not soft-deleted."""
        try:
            author = Author.objects.get(id=value)
            if hasattr(author, 'is_deleted') and author.is_deleted:
                raise serializers.ValidationError("Cannot assign a deleted author to a book.")
            return value
        except Author.DoesNotExist:
            raise serializers.ValidationError("Author does not exist.")
    
    def validate_publisher_id(self, value):
        """Ensure publisher exists and is not soft-deleted."""
        try:
            publisher = Publisher.objects.get(id=value)
            if hasattr(publisher, 'is_deleted') and publisher.is_deleted:
                raise serializers.ValidationError("Cannot assign a deleted publisher to a book.")
            return value
        except Publisher.DoesNotExist:
            raise serializers.ValidationError("Publisher does not exist.")
    
    def validate_category_id(self, value):
        """Ensure category exists if provided."""
        if value is not None:
            try:
                Category.objects.get(id=value)
                return value
            except Category.DoesNotExist:
                raise serializers.ValidationError("Category does not exist.")
        return value
    
    def create(self, validated_data):
        author_id = validated_data.pop('author_id')
        publisher_id = validated_data.pop('publisher_id')
        category_id = validated_data.pop('category_id', None)
        
        validated_data['author_id'] = author_id
        validated_data['publisher_id'] = publisher_id
        if category_id:
            validated_data['category_id'] = category_id
            
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        if 'author_id' in validated_data:
            instance.author_id = validated_data.pop('author_id')
        if 'publisher_id' in validated_data:
            instance.publisher_id = validated_data.pop('publisher_id')
        if 'category_id' in validated_data:
            instance.category_id = validated_data.pop('category_id')
            
        return super().update(instance, validated_data)
    

class BookSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='author.get_full_name')
    publisher = serializers.CharField(source='publisher.name')
    category = serializers.CharField(source='category.name', allow_null=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'publisher', 'category', 'publication_date', 'description']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if not representation['category']:
            representation['category'] = '-'  # Handle null category
        return representation