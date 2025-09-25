from django.contrib import admin
from accounts.models import CustomUser
from django.contrib.auth.admin import UserAdmin
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_deleted', 'created_at']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'search_vector']
    list_filter = ['is_active', 'is_deleted', 'created_at']
    list_per_page = 20
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'bio', 'phone_number', 'address', 'profile_picture')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
        ('Status', {'fields': ('is_deleted',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'first_name', 'last_name', 'bio', 'phone_number', 'address', 'profile_picture'),
        }),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request).filter(is_deleted=False)
        search_query = request.GET.get('q', '').strip()
        if search_query:
            search_q = SearchQuery(search_query, config='english')
            if 'search_vector' in [f.name for f in CustomUser._meta.get_fields()]:
                queryset = queryset.annotate(
                    rank=SearchRank('search_vector', search_q)
                ).filter(search_vector=search_q).order_by('-rank')
            else:
                queryset = queryset.annotate(
                    search_vector_temp=SearchVector('username', weight='A', config='english') +
                                      SearchVector('email', weight='A', config='english') +
                                      SearchVector('bio', weight='B', config='english'),
                    rank=SearchRank('search_vector_temp', search_q)
                ).filter(search_vector_temp=search_q).order_by('-rank')
        return queryset