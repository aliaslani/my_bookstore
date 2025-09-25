## 1. Introduction
This project is a scalable backend for an online bookstore application, built using Django 5.2.6, Django REST Framework (DRF), and PostgreSQL 16. It supports over 300,000 books with features like e-book formats, threaded comments, full-text search, soft deletes, and table partitioning for performance optimization. The system is designed for high traffic, with caching (Redis), asynchronous tasks (Celery), and optimized queries.

### Key Features
- **Models**: Author, Publisher, Category, Book, BookFormat, Comment.
- **Soft Deletes**: All models (except Category) inherit from `BaseModel`, which includes `is_deleted` and `created_at` fields.
- **Partitioning**: Book and BookFormat tables partitioned by `created_at` (2023–2025) for scalability.
- **Full-Text Search**: Using `search_vector` fields with `GIN` indexes for efficient searches on titles, descriptions, bios, etc.
- **API Endpoints**: CRUD operations, search, filtering (e.g., by format, price, availability), and custom actions (e.g., comments, formats, replies).
- **Admin Interface**: Optimized for large datasets with custom displays, search, and filters.
- **Data Generation**: Script to insert fake data for testing (up to 300k books, 600k formats, 900k comments).
- **Security**: Token authentication, read-only for unauthenticated users.
- **Performance**: Pagination, batch operations, indexes, and connection pooling.

## 2. Setup and Installation
### Prerequisites
- Python 3.12.3
- PostgreSQL 16.10 (installed locally on Ubuntu 24.04)
- Redis (for caching and Celery)
- Virtual environment tools (e.g., `uv` or `venv`)

### Installation Steps
1. **Activate Virtual Environment**:
   ```bash
   source /path/to/root/.venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   uv add django==5.2.6 djangorestframework psycopg2-binary python-decouple django-redis celery faker django-debug-toolbar
   ```

3. **Configure `.env` File**:
   Create or update `/path/to/root/of/project/bookstore/.env`:
   ```plaintext
   SECRET_KEY=your-secret-key-here  # Generate with python -c "import secrets; print(secrets.token_urlsafe(50))"
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   DB_NAME=bookstore_db
   DB_USER=bookstore_user
   DB_PASSWORD=your-secure-password
   DB_HOST=localhost
   DB_PORT=5432
   REDIS_URL=redis://localhost:6379/1
   CELERY_BROKER_URL=redis://localhost:6379/1
   CELERY_RESULT_BACKEND=redis://localhost:6379/1
   SECURE_SSL_REDIRECT=False
   SESSION_COOKIE_SECURE=False
   CSRF_COOKIE_SECURE=False
   ```

4. **Configure PostgreSQL**:
   - Create user and database:
     ```bash
     sudo -u postgres psql
     ```
     ```sql
     CREATE USER bookstore_user WITH PASSWORD 'your-secure-password';
     CREATE DATABASE bookstore_db;
     GRANT ALL PRIVILEGES ON DATABASE bookstore_db TO bookstore_user;
     \c bookstore_db
     GRANT USAGE, CREATE ON SCHEMA public TO bookstore_user;
     GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bookstore_user;
     ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO bookstore_user;
     CREATE EXTENSION IF NOT EXISTS pg_trgm;
     \q
     ```
   - Verify connection:
     ```bash
     psql -h localhost -U bookstore_user -d bookstore_db
     ```

5. **Configure Redis**:
   - Install if needed:
     ```bash
     sudo apt-get install redis-server
     sudo systemctl start redis
     sudo systemctl enable redis
     ```
   - Test:
     ```bash
     redis-cli ping  # Expected: PONG
     ```

6. **Apply Migrations**:
   ```bash
   uv run manage.py makemigrations
   uv run manage.py migrate
   ```

7. **Create Superuser**:
   ```bash
   uv run manage.py createsuperuser
   ```

8. **Run the Server**:
   ```bash
   uv run manage.py runserver
   ```

   - API: `http://localhost:8000/books/`
   - Admin: `http://localhost:8000/admin/`

## 3. Database Configuration
- **Schema**: Uses partitioning for `core_book` and `core_bookformat` by `created_at` (2023–2025). Verify partitions:
  ```sql
  \d+ core_book
  ```
- **Soft Deletes**: `is_deleted` field; querysets filter `is_deleted=False` in views.
- **Full-Text Search**: `search_vector` fields with `GIN` indexes on `Book`, `Author`, `Publisher`, `Category`, `Comment`.
- **Maintenance**: Run `VACUUM ANALYZE` for performance:
  ```sql
  VACUUM ANALYZE core_comment;
  ```

## 4. API Endpoints
The API uses DRF with token authentication. Use curl for testing. All endpoints exclude soft-deleted records.

### Authentication
- Create token:
  ```bash
  curl -X POST -d "username=your_username&password=your_password" http://localhost:8000/api-auth/login/
  ```
- Use token: Add header `Authorization: Token your_token` to requests.

### Authors
- **List**: `GET /authors/`
  ```bash
  curl http://localhost:8000/authors/?limit=10
  ```
