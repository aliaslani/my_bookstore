# catalog/search.py
from typing import Optional
from django.db.models import QuerySet
from django.contrib.postgres.search import (
    SearchVector, SearchQuery, SearchRank, TrigramSimilarity
)
from core.models import Book

# fields & weights chosen for relevance: title A, author B, publisher C, description D, category C
DEFAULT_VECTOR = (
    SearchVector("title", weight="A", config="english")
    + SearchVector("author__first_name", weight="B", config="english")
    + SearchVector("author__last_name", weight="B", config="english")
    + SearchVector("publisher__name", weight="C", config="english")
    + SearchVector("category__name", weight="C", config="english")
    + SearchVector("description", weight="D", config="english")
)


class SearchService:
    """
    Encapsulate full-text search behavior and options.
    """

    @staticmethod
    def build_search_query(q: str):
        q = (q or "").strip()
        return SearchQuery(q, config="english") if q else None

    @staticmethod
    def annotate_vector(queryset: QuerySet):
        """Annotate the temporary search vector (useful for ad-hoc searching when search_vector column is missing)."""
        return queryset.annotate(_search_vector=DEFAULT_VECTOR)

    @staticmethod
    def full_text_search(
        queryset: QuerySet,
        q: Optional[str],
        use_materialized_vector: bool = True,
        trigram_fallback: bool = True,
    ) -> QuerySet:
        """
        Perform a ranked full-text search with optional trigram fallback.

        - If the model has a materialized `search_vector` column (preferred), use it.
        - Otherwise compute a temporary vector using DEFAULT_VECTOR.
        - If full-text returns no results and trigram_fallback=True, apply TrigramSimilarity on title/author/publisher.
        """

        q_obj = SearchService.build_search_query(q)
        if not q_obj:
            return queryset

        # Prefer materialized search_vector if it exists
        if use_materialized_vector and "search_vector" in [f.name for f in Book._meta.get_fields()]:
            qs = queryset.annotate(rank=SearchRank("search_vector", q_obj)).filter(search_vector=q_obj)
            qs = qs.order_by("-rank")
            # If no results and trigram allowed, fallback below
            if qs.exists() or not trigram_fallback:
                return qs
        else:
            # annotate temporary vector & rank
            qs = SearchService.annotate_vector(queryset).annotate(rank=SearchRank("_search_vector", q_obj)).filter(_search_vector=q_obj).order_by("-rank")
            if qs.exists() or not trigram_fallback:
                return qs

        # Trigram fallback: fuzzy match on title, author, publisher
        # This requires the pg_trgm extension. It does not use rank, but similarity score.
        try:
            # annotate similarity on some high-value fields and order by best similarity
            qs = (
                queryset
                .annotate(
                    sim_title=TrigramSimilarity("title", q),
                    sim_author=TrigramSimilarity("author__first_name", q) + TrigramSimilarity("author__last_name", q),
                    sim_publisher=TrigramSimilarity("publisher__name", q),
                )
                .annotate(similarity_rank=(  # weighted similarity
                    3 * models.F("sim_title") + 2 * models.F("sim_author") + 1 * models.F("sim_publisher")
                ))
                .filter(similarity_rank__gt=0.1)  # threshold you can tune
                .order_by("-similarity_rank")
            )
            return qs
        except Exception:
            # If TrigramSimilarity not available or throws, return the original empty queryset
            return queryset.none()
