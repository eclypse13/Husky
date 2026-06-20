# dogs_module/urls.py
"""
URL маршруты для модуля собак
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DogViewSet,
    BreederViewSet,
    OwnerViewSet,
    TitleViewSet,
    LitterViewSet,
    MedicalRecordViewSet,

    ImportZooportalDogView,
    ImportZooportalPageView,
    ImportZooportalRangeView,
    ImportTaskStatusView,

    ImportBreedarchiveDogView,
    ImportBreedarchiveRecentView,
    ImportBreedarchiveBrowseView, ImportHybridDogView, ImportHybridPageView, ImportHybridRangeView,
    RecalculateAllCoiView,
    ImportBreedarchiveFullPedigreeView,

    ImportHybridFullDogView,
    ImportHybridFullPageView,
    ImportHybridFullRangeView,

    ImportOFADogView,
    ImportOFABulkByRegView,
    ImportOFABulkByNameView,
    OFABreedingStatsSHView,
    BreedingPredictView,

    ShowEventViewSet,
    ImportShowListView,
    ImportShowResultsView,
    ImportShowDateRangeView,
    RecalculateRatingsView,
    LinkShowResultsView,
    ImportShowsFullView,
    ImportResultsForDateRangeView,
    HealthSearchView,
    HealthRegistriesView,
    HealthStatsView,
    DogHealthRecordsView,

    PhotoStatsView,
    PhotoUploadBulkView,
    PhotoUploadSingleView,
    PhotoSyncFromYaDiskView,
    PhotoFetchZooSingleView,
    PhotoFetchZooBulkView,
    PhotoDeleteSingleView,
    PhotoBackfillHashesView,
    PhotoCleanupPlaceholdersView,

    PopulationStatsView,
    PhotoBackfillHashesFromSourceView, DogPhotoRawView,
)

router = DefaultRouter()
router.register(r'dogs', DogViewSet, basename='dog')
router.register(r'breeders', BreederViewSet, basename='breeder')
router.register(r'owners', OwnerViewSet, basename='owner')
router.register(r'titles', TitleViewSet, basename='title')
router.register(r'litters', LitterViewSet, basename='litter')
router.register(r'medical-records', MedicalRecordViewSet, basename='medical-record')
router.register(r'shows', ShowEventViewSet, basename='show-event')

urlpatterns = [
    # Существующие маршруты (ViewSets)
    path('', include(router.urls)),

    # ZOOPORTAL
    path(
        'dogs/import/zooportal/dog/',
        ImportZooportalDogView.as_view(),
        name='import-zooportal-dog'
    ),
    path(
        'dogs/import/zooportal/page/',
        ImportZooportalPageView.as_view(),
        name='import-zooportal-page'
    ),
    path(
        'dogs/import/zooportal/range/',
        ImportZooportalRangeView.as_view(),
        name='import-zooportal-range'
    ),
    path(
        'dogs/import/status/<str:task_id>/',
        ImportTaskStatusView.as_view(),
        name='import-task-status'
    ),
    # BREEDARCHIVE
    path(
        'dogs/import/breedarchive/dog/',
        ImportBreedarchiveDogView.as_view(),
        name='import-breedarchive-dog'
    ),
    path(
        'dogs/import/breedarchive/recent/',
        ImportBreedarchiveRecentView.as_view(),
        name='import-breedarchive-recent'
    ),
    path(
        'dogs/import/breedarchive/browse/',
        ImportBreedarchiveBrowseView.as_view(),
        name='import-breedarchive-browse'
    ),
    path(
        'dogs/import/breedarchive/dog/full-pedigree/',
        ImportBreedarchiveFullPedigreeView.as_view(),
        name='import-breedarchive-full-pedigree',
    ),
    # breedarchive parse + some zooportal info
    path(
        'dogs/import/hybrid/dog/',
        ImportHybridDogView.as_view(),
        name='import-hybrid-dog',
    ),
    path(
        'dogs/import/hybrid/page/',
        ImportHybridPageView.as_view(),
        name='import-hybrid-page',
    ),
    path(
        'dogs/import/hybrid/range/',
        ImportHybridRangeView.as_view(),
        name='import-hybrid-range',
    ),
    path(
        'dogs/import/hybrid/full/dog/',
        ImportHybridFullDogView.as_view(),
        name='import-hybrid-full-dog',
    ),
    path(
        'dogs/import/hybrid/full/page/',
        ImportHybridFullPageView.as_view(),
        name='import-hybrid-full-page',
    ),
    path(
        'dogs/import/hybrid/full/range/',
        ImportHybridFullRangeView.as_view(),
        name='import-hybrid-full-range',
    ),

    # OFA
    path(
        'dogs/import/ofa/dog/',
        ImportOFADogView.as_view(),
        name='import-ofa-dog'
    ),
    path(
        'dogs/import/ofa/bulk/reg/',
        ImportOFABulkByRegView.as_view(),
        name='import-ofa-bulk-reg'
    ),
    path(
        'dogs/import/ofa/bulk/name/',
        ImportOFABulkByNameView.as_view(),
        name='import-ofa-bulk-name'
    ),
    path(
        'dogs/import/ofa/stats/siberian-husky/',
        OFABreedingStatsSHView.as_view(),
        name='breeding-stats'
    ),

    # COI
    path(
        'dogs/coi/recalculate/',
        RecalculateAllCoiView.as_view(),
        name='coi-recalculate-all'
    ),
    path(
        'dogs/breeding/predict/',
        BreedingPredictView.as_view(),
        name='breeding-predict'
    ),

    # ZOOPORTAL Shows (мероприятия)
    path('dogs/import/shows/list/', ImportShowListView.as_view(), name='import-show-list'),
    path('dogs/import/shows/results/', ImportShowResultsView.as_view(), name='import-show-results'),
    path('dogs/import/shows/range/', ImportShowDateRangeView.as_view(), name='import-show-range'),
    path('dogs/shows/recalculate-ratings/', RecalculateRatingsView.as_view(), name='recalculate-ratings'),
    path('dogs/shows/link-results/', LinkShowResultsView.as_view(), name='link-show-results'),
    path('dogs/import/shows/full/', ImportShowsFullView.as_view(), name='import-shows-full'),
    path(
        'dogs/import/shows/results/range/',
        ImportResultsForDateRangeView.as_view(),
        name='import-show-results-range',
    ),

    # Health поиск тестов
    path('dogs/health/search/', HealthSearchView.as_view(), name='health-search'),
    path('dogs/health/registries/', HealthRegistriesView.as_view(), name='health-registries'),
    path('dogs/health/stats/', HealthStatsView.as_view(), name='health-stats'),
    path('dogs/health/records/', DogHealthRecordsView.as_view(), name='dog-health-records'),

    # Yandex Disk Photo
    path('dogs/photos/stats/',
         PhotoStatsView.as_view(),
         name='photos-stats'),

    path('dogs/photos/upload/bulk/',
         PhotoUploadBulkView.as_view(),
         name='photos-upload-bulk'),

    path('dogs/photos/upload/<int:dog_id>/',
         PhotoUploadSingleView.as_view(),
         name='photos-upload-single'),

    path('dogs/photos/sync-from-yadisk/',
         PhotoSyncFromYaDiskView.as_view(),
         name='photos-sync-from-yadisk'),

    path('dogs/photos/<int:dog_id>/raw/', DogPhotoRawView.as_view(), name='dog-photo-raw'),

    # Yandex Disk Photo Zoo фото через Playwright
    path(
        'dogs/photos/fetch-zoo/<int:dog_id>/',
        PhotoFetchZooSingleView.as_view(),
        name='photos-fetch-zoo-single',
    ),
    path(
        'dogs/photos/fetch-zoo/bulk/',
        PhotoFetchZooBulkView.as_view(),
        name='photos-fetch-zoo-bulk',
    ),
    path('dogs/photos/delete/<int:dog_id>/',
         PhotoDeleteSingleView.as_view(),
         name='photos-delete-single'),
    path('dogs/photos/backfill-hashes/',
         PhotoBackfillHashesView.as_view(),
         name='photos-backfill-hashes'),
    path('dogs/photos/cleanup-placeholders/',
         PhotoCleanupPlaceholdersView.as_view(),
         name='photos-cleanup-placeholders'),

    path('dogs/photos/backfill-hashes-from-source/',
         PhotoBackfillHashesFromSourceView.as_view(),
         name='photos-backfill-hashes-from-source'),

    # dog breed stats
    path('dogs/stats/population/', PopulationStatsView.as_view(), name='population-stats'),
]