- **Detail**: `GET /authors/{id}/`
- **Create/Update/Delete**: POST/PUT/DELETE (authenticated)
- **Books by Author**: `GET /authors/{id}/books/`
  ```bash
  curl http://localhost:8000/authors/1/books/
  ```
- **Search**: `GET /authors/?search=john`

### Publishers
- **List**: `GET /publishers/`
  ```bash
  curl http://localhost:8000/publishers/?search=press
  ```
- **Detail**: `GET /publishers/{id}/`
- **Create/Update/Delete**: POST/PUT/DELETE (authenticated)
- **Books by Publisher**: `GET /publishers/{id}/books/`

### Categories
- **List**: `GET /categories/`
  ```bash
  curl http://localhost:8000/categories/?search=fiction
  ```
- **Detail**: `GET /categories/{id}/`
- **Create/Update/Delete**: POST/PUT/DELETE (authenticated)
- **Books in Category**: `GET /categories/{id}/books/`
- **Subcategories**: `GET /categories/{id}/subcategories/`

### Books
- **List**: `GET /books/`
  ```bash
  curl "http://localhost:8000/books/?limit=10&offset=0&format=PDF&available=true&min_price=10&max_price=50&publication_year=2024"
  ```
- **Detail**: `GET /books/{id}/`
- **Create/Update/Delete**: POST/PUT/DELETE (authenticated)
- **Search**: `GET /books/?search=john`
  ```bash
  curl "http://localhost:8000/books/?search=john"
  ```
- **Formats for Book**: `GET /books/{id}/formats/`
- **Comments for Book**: `GET /books/{id}/comments/`
- **Available Books**: `GET /books/available/`

### Book Formats
- **List**: `GET /formats/`
  ```bash
  curl "http://localhost:8000/formats/?book=1"
  ```
- **Detail**: `GET /formats/{id}/`
- **Create/Update/Delete**: POST/PUT/DELETE (authenticated)

### Comments
- **List**: `GET /comments/`
  ```bash
  curl "http://localhost:8000/comments/?book=1&parent=2&search=review"
  ```
- **Detail**: `GET /comments/{id}/`
- **Create/Update/Delete**: POST/PUT/DELETE (authenticated)
- **Replies for Comment**: `GET /comments/{id}/replies/`
- **Top-Level Comments for Book**: `GET /comments/top_level/?book=1`

### Global Search
- **Search Across Models**: `GET /search/?search=novel`
  ```bash
  curl "http://localhost:8000/search/?search=novel"
  ```
  Returns unified results with `type` (book/author/publisher/category), `data`, and `rank`.

## 5. Admin Interface
Access `http://localhost:8000/admin/` with superuser credentials.

- **Comment Admin**: Optimized with custom displays (`book_title`, `user_username`, `content_preview`), search using `search_vector`, filters (`is_deleted`, `created_at`), and inline replies. List view limited to 20 items.
- **Other Models**: Similar optimizations with soft delete actions (`soft_delete`, `restore`) and indexes for large datasets.
- **Performance Tip**: For ~900k comments, use search and filters to reduce queryset size. Verify with `EXPLAIN ANALYZE` in `psql`.

## 6. Search Functionality
- **Book Search**: `GET /books/?search=john` uses `search_vector` for title/author/description, sorted by rank.
- **Global Search**: `GET /search/?search=novel` searches across models, returning sorted results by rank.
- **Comment Search**: `GET /comments/?search=review` uses `search_vector` for content.
- **Admin Search**: Use the search bar in admin interfaces; results sorted by rank.

## 7. Performance Testing
- **Fake Data Insertion**: Use `uv run python insert_fake_data.py` (10k books default; scale to 300k in `main()`).
- **API Performance**:
  ```bash
  time curl "http://localhost:8000/books/?search=john&limit=50"
  ```
- **Database Queries**:
  ```sql
  EXPLAIN ANALYZE SELECT * FROM core_book WHERE search_vector @@ to_tsquery('english', 'john') ORDER BY ts_rank(search_vector, to_tsquery('english', 'john')) DESC LIMIT 50;
  ```
- **Load Testing**: Use Locust or ab:
  ```bash
  ab -n 100 -c 10 http://localhost:8000/books/?search=john
  ```
- **Partitioning Verification**: Check distribution:
  ```sql
  SELECT COUNT(*) FROM core_book_2023;
  ```

## 8. Fake Data Generation
- Script: `insert_fake_data.py`
- Run: `uv run python insert_fake_data.py`
- Features: Generates users, authors, publishers, categories, books, formats, comments with partitioning, soft deletes, and `search_vector` updates.
- Scale: Edit `num_books=300000` for full test (expect 30–90 minutes).

## 9. Troubleshooting
- **NoReverseMatch**: Ensure `urls.py` includes `debug_toolbar.urls` for `DEBUG=True`.
- **FieldError**: Verify `search_vector` fields in models and apply migrations.
- **Slow Admin**: Reduce `list_per_page`, remove unnecessary prefetch, add indexes.
- **Connection Errors**: Check `.env` and PostgreSQL logs (`sudo tail -f /var/log/postgresql/postgresql-16-main.log`).
- **Django Logs**: `tail -f /path/to/root/of/project/my_bookstore/logs/bookstore.log`.

