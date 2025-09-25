import os
import random
import time
from datetime import datetime, timedelta
from faker import Faker
import django
import logging
from django.db.utils import ProgrammingError
from django.contrib.postgres.search import SearchVector, SearchQuery
from django.utils import timezone
# Configure Django settings first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookstore.settings')
django.setup()

# Now import Django models and libraries
from accounts.models import CustomUser
from core.models import Author, Publisher, Category, Book, BookFormat, Comment

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Faker
fake = Faker()

def create_users(num_users=50):
    """Create fake CustomUser instances for comments."""
    logger.info(f"Creating {num_users} users...")
    start_time = time.time()
    users = []
    for _ in range(num_users):
        username = fake.user_name()
        email = fake.email()
        password = fake.password()
        user, created = CustomUser.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': fake.first_name(),
                'last_name': fake.last_name(),
                'bio': fake.paragraph(nb_sentences=3),
                'phone_number': fake.phone_number(),
                'address': fake.address(),
                'is_active': True,
                'is_deleted': random.choice([False] * 9 + [True]),
                'created_at': fake.date_time_between(
                    start_date=datetime(2023, 1, 1),
                    end_date=datetime(2025, 12, 31),
                    tzinfo=timezone.get_current_timezone()
                )
            }
        )
        if created:
            user.set_password(password)
            user.save()
        users.append(user)
    update_user_search_vectors()
    end_time = time.time()
    logger.info(f"Created {len(users)} users in {end_time - start_time:.2f} seconds.")
    return CustomUser.objects.filter(is_deleted=False)

def update_user_search_vectors():
    """Update search_vector for all users in batches."""
    logger.info("Updating search_vector for users...")
    start_time = time.time()
    if 'search_vector' not in [f.name for f in CustomUser._meta.get_fields()]:
        logger.warning("search_vector field not found in CustomUser model. Skipping update.")
        return
    try:
        batch_size = 1000
        user_ids = CustomUser.objects.values_list('id', flat=True)
        total_users = len(user_ids)
        
        for i in range(0, total_users, batch_size):
            batch_ids = user_ids[i:i + batch_size]
            CustomUser.objects.filter(id__in=batch_ids).update(
                search_vector=SearchVector('username', weight='A', config='english') +
                             SearchVector('email', weight='A', config='english') +
                             SearchVector('bio', weight='B', config='english')
            )
            logger.info(f"Updated search_vector for {min(i + batch_size, total_users)} of {total_users} users...")
        end_time = time.time()
        logger.info(f"search_vector for users updated in {end_time - start_time:.2f} seconds.")
    except ProgrammingError as e:
        logger.error(f"Failed to update user search_vector: {str(e)}")

def update_author_search_vectors():
    """Update search_vector for all authors in batches."""
    logger.info("Updating search_vector for authors...")
    start_time = time.time()
    if 'search_vector' not in [f.name for f in Author._meta.get_fields()]:
        logger.warning("search_vector field not found in Author model. Skipping update.")
        return
    try:
        batch_size = 1000
        author_ids = Author.objects.values_list('id', flat=True)
        total_authors = len(author_ids)
        
        for i in range(0, total_authors, batch_size):
            batch_ids = author_ids[i:i + batch_size]
            Author.objects.filter(id__in=batch_ids).update(
                search_vector=SearchVector('first_name', weight='A', config='english') +
                             SearchVector('last_name', weight='A', config='english') +
                             SearchVector('bio', weight='B', config='english')
            )
            logger.info(f"Updated search_vector for {min(i + batch_size, total_authors)} of {total_authors} authors...")
        end_time = time.time()
        logger.info(f"search_vector for authors updated in {end_time - start_time:.2f} seconds.")
    except ProgrammingError as e:
        logger.error(f"Failed to update author search_vector: {str(e)}")

def create_authors(num_authors=1000):
    """Create fake authors."""
    logger.info(f"Creating {num_authors} authors...")
    start_time = time.time()
    authors = []
    for _ in range(num_authors):
        author = Author(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=80),
            date_of_death=fake.date_of_birth(minimum_age=18, maximum_age=80) if random.choice([True, False]) else None,
            bio=fake.paragraph(nb_sentences=3),
            is_deleted=random.choice([False] * 9 + [True]),
            created_at=fake.date_time_between(
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2025, 12, 31),
                tzinfo=timezone.get_current_timezone()
            )
        )
        authors.append(author)
    Author.objects.bulk_create(authors, batch_size=500, ignore_conflicts=True)
    update_author_search_vectors()
    end_time = time.time()
    logger.info(f"Authors created in {end_time - start_time:.2f} seconds.")
    return Author.objects.filter(is_deleted=False)

def update_publisher_search_vectors():
    """Update search_vector for all publishers in batches."""
    logger.info("Updating search_vector for publishers...")
    start_time = time.time()
    if 'search_vector' not in [f.name for f in Publisher._meta.get_fields()]:
        logger.warning("search_vector field not found in Publisher model. Skipping update.")
        return
    try:
        batch_size = 1000
        publisher_ids = Publisher.objects.values_list('id', flat=True)
        total_publishers = len(publisher_ids)
        
        for i in range(0, total_publishers, batch_size):
            batch_ids = publisher_ids[i:i + batch_size]
            Publisher.objects.filter(id__in=batch_ids).update(
                search_vector=SearchVector('name', weight='A', config='english') +
                             SearchVector('address', weight='B', config='english') +
                             SearchVector('email', weight='C', config='english')
            )
            logger.info(f"Updated search_vector for {min(i + batch_size, total_publishers)} of {total_publishers} publishers...")
        end_time = time.time()
        logger.info(f"search_vector for publishers updated in {end_time - start_time:.2f} seconds.")
    except ProgrammingError as e:
        logger.error(f"Failed to update publisher search_vector: {str(e)}")

def create_publishers(num_publishers=200):
    """Create fake publishers."""
    logger.info(f"Creating {num_publishers} publishers...")
    start_time = time.time()
    publishers = []
    for _ in range(num_publishers):
        publisher = Publisher(
            name=fake.company(),
            address=fake.address(),
            email=fake.email(),
            phone=fake.phone_number(),
            website=fake.url(),
            logo=None,
            is_deleted=random.choice([False] * 9 + [True]),
            created_at=fake.date_time_between(
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2025, 12, 31),
                tzinfo=timezone.get_current_timezone()
            )
        )
        publishers.append(publisher)
    Publisher.objects.bulk_create(publishers, batch_size=500, ignore_conflicts=True)
    update_publisher_search_vectors()
    end_time = time.time()
    logger.info(f"Publishers created in {end_time - start_time:.2f} seconds.")
    return Publisher.objects.filter(is_deleted=False)

def update_category_search_vectors():
    """Update search_vector for all categories in batches."""
    logger.info("Updating search_vector for categories...")
    start_time = time.time()
    if 'search_vector' not in [f.name for f in Category._meta.get_fields()]:
        logger.warning("search_vector field not found in Category model. Skipping update.")
        return
    try:
        batch_size = 1000
        category_ids = Category.objects.values_list('id', flat=True)
        total_categories = len(category_ids)
        
        for i in range(0, total_categories, batch_size):
            batch_ids = category_ids[i:i + batch_size]
            Category.objects.filter(id__in=batch_ids).update(
                search_vector=SearchVector('name', weight='A', config='english') +
                             SearchVector('description', weight='B', config='english')
            )
            logger.info(f"Updated search_vector for {min(i + batch_size, total_categories)} of {total_categories} categories...")
        end_time = time.time()
        logger.info(f"search_vector for categories updated in {end_time - start_time:.2f} seconds.")
    except ProgrammingError as e:
        logger.error(f"Failed to update category search_vector: {str(e)}")

def create_categories(num_categories=50):
    """Create fake categories with hierarchy."""
    logger.info(f"Creating {num_categories} categories...")
    start_time = time.time()
    categories = []
    for _ in range(num_categories):
        category = Category(
            name=fake.word().title() + " " + fake.word().title(),
            description=fake.sentence(nb_words=6),
            parent=None
        )
        categories.append(category)
    
    Category.objects.bulk_create(categories, batch_size=100, ignore_conflicts=True)
    
    # Set parent relationships
    created_categories = Category.objects.all()
    for i, category in enumerate(created_categories):
        if i % 3 == 0 and len(created_categories) > i + 1:
            category.parent = random.choice(created_categories[i + 1:])
            category.save()
    
    update_category_search_vectors()
    end_time = time.time()
    logger.info(f"Categories created in {end_time - start_time:.2f} seconds.")
    return Category.objects.all()

def update_book_search_vectors():
    """Update search_vector for all books in batches."""
    logger.info("Updating search_vector for books...")
    start_time = time.time()
    if 'search_vector' not in [f.name for f in Book._meta.get_fields()]:
        logger.warning("search_vector field not found in Book model. Skipping update.")
        return
    try:
        batch_size = 1000
        book_ids = Book.objects.values_list('id', flat=True)
        total_books = len(book_ids)
        
        for i in range(0, total_books, batch_size):
            batch_ids = book_ids[i:i + batch_size]
            Book.objects.filter(id__in=batch_ids).update(
                search_vector=SearchVector('title', weight='A', config='english') +
                             SearchVector('description', weight='B', config='english')
            )
            logger.info(f"Updated search_vector for {min(i + batch_size, total_books)} of {total_books} books...")
        end_time = time.time()
        logger.info(f"search_vector for books updated in {end_time - start_time:.2f} seconds.")
    except ProgrammingError as e:
        logger.error(f"Failed to update book search_vector: {str(e)}")

def create_books(authors, publishers, categories, num_books=10000):
    """Create fake books with partitioning support."""
    logger.info(f"Creating {num_books} books...")
    start_time = time.time()
    batch_size = 500
    books = []
    inserted_count = 0
    
    for i in range(num_books):
        created_year = random.choice([2023, 2024, 2025])
        created_at = fake.date_time_between(
            start_date=datetime(created_year, 1, 1),
            end_date=datetime(created_year, 12, 31),
            tzinfo=timezone.get_current_timezone()
        )
        publication_year = random.randint(1900, 2025)
        publication_date = datetime(publication_year, random.randint(1, 12), random.randint(1, 28))
        
        book = Book(
            title=f"{fake.word().title()} {fake.word().title()} {fake.word().title()}",
            author=random.choice(authors),
            description=fake.paragraph(nb_sentences=3),
            publication_date=publication_date,
            publisher=random.choice(publishers),
            category=random.choice(categories) if random.choice([True, False]) else None,
            created_at=created_at,
            is_deleted=random.choice([False] * 9 + [True])
        )
        books.append(book)
        
        if len(books) >= batch_size:
            Book.objects.bulk_create(books, batch_size=batch_size, ignore_conflicts=True)
            inserted_count += len(books)
            logger.info(f"Inserted {inserted_count} books...")
            books = []
    
    if books:
        Book.objects.bulk_create(books, batch_size=batch_size, ignore_conflicts=True)
        inserted_count += len(books)
    
    update_book_search_vectors()
    end_time = time.time()
    logger.info(f"Books created in {end_time - start_time:.2f} seconds. Total: {inserted_count}")
    return Book.objects.filter(is_deleted=False)

def create_book_formats(books, num_formats_per_book=2):
    """Create fake book formats."""
    num_formats = len(books) * num_formats_per_book
    logger.info(f"Creating ~{num_formats} book formats...")
    start_time = time.time()
    batch_size = 500
    formats = [BookFormat.FormatTypes.PHYSICAL, BookFormat.FormatTypes.PDF, 
               BookFormat.FormatTypes.EPUB, BookFormat.FormatTypes.AUDIO]
    book_formats = []
    inserted_count = 0
    
    for book in books:
        selected_formats = random.sample(formats, k=min(len(formats), num_formats_per_book))
        for format_type in selected_formats:
            created_year = random.choice([2023, 2024, 2025])
            created_at = fake.date_time_between(
                start_date=datetime(created_year, 1, 1),
                end_date=datetime(created_year, 12, 31),
                tzinfo=timezone.get_current_timezone()
            )
            
            book_format = BookFormat(
                book=book,
                format_type=format_type,
                price=round(random.uniform(5.99, 59.99), 2),
                stock=random.randint(0, 500),
                pdf_file=f"pdfs/{fake.file_name(extension='pdf')}" if format_type == BookFormat.FormatTypes.PDF else None,
                created_at=created_at,
                is_deleted=random.choice([False] * 9 + [True])
            )
            book_formats.append(book_format)
            
            if len(book_formats) >= batch_size:
                BookFormat.objects.bulk_create(book_formats, batch_size=batch_size, ignore_conflicts=True)
                inserted_count += len(book_formats)
                logger.info(f"Inserted {inserted_count} book formats...")
                book_formats = []
    
    if book_formats:
        BookFormat.objects.bulk_create(book_formats, batch_size=batch_size, ignore_conflicts=True)
        inserted_count += len(book_formats)
    
    end_time = time.time()
    logger.info(f"Book formats created in {end_time - start_time:.2f} seconds. Total: {inserted_count}")

def update_comment_search_vectors():
    """Update search_vector for all comments in batches."""
    logger.info("Updating search_vector for comments...")
    start_time = time.time()
    if 'search_vector' not in [f.name for f in Comment._meta.get_fields()]:
        logger.warning("search_vector field not found in Comment model. Skipping update.")
        return
    try:
        batch_size = 1000
        comment_ids = Comment.objects.values_list('id', flat=True)
        total_comments = len(comment_ids)
        
        for i in range(0, total_comments, batch_size):
            batch_ids = comment_ids[i:i + batch_size]
            Comment.objects.filter(id__in=batch_ids).update(
                search_vector=SearchVector('content', weight='A', config='english')
            )
            logger.info(f"Updated search_vector for {min(i + batch_size, total_comments)} of {total_comments} comments...")
        end_time = time.time()
        logger.info(f"search_vector for comments updated in {end_time - start_time:.2f} seconds.")
    except ProgrammingError as e:
        logger.error(f"Failed to update comment search_vector: {str(e)}")

def create_comments(books, users, num_comments_per_book=3):
    """Create fake comments with hierarchy."""
    num_comments = len(books) * num_comments_per_book
    logger.info(f"Creating ~{num_comments} comments...")
    start_time = time.time()
    batch_size = 500
    comments = []
    inserted_count = 0
    
    for book in books:
        for _ in range(num_comments_per_book):
            created_year = random.choice([2023, 2024, 2025])
            created_at = fake.date_time_between(
                start_date=datetime(created_year, 1, 1),
                end_date=datetime(created_year, 12, 31),
                tzinfo=timezone.get_current_timezone()
            )
            
            comment = Comment(
                book=book,
                user=random.choice(users),
                content=fake.paragraph(nb_sentences=2),
                parent=None,
                created_at=created_at,
                is_deleted=random.choice([False] * 9 + [True])
            )
            comments.append(comment)
            
            if len(comments) >= batch_size:
                Comment.objects.bulk_create(comments, batch_size=batch_size, ignore_conflicts=True)
                inserted_count += len(comments)
                logger.info(f"Inserted {inserted_count} comments...")
                comments = []
    
    if comments:
        Comment.objects.bulk_create(comments, batch_size=batch_size, ignore_conflicts=True)
        inserted_count += len(comments)
    
    # Add hierarchical replies
    created_comments = Comment.objects.filter(is_deleted=False)
    for i, comment in enumerate(created_comments):
        if i % 5 == 0 and len(created_comments) > i + 1:
            reply = Comment(
                book=comment.book,
                user=random.choice(users),
                content=fake.sentence(),
                parent=comment,
                created_at=comment.created_at + timedelta(days=random.randint(1, 30)),
                is_deleted=random.choice([False] * 9 + [True])
            )
            comments.append(reply)
            if len(comments) >= batch_size:
                Comment.objects.bulk_create(comments, batch_size=batch_size, ignore_conflicts=True)
                inserted_count += len(comments)
                logger.info(f"Inserted {inserted_count} comments (with replies)...")
                comments = []
    
    if comments:
        Comment.objects.bulk_create(comments, batch_size=batch_size, ignore_conflicts=True)
        inserted_count += len(comments)
    
    update_comment_search_vectors()
    end_time = time.time()
    logger.info(f"Comments created in {end_time - start_time:.2f} seconds. Total: {inserted_count}")

def main():
    """Main function to insert fake data."""
    try:
        logger.info("Starting fake data insertion...")
        
        # Create users
        users = create_users(num_users=50)
        
        # Create related objects
        authors = create_authors(num_authors=1000)
        publishers = create_publishers(num_publishers=200)
        categories = create_categories(num_categories=50)
        
        # Create books (10k for testing, scale to 300k later)
        books = create_books(authors, publishers, categories, num_books=10000)
        
        # Create book formats and comments
        create_book_formats(books, num_formats_per_book=2)
        create_comments(books, users, num_comments_per_book=3)
        
        logger.info("Fake data insertion completed successfully!")
        
        # Verify counts
        logger.info(f"Total Users: {CustomUser.objects.count()} (Active: {CustomUser.objects.filter(is_deleted=False).count()})")
        logger.info(f"Total Authors: {Author.objects.count()} (Active: {Author.objects.filter(is_deleted=False).count()})")
        logger.info(f"Total Publishers: {Publisher.objects.count()} (Active: {Publisher.objects.filter(is_deleted=False).count()})")
        logger.info(f"Total Categories: {Category.objects.count()}")
        logger.info(f"Total Books: {Book.objects.count()} (Active: {Book.objects.filter(is_deleted=False).count()})")
        logger.info(f"Total Book Formats: {BookFormat.objects.count()} (Active: {BookFormat.objects.filter(is_deleted=False).count()})")
        logger.info(f"Total Comments: {Comment.objects.count()} (Active: {Comment.objects.filter(is_deleted=False).count()})")
        
        # Test full-text search
        logger.info("Testing full-text search...")
        try:
            search_q = SearchQuery('book', config='english')
            search_results = Book.objects.filter(search_vector=search_q).count()
            logger.info(f"Books matching 'book': {search_results}")
        except Exception as e:
            logger.error(f"Search test failed: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error inserting fake data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()