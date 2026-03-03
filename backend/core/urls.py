from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from .views import *
from . import admin_views

router = DefaultRouter()

# Публичные API
router.register(r'dict', ContentDictionaryViewSet, basename='content-dict')
router.register(r'news', NewsViewSet, basename='news')
router.register(r'pages', PageViewSet, basename='pages')
router.register(r'galleries', GalleryViewSet, basename='galleries')
router.register(r'events', EventViewSet, basename='events')
router.register(r'event-reports', EventReportViewSet, basename='event-reports')
router.register(r'judges', JudgeViewSet, basename='judges')
router.register(r'judge-details', JudgeDetailsViewSet, basename='judge-details')
router.register(r'club/documents', ClubDocumentViewSet, basename='club-documents')
router.register(r'club/stats', ClubStatsViewSet, basename='club-stats')
router.register(r'club/board', BoardMemberViewSet, basename='club-board')
router.register(r'working-groups', WorkingGroupViewSet, basename='working-groups')
router.register(r'breed/standards', BreedStandardViewSet, basename='breed-standards')
router.register(r'breed/articles', BreedArticleViewSet, basename='breed-articles')

# Личный кабинет
router.register(r'me/dogs', MyDogViewSet, basename='my-dogs')
router.register(r'me/kennels', MyKennelViewSet, basename='my-kennels')
router.register(r'me/litters', MyLitterViewSet, basename='my-litters')
router.register(r'me/applications', MyApplicationViewSet, basename='my-applications')
router.register(r'me/achievements', MyAchievementViewSet, basename='my-achievements')

urlpatterns = [

    # Auth
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    
    # Home
    path('home/', home_api, name='home'),
    
    # Profile
    path('me/', MyProfileViewSet.as_view({'get': 'me'}), name='profile'),
    path('me/profile/', MyProfileViewSet.as_view({'put': 'update_profile'}), name='update-profile'),
    
    # Router URLs
    path('', include(router.urls)),

    # Админка для MongoEngine моделей
    path('nkp-admin/', include(admin_views.get_admin_urls())),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
