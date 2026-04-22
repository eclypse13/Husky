# dogs_module/urls.py
"""
URL маршруты для модуля собак

МАРШРУТЫ:
- /api/dogs/ - DogViewSet (CRUD)
- /api/breeders/ - BreederViewSet
- /api/owners/ - OwnerViewSet
- /api/titles/ - TitleViewSet
- /api/litters/ - LitterViewSet
- /api/medical-records/ - MedicalRecordViewSet

МАРШРУТЫ (Zooportal):
- /api/dogs/import/zooportal/dog/ - Импорт одной собаки
- /api/dogs/import/zooportal/page/ - Импорт страницы поиска
- /api/dogs/import/zooportal/range/ - Импорт диапазона страниц
- /api/dogs/import/status/<task_id>/ - Статус задачи

МАРШРУТЫ (BreedArchive):
- POST /api/dogs/import/breedarchive/dog/ - Импорт одной собаки по UUID
- POST /api/dogs/import/breedarchive/recent/ - Импорт последних обновлений (API)
- POST /api/dogs/import/breedarchive/browse/ - Импорт через browse-страницу (Playwright)
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    # Существующие ViewSets
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
)


router = DefaultRouter()
router.register(r'dogs', DogViewSet, basename='dog')
router.register(r'breeders', BreederViewSet, basename='breeder')
router.register(r'owners', OwnerViewSet, basename='owner')
router.register(r'titles', TitleViewSet, basename='title')
router.register(r'litters', LitterViewSet, basename='litter')
router.register(r'medical-records', MedicalRecordViewSet, basename='medical-record')


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

    # COI
   path(
     'dogs/coi/recalculate/',
       RecalculateAllCoiView.as_view(),
       name='coi-recalculate-all'
   ),

]