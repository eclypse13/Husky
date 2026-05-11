# dogs_module/urls.py
"""
URL маршруты для модуля собак
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
    OFABreedingStatsSHView,
    BreedingPredictView,
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




]