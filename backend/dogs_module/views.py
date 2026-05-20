# dogs_module/views.py

import logging

from celery.result import AsyncResult
from drf_spectacular.openapi import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .config import HUSKY_REGISTRIES
from .models import Dog, Breeder, Owner, Title, Litter, MedicalRecord, ShowEvent, ShowResult
from .serializers import (
    DogListSerializer,
    DogDetailSerializer,
    BreederSerializer,
    OwnerSerializer,
    TitleSerializer,
    LitterSerializer,
    PedigreeSerializer,
    MedicalRecordSerializer,
    ShowEventSerializer,
    ShowResultSerializer,
    ImportZooportalDogSerializer,
    ImportZooportalPageSerializer,
    ImportZooportalRangeSerializer,
    ImportHybridDogSerializer,
    ImportHybridPageSerializer,
    ImportHybridRangeSerializer,
    ImportHybridFullDogSerializer,
    ImportHybridFullPageSerializer,
    ImportHybridFullRangeSerializer,
    ImportBreedarchiveDogSerializer,
    ImportBreedarchiveRecentSerializer,
    ImportBreedarchiveBrowseSerializer,
    ImportBreedarchiveFullPedigreeSerializer,
    ImportOFADogSerializer,
    ImportOFABulkByRegSerializer,
    ImportOFABulkByNameSerializer,
    ImportShowListSerializer,
    ImportShowResultsSerializer,
    ImportShowDateRangeSerializer,
    RecalculateRatingsSerializer,
    ImportShowsFullSerializer,
    ImportResultsForDateRangeSerializer, PhotoUploadBulkSerializer
)
from .tasks.tasks_zooportal import (
    import_zooportal_dog_task,
    import_zooportal_page_task,
    import_zooportal_range_task,
    import_hybrid_dog_task,
    import_hybrid_page_task,
    import_hybrid_range_task,
)
from .tasks.tasks_breedarchive import (
    fetch_breedarchive_dog_task,
    fetch_full_pedigree_task,
    sync_breedarchive_recent_task,
    sync_breedarchive_browse_task,
    import_hybrid_full_dog_task,
    import_hybrid_full_page_task,
    import_hybrid_full_range_task,
)
from .tasks.tasks_ofa import (
    fetch_ofa_dog_task,
    fetch_ofa_bulk_by_reg_task,
    fetch_ofa_bulk_by_name_task,
)
from .tasks.tasks_shows import (
    import_show_list_task,
    import_show_results_task,
    import_show_date_range_task,
    recalculate_ratings_task,
    import_shows_full_task,
    import_results_for_date_range_task, process_all_pending_results_task
)
from .utils.coi_calculator import calculate_coi, save_coi

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# СОБАКИ
# ──────────────────────────────────────────────────────────────────────────────

class DogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Dog.objects.using('dogs_db').all().order_by('-id')
    filter_backends = [SearchFilter, OrderingFilter]
    ordering_fields = ['rating', 'registered_name', 'id']

    def get_serializer_class(self):
        return DogListSerializer if self.action == 'list' else DogDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        search = self.request.query_params.get('q')
        if search:
            qs = qs.filter(registered_name__icontains=search)

        sex = self.request.query_params.get('sex')
        if sex:
            qs = qs.filter(sex=sex)

        year = self.request.query_params.get('year')
        if year:
            qs = qs.filter(year_of_birth=year)

        return qs.select_related('dam', 'sire')

    @action(detail=True, methods=['get'])
    def pedigree(self, request, pk=None):
        dog         = self.get_object()
        generations = max(1, min(int(request.query_params.get('generations', 3)), 10))
        serializer  = PedigreeSerializer(
            dog,
            context={'request': request, 'depth': generations, 'current_depth': 1}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def siblings(self, request, pk=None):
        dog      = self.get_object()
        siblings = Dog.objects.using('dogs_db').filter(
            dam=dog.dam, sire=dog.sire
        ).exclude(id=dog.id)
        return Response(DogListSerializer(siblings, many=True).data)

    @action(detail=True, methods=['get'])
    def offspring(self, request, pk=None):
        dog = self.get_object()
        if dog.sex == 1:
            qs = Dog.objects.using('dogs_db').filter(sire=dog)
        elif dog.sex == 2:
            qs = Dog.objects.using('dogs_db').filter(dam=dog)
        else:
            qs = Dog.objects.using('dogs_db').none()
        return Response(DogListSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'Query parameter required'}, status=400)
        dogs = Dog.objects.using('dogs_db').filter(registered_name__icontains=query)[:20]
        return Response(DogListSerializer(dogs, many=True).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        return Response({
            'total':            Dog.objects.using('dogs_db').count(),
            'males':            Dog.objects.using('dogs_db').filter(sex=1).count(),
            'females':          Dog.objects.using('dogs_db').filter(sex=2).count(),
            'breeders':         Breeder.objects.using('dogs_db').count(),
            'with_zooportal_id': Dog.objects.using('dogs_db').filter(zooportal_id__isnull=False).count(),
            'with_uuid':        Dog.objects.using('dogs_db').filter(uuid__isnull=False).count(),
        })

    @action(detail=True, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def calculate_coi(self, request, pk=None):
        dog             = self.get_object()
        generations     = max(1, min(int(request.data.get('generations', 5)), 10))
        use_ancestor_coi = bool(request.data.get('use_ancestor_coi', False))
        result          = calculate_coi(dog, generations=generations, use_ancestor_coi=use_ancestor_coi)

        if not result.is_valid:
            return Response({'error': result.error, 'coi': None}, status=422)

        save_coi(dog, result)
        dog.refresh_from_db(using='dogs_db')

        return Response({
            'coi':                    result.coi,
            'coi_updated_on':         dog.coi_updated_on,
            'generations':            result.generations,
            'common_ancestors':       result.common_ancestors,
            'total_ancestors_sire':   result.total_ancestors_sire,
            'total_ancestors_dam':    result.total_ancestors_dam,
            'ancestor_contributions': result.ancestor_contributions,
        })

    @action(detail=True, methods=['get'])
    def show_results(self, request, pk=None):
        from .services.show_service import get_rating_period, get_rating_year

        qs = ShowResult.objects.using('dogs_db').filter(dog_id=pk).select_related('event')

        year = request.query_params.get('year')
        if year:
            date_from, date_to = get_rating_period(int(year))
            qs = qs.filter(
                event__event_date__gte=date_from,
                event__event_date__lte=date_to,
            )

        # nomination фильтруем на фронте — возвращаем все
        qs = qs.order_by('-event__event_date')
        return Response(ShowResultSerializer(qs, many=True).data)

    # Rating
    @action(detail=False, methods=['get'])
    def rating(self, request):
        from .services.show_service import get_rating_leaderboard, get_rating_year
        nomination = request.query_params.get('nomination', 'main')
        year = request.query_params.get('year')
        rating_year = int(year) if year else get_rating_year()
        data = get_rating_leaderboard(nomination=nomination, rating_year=rating_year, limit=50)
        return Response(data)


# ──────────────────────────────────────────────────────────────────────────────
# СПРАВОЧНИКИ
# ──────────────────────────────────────────────────────────────────────────────

class BreederViewSet(viewsets.ReadOnlyModelViewSet):
    queryset         = Breeder.objects.using('dogs_db').all()
    serializer_class = BreederSerializer


class OwnerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset         = Owner.objects.using('dogs_db').all()
    serializer_class = OwnerSerializer


class TitleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Title.objects.using('dogs_db').all()
    serializer_class = TitleSerializer


class LitterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Litter.objects.using('dogs_db').all()
    serializer_class = LitterSerializer


class MedicalRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MedicalRecord.objects.using('dogs_db').all()
    serializer_class = MedicalRecordSerializer
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        dog_id = self.request.query_params.get('dog_id')
        source = self.request.query_params.get('source')
        if dog_id:
            qs = qs.filter(dog_id=dog_id)
        if source:
            qs = qs.filter(source=source)
        return qs.order_by('-test_date')


# ──────────────────────────────────────────────────────────────────────────────
# ВЫСТАВКИ
# ──────────────────────────────────────────────────────────────────────────────

class ShowEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/dogs/shows/              — список выставок
    GET /api/dogs/shows/{id}/         — одна выставка
    GET /api/dogs/shows/{id}/results/ — результаты выставки
    """
    queryset         = ShowEvent.objects.using('dogs_db').all().order_by('-event_date')
    serializer_class = ShowEventSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        year = self.request.query_params.get('year')
        if year:
            qs = qs.filter(event_date__year=year)

        city = self.request.query_params.get('city')
        if city:
            qs = qs.filter(city__icontains=city)

        show_type = self.request.query_params.get('show_type')
        if show_type:
            qs = qs.filter(show_type=show_type)

        has_results = self.request.query_params.get('has_results')
        if has_results == '1':
            qs = qs.filter(results_parsed_at__isnull=False)

        return qs

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """GET /api/dogs/shows/{id}/results/"""
        event   = self.get_object()
        results = ShowResult.objects.using('dogs_db').filter(event=event).select_related('dog')
        return Response(ShowResultSerializer(results, many=True).data)


# ──────────────────────────────────────────────────────────────────────────────
# СТАТУС ЗАДАЧИ
# ──────────────────────────────────────────────────────────────────────────────

class ImportTaskStatusView(APIView):

    @extend_schema(
        summary='Статус задачи',
        parameters=[OpenApiParameter('task_id', str, OpenApiParameter.PATH)],
        responses={200: OpenApiTypes.OBJECT},
        tags=['Status'],
    )
    def get(self, request, task_id):
        try:
            task_result   = AsyncResult(task_id)
            response_data = {'task_id': task_id, 'status': task_result.status}

            if task_result.state == 'PENDING':
                response_data['message'] = 'Задача в очереди'
            elif task_result.state == 'PROGRESS':
                response_data['message']  = 'Выполняется'
                response_data['progress'] = task_result.info
            elif task_result.state == 'SUCCESS':
                response_data['message'] = 'Завершена'
                response_data['result']  = task_result.result
            elif task_result.state == 'FAILURE':
                response_data['message'] = 'Ошибка'
                response_data['error']   = str(task_result.info)

            return Response(response_data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


# ──────────────────────────────────────────────────────────────────────────────
# ИМПОРТ — ZOOPORTAL
# ──────────────────────────────────────────────────────────────────────────────

class ImportZooportalDogView(APIView):
    @extend_schema(summary='Импорт одной собаки', request=ImportZooportalDogSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Zooportal'])
    def post(self, request):
        ser = ImportZooportalDogSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        zoo_id = ser.validated_data['zooportal_id']
        task   = import_zooportal_dog_task.apply_async(args=[zoo_id], countdown=1)
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f'Импорт собаки {zoo_id} запущен',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportZooportalPageView(APIView):
    @extend_schema(summary='Импорт страницы', request=ImportZooportalPageSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Zooportal'])
    def post(self, request):
        ser = ImportZooportalPageSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        d    = ser.validated_data
        task = import_zooportal_page_task.apply_async(
            args=[d['page_num'], d.get('max_dogs', 11), d.get('delay', 2.0)], countdown=1
        )
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f"Импорт страницы {d['page_num']} запущен",
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportZooportalRangeView(APIView):
    @extend_schema(summary='Импорт диапазона страниц', request=ImportZooportalRangeSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Zooportal'])
    def post(self, request):
        ser = ImportZooportalRangeSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        d    = ser.validated_data
        task = import_zooportal_range_task.apply_async(
            args=[d['start_page'], d['end_page'], d.get('max_dogs_per_page', 11), d.get('delay', 2.0)],
            countdown=1,
        )
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f"Импорт страниц {d['start_page']}–{d['end_page']} запущен",
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


# ──────────────────────────────────────────────────────────────────────────────
# ИМПОРТ — BREEDARCHIVE
# ──────────────────────────────────────────────────────────────────────────────

class ImportBreedarchiveDogView(APIView):
    @extend_schema(summary='Импорт собаки из BA', request=ImportBreedarchiveDogSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import BreedArchive'])
    def post(self, request):
        ser = ImportBreedarchiveDogSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        d    = ser.validated_data
        task = fetch_breedarchive_dog_task.apply_async(args=[d['uuid'], d.get('force_update', False)])
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f"Импорт BA {d['uuid']} запущен",
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportBreedarchiveFullPedigreeView(APIView):
    @extend_schema(summary='Полная родословная из BA', request=ImportBreedarchiveFullPedigreeSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import BreedArchive'])
    def post(self, request):
        ser = ImportBreedarchiveFullPedigreeSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        d    = ser.validated_data
        task = fetch_full_pedigree_task.apply_async(args=[d['uuid'], d.get('force_update', False)])
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f"Полная родословная BA {d['uuid']} запущена",
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportBreedarchiveRecentView(APIView):
    @extend_schema(summary='Последние обновления BA', request=ImportBreedarchiveRecentSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import BreedArchive'])
    def post(self, request):
        ser = ImportBreedarchiveRecentSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        d    = ser.validated_data
        task = sync_breedarchive_recent_task.apply_async(
            args=[d['pages_count'], d['start_page'], d['is_full_sync']]
        )
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': 'Синхронизация BA запущена',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportBreedarchiveBrowseView(APIView):
    @extend_schema(summary='Browse-страница BA', request=ImportBreedarchiveBrowseSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import BreedArchive'])
    def post(self, request):
        ser = ImportBreedarchiveBrowseSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        task = sync_breedarchive_browse_task.apply_async(args=[ser.validated_data['recent_days']])
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': 'Browse BA запущен',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


# ──────────────────────────────────────────────────────────────────────────────
# ИМПОРТ — HYBRID
# ──────────────────────────────────────────────────────────────────────────────

class ImportHybridDogView(APIView):
    @extend_schema(summary='Гибридный импорт собаки Zoo→BA', request=ImportHybridDogSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Hybrid'])
    def post(self, request):
        ser = ImportHybridDogSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        task = import_hybrid_dog_task.apply_async(kwargs=ser.validated_data, countdown=1)
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f"Гибридный импорт {ser.validated_data['zooportal_id']} запущен",
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportHybridPageView(APIView):
    @extend_schema(summary='Гибридный импорт страницы', request=ImportHybridPageSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Hybrid'])
    def post(self, request):
        ser = ImportHybridPageSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        task = import_hybrid_page_task.apply_async(kwargs=ser.validated_data, countdown=1)
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f"Гибридный импорт страницы {ser.validated_data['page_num']} запущен",
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportHybridRangeView(APIView):
    @extend_schema(summary='Гибридный импорт диапазона', request=ImportHybridRangeSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Hybrid'])
    def post(self, request):
        ser = ImportHybridRangeSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        task = import_hybrid_range_task.apply_async(kwargs=ser.validated_data, countdown=1)
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f"Гибридный импорт запущен",
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportHybridFullDogView(APIView):
    @extend_schema(summary='Гибридный импорт (все поколения)', request=ImportHybridFullDogSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Hybrid Full'])
    def post(self, request):
        ser = ImportHybridFullDogSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        d    = ser.validated_data
        task = import_hybrid_full_dog_task.apply_async(kwargs={
            'zooportal_id': d['zooportal_id'],
            'generations':  d.get('generations', 3),
            'force_update': d.get('force_update', False),
        })
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f"Полный гибридный импорт {d['zooportal_id']} запущен",
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportHybridFullPageView(APIView):
    @extend_schema(summary='Гибридный импорт страницы (все поколения)', request=ImportHybridFullPageSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Hybrid Full'])
    def post(self, request):
        ser = ImportHybridFullPageSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        d    = ser.validated_data
        task = import_hybrid_full_page_task.apply_async(kwargs={
            'page_num':   d['page_num'],
            'max_dogs':   d.get('max_dogs', 11),
            'generations': d.get('generations', 3),
            'delay':      d.get('delay', 2.0),
        })
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f"Полный гибридный импорт страницы {d['page_num']} запущен",
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportHybridFullRangeView(APIView):
    @extend_schema(summary='Гибридный импорт диапазона (все поколения)', request=ImportHybridFullRangeSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Hybrid Full'])
    def post(self, request):
        ser = ImportHybridFullRangeSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        task = import_hybrid_full_range_task.apply_async(kwargs=ser.validated_data)
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': 'Полный гибридный импорт диапазона запущен',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


# ──────────────────────────────────────────────────────────────────────────────
# ИМПОРТ — OFA
# ──────────────────────────────────────────────────────────────────────────────

class ImportOFADogView(APIView):
    @extend_schema(summary='Импорт OFA для одной собаки', request=ImportOFADogSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import OFA'])
    def post(self, request):
        ser = ImportOFADogSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        d    = ser.validated_data
        task = fetch_ofa_dog_task.apply_async(kwargs={
            'dog_id':              d.get('dog_id'),
            'registered_name':     d.get('registered_name'),
            'registration_number': d.get('registration_number'),
            'ofa_number':          d.get('ofa_number'),
        }, countdown=1)
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f"OFA импорт запущен: dog_id={d.get('dog_id')}",
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportOFABulkByRegView(APIView):
    @extend_schema(summary='Bulk OFA по рег. номеру', request=ImportOFABulkByRegSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import OFA'])
    def post(self, request):
        ser = ImportOFABulkByRegSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        task = fetch_ofa_bulk_by_reg_task.apply_async(kwargs=ser.validated_data, countdown=1)
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': 'OFA bulk (рег. номер) запущен',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportOFABulkByNameView(APIView):
    @extend_schema(summary='Bulk OFA по имени', request=ImportOFABulkByNameSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import OFA'])
    def post(self, request):
        ser = ImportOFABulkByNameSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        task = fetch_ofa_bulk_by_name_task.apply_async(kwargs=ser.validated_data, countdown=1)
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': 'OFA bulk (имя) запущен',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class OFABreedingStatsSHView(APIView):
    def get(self, request):
        from .services.ofa_service import get_breed_ofa_stats
        try:
            return Response(get_breed_ofa_stats())
        except Exception as e:
            logger.error(f"OFABreedingStatsSHView: {e}")
            return Response({'error': 'Не удалось получить статистику'}, status=503)


# ──────────────────────────────────────────────────────────────────────────────
# ИМПОРТ — ВЫСТАВКИ
# ──────────────────────────────────────────────────────────────────────────────

class ImportShowListView(APIView):
    @extend_schema(summary='Найти выставки за дату', request=ImportShowListSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Shows'])
    def post(self, request):
        ser = ImportShowListSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        date_str = ser.validated_data['date_str']
        task     = import_show_list_task.apply_async(args=[date_str], countdown=1)
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f'Поиск выставок за {date_str} запущен',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportShowResultsView(APIView):
    @extend_schema(summary='Импорт результатов выставки', request=ImportShowResultsSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Shows'])
    def post(self, request):
        ser = ImportShowResultsSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        d    = ser.validated_data
        task = import_show_results_task.apply_async(
            args=[d['show_id'], d.get('import_missing_dogs', True)], countdown=1
        )
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f"Импорт результатов выставки {d['show_id']} запущен",
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportShowDateRangeView(APIView):
    @extend_schema(summary='Импорт выставок за диапазон дат', request=ImportShowDateRangeSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Shows'])
    def post(self, request):
        ser = ImportShowDateRangeSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        d    = ser.validated_data
        task = import_show_date_range_task.apply_async(kwargs=d, countdown=1)
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f"Импорт выставок {d['date_from']} — {d['date_to']} запущен",
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class RecalculateRatingsView(APIView):
    @extend_schema(summary='Пересчёт рейтингов', request=RecalculateRatingsSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Shows'])
    def post(self, request):
        ser = RecalculateRatingsSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        year = ser.validated_data.get('year')
        task = recalculate_ratings_task.apply_async(args=[year])
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f'Пересчёт рейтингов за {"текущий год" if not year else year} запущен',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class LinkShowResultsView(APIView):
    @extend_schema(summary='Залинковать незалинкованные результаты с собаками',
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Shows'])
    def post(self, request):
        task = process_all_pending_results_task.apply_async()
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': 'Линковка результатов запущена',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


# ──────────────────────────────────────────────────────────────────────────────
# COI
# ──────────────────────────────────────────────────────────────────────────────

class RecalculateAllCoiView(APIView):
    def post(self, request):
        from .tasks.tasks_coi import recalculate_all_coi_task
        generations      = max(1, min(int(request.data.get('generations', 5)), 10))
        only_missing     = bool(request.data.get('only_missing', True))
        use_ancestor_coi = bool(request.data.get('use_ancestor_coi', False))
        batch_size       = max(10, min(int(request.data.get('batch_size', 100)), 500))
        task             = recalculate_all_coi_task.apply_async(
            args=[generations, batch_size, only_missing, use_ancestor_coi]
        )
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f'Пересчёт COI запущен: gen={generations}, only_missing={only_missing}',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


# ──────────────────────────────────────────────────────────────────────────────
# ML / ПОДБОР ПАР
# ──────────────────────────────────────────────────────────────────────────────

class BreedingPredictView(APIView):
    def get(self, request):
        from .services.ml_dog_service import get_dog_health_data, get_pair_data, get_breeding_recommendation
        from .services.ml_client import predict_breeding
        from .services.pedigree_service import calc_offspring_coi

        sire_id = request.query_params.get('sire_id')
        dam_id  = request.query_params.get('dam_id')

        if not sire_id or not dam_id:
            return Response({'error': 'Нужны sire_id и dam_id'}, status=400)
        try:
            sire_id, dam_id = int(sire_id), int(dam_id)
        except ValueError:
            return Response({'error': 'sire_id и dam_id должны быть числами'}, status=400)

        result = predict_breeding(
            get_dog_health_data(sire_id),
            get_dog_health_data(dam_id),
            get_pair_data(sire_id, dam_id),
        )
        if 'error' in result:
            return Response(result, status=503)

        offspring_coi = calc_offspring_coi(sire_id, dam_id)
        result['offspring_coi'] = offspring_coi
        result = get_breeding_recommendation(result, offspring_coi)
        return Response(result)


# ──────────────────────────────────────────────────────────────────────────────
# Мероприятий/соревнования/выставки с Zooportal
# ──────────────────────────────────────────────────────────────────────────────

class ImportShowsFullView(APIView):
    """
    POST /api/dogs/import/shows/full/

    Полный импорт выставок за дату или диапазон:
      1. Парсим список выставок
      2. Парсим результаты
      3. Импортируем собак (ждём завершения каждой)
      4. Линкуем результаты
      5. Пересчитываем рейтинги

    Задача может выполняться несколько часов — используй check_status_url
    для проверки готовности.
    """

    @extend_schema(
        summary='Полный импорт выставок (выставки + собаки + рейтинг)',
        request=ImportShowsFullSerializer,
        responses={202: OpenApiTypes.OBJECT},
        tags=['Import Shows'],
    )
    def post(self, request):

        ser = ImportShowsFullSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        date_from = ser.validated_data['date_from']
        date_to = ser.validated_data.get('date_to') or date_from

        task = import_shows_full_task.apply_async(
            kwargs={'date_from': date_from, 'date_to': date_to},
            countdown=1,
        )

        period = date_from if date_from == date_to else f"{date_from} — {date_to}"

        return Response({
            'task_id': task.id,
            'status': 'PENDING',
            'message': f'Полный импорт выставок за {period} запущен. '
                       f'Задача может занять несколько часов.',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportResultsForDateRangeView(APIView):
    """
    POST /api/dogs/import/shows/results/range/

    Смотрит в БД на таблицу show_event за указанный период,
    для каждой выставки без результатов парсит и сохраняет результаты.

    Пример:
      {"date_from": "01.01.2026", "date_to": "31.01.2026"}
      → найдёт все show_event за январь, для каждой спарсит результаты
    """

    @extend_schema(
        summary='Импорт результатов для выставок из БД за период',
        request=ImportResultsForDateRangeSerializer,
        responses={202: OpenApiTypes.OBJECT},
        tags=['Import Shows'],
    )
    def post(self, request):

        ser = ImportResultsForDateRangeSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        d = ser.validated_data
        date_from = d['date_from']
        date_to = d.get('date_to') or date_from
        period = date_from if date_from == date_to else f"{date_from} — {date_to}"

        task = import_results_for_date_range_task.apply_async(
            kwargs={
                'date_from': date_from,
                'date_to': date_to,
                'only_without_results': d['only_without_results'],
                'import_missing_dogs': d['import_missing_dogs'],
            },
            countdown=1,
        )

        return Response({
            'task_id': task.id,
            'status': 'PENDING',
            'message': f'Импорт результатов за {period} запущен',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


# ──────────────────────────────────────────────────────────────────────────────
# Health поиск по медицинским тестам из БД
# ──────────────────────────────────────────────────────────────────────────────
class HealthSearchView(APIView):
    """
    GET /api/dogs/health/search/
    """
    def get(self, request):
        from .models import Dog, MedicalRecord

        q          = request.query_params.get("q", "").strip()
        registry   = request.query_params.get("registry", "").strip()
        conclusion = request.query_params.get("conclusion", "").strip()
        try:
            page     = max(1, int(request.query_params.get("page", 1)))
            per_page = min(50, max(1, int(request.query_params.get("per_page", 20))))
        except ValueError:
            page, per_page = 1, 20

        qs = MedicalRecord.objects.using("dogs_db").filter(source="ofa")

        if registry:
            qs = qs.filter(registry__iexact=registry)

        if conclusion:
            qs = qs.filter(conclusion__icontains=conclusion)

        if q:
            dog_ids = list(
                Dog.objects.using("dogs_db")
                .filter(registered_name__icontains=q)
                .values_list("id", flat=True)[:500]
            )
            qs = qs.filter(dog_id__in=dog_ids)

        # Дедупликация: убираем одинаковые (dog_id, registry, ofa_number)
        qs = qs.order_by("dog_id", "registry", "ofa_number", "-test_date")

        # Используем distinct по ключевым полям
        from django.db.models import Max
        # Берём только последнюю запись для каждой пары (dog_id, registry, ofa_number)
        qs = qs.distinct()

        total  = qs.count()
        offset = (page - 1) * per_page
        records = list(
            qs.order_by("-test_date")[offset: offset + per_page]
            .values("id", "registry", "conclusion", "test_date",
                    "ofa_number", "dog_id")
        )

        dog_ids_page = {r["dog_id"] for r in records}
        dogs = {
            d["id"]: d["registered_name"]
            for d in Dog.objects.using("dogs_db")
            .filter(id__in=dog_ids_page)
            .values("id", "registered_name")
        }

        for r in records:
            r["dog_name"] = dogs.get(r["dog_id"], "—")
            # test_date — дата самого анализа из OFA
            r["test_date"] = r["test_date"].strftime("%d.%m.%Y") if r["test_date"] else None

        return Response({
            "count":    total,
            "page":     page,
            "per_page": per_page,
            "results":  records,
        })


class HealthRegistriesView(APIView):
    """
    GET /api/dogs/health/registries/
    Возвращает только те тесты которые реально есть в БД
    и входят в список релевантных для хаски.
    """
    def get(self, request):
        from .models import MedicalRecord
        from django.core.cache import cache

        cached = cache.get("health_registries_v2")
        if cached:
            return Response(cached)

        # Только те что есть в БД И входят в список хаски
        existing = set(
            MedicalRecord.objects.using("dogs_db")
            .filter(source="ofa")
            .values_list("registry", flat=True)
            .distinct()
        )

        # Сохраняем порядок из HUSKY_REGISTRIES
        registries = [r for r in HUSKY_REGISTRIES if r in existing]

        cache.set("health_registries_v2", registries, 3600)
        return Response(registries)


class HealthStatsView(APIView):
    """
    GET /api/dogs/health/stats/
    Статистика по медицинским тестам из БД. Кэш 1 час.
    """
    def get(self, request):
        from .models import Dog, MedicalRecord
        from django.core.cache import cache

        cached = cache.get("health_stats")
        if cached:
            return Response(cached)

        total_tests = MedicalRecord.objects.using("dogs_db").filter(source="ofa").count()

        dogs_with_tests = (
            MedicalRecord.objects.using("dogs_db")
            .filter(source="ofa")
            .values("dog_id")
            .distinct()
            .count()
        )

        clear_total = MedicalRecord.objects.using("dogs_db").filter(
            source="ofa",
            registry__in=["DEGENERATIVE MYELOPATHY", "PROGRESSIVE RETINAL ATROPHY",
                          "PRIMARY LENS LUXATION",
                          "JUVENILE LARYNGEAL PARALYSIS & POLYNEUROPATHY (LPP)"]
        ).count()

        clear_normal = MedicalRecord.objects.using("dogs_db").filter(
            source="ofa",
            registry__in=["DEGENERATIVE MYELOPATHY", "PROGRESSIVE RETINAL ATROPHY",
                          "PRIMARY LENS LUXATION",
                          "JUVENILE LARYNGEAL PARALYSIS & POLYNEUROPATHY (LPP)"],
            conclusion__icontains="CLEAR"
        ).count()

        pct_clear = round(clear_normal / clear_total * 100) if clear_total else 0

        registries_count = (
            MedicalRecord.objects.using("dogs_db")
            .filter(source="ofa")
            .values("registry")
            .distinct()
            .count()
        )

        stats = {
            "total_tests":    total_tests,
            "dogs_with_tests": dogs_with_tests,
            "pct_clear":      pct_clear,
            "registries":     registries_count,
        }

        cache.set("health_stats", stats, 3600)
        return Response(stats)


class DogHealthRecordsView(APIView):
    """GET /api/dogs/health/records/?dog_id=123"""
    def get(self, request):
        from .models import MedicalRecord
        dog_id = request.query_params.get('dog_id')
        if not dog_id:
            return Response({"error": "dog_id required"}, status=400)
        try:
            records = list(
                MedicalRecord.objects.using('dogs_db')
                .filter(dog_id=dog_id, source='ofa')
                .order_by('-test_date')
                .values('id', 'registry', 'conclusion', 'test_date', 'ofa_number')
            )
            for r in records:
                r['test_date'] = r['test_date'].strftime('%d.%m.%Y') if r['test_date'] else None
            return Response(records)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


# Yandex Photo

class PhotoStatsView(APIView):
    @extend_schema(
        summary="Статистика фото на Яндекс.Диске",
        responses={200: OpenApiTypes.OBJECT},
        tags=["Photos"],
    )
    def get(self, request):
        from .tasks.tasks_photos import photo_stats
        result = photo_stats.apply_async()
        return Response(result.get(timeout=30))


class PhotoUploadBulkView(APIView):
    @extend_schema(
        summary="Bulk загрузка фото БД → Яндекс.Диск",
        request=PhotoUploadBulkSerializer,
        responses={202: OpenApiTypes.OBJECT},
        tags=["Photos"],
    )
    def post(self, request):
        from .tasks.tasks_photos import photo_upload_bulk

        ser = PhotoUploadBulkSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        d = ser.validated_data

        task = photo_upload_bulk.apply_async(kwargs={
            "id_from": d["id_from"],
            "id_to": d.get("id_to"),
            "limit": d["limit"],
            "delay": d["delay"],
            "only_without_yadisk": d["only_without_yadisk"],
        })
        return Response({
            "task_id": task.id,
            "status": "PENDING",
            "message": f"Bulk загрузка фото запущена (limit={d['limit']})",
            "check_status_url": f"/api/dogs/import/status/{task.id}/",
        }, status=202)


class PhotoUploadSingleView(APIView):
    @extend_schema(
        summary="Загрузка фото одной собаки → Яндекс.Диск",
        responses={202: OpenApiTypes.OBJECT},
        tags=["Photos"],
    )
    def post(self, request, dog_id: int):
        from .tasks.tasks_photos import photo_upload_one
        task = photo_upload_one.apply_async(kwargs={"dog_id": dog_id})
        return Response({
            "task_id": task.id,
            "status": "PENDING",
            "message": f"Загрузка фото dog_id={dog_id} запущена",
            "check_status_url": f"/api/dogs/import/status/{task.id}/",
        }, status=202)


class PhotoSyncFromYaDiskView(APIView):
    @extend_schema(
        summary="Синхронизация путей ЯД → БД",
        responses={202: OpenApiTypes.OBJECT},
        tags=["Photos"],
    )
    def post(self, request):
        from .tasks.tasks_photos import photo_sync_yadisk_to_db
        task = photo_sync_yadisk_to_db.apply_async()
        return Response({
            "task_id": task.id,
            "status": "PENDING",
            "message": "Синхронизация ЯД → БД запущена",
            "check_status_url": f"/api/dogs/import/status/{task.id}/",
        }, status=202)


class PhotoFetchZooSingleView(APIView):
    @extend_schema(
        summary="Скачать Zoo фото одной собаки через Playwright → ЯД",
        description=(
                "Открывает страницу собаки на Zooportal через Playwright (авторизованный браузер), "
                "скачивает фото и загружает на Яндекс.Диск.\n\n"
                "Используй для Zoo собак у которых `photo_yadisk_url` пустой."
        ),
        responses={202: OpenApiTypes.OBJECT},
        tags=["Photos"],
    )
    def post(self, request, dog_id: int):
        from .tasks.tasks_photos import photo_fetch_zoo_via_playwright
        task = photo_fetch_zoo_via_playwright.apply_async(kwargs={"dog_id": dog_id})
        return Response({
            "task_id": task.id,
            "status": "PENDING",
            "message": f"Zoo Playwright фото dog_id={dog_id} запущено",
            "check_status_url": f"/api/dogs/import/status/{task.id}/",
        }, status=202)


class PhotoFetchZooBulkView(APIView):
    @extend_schema(
        summary="Bulk скачивание Zoo фото через Playwright → ЯД",
        description=(
                "Диспатчит таски для всех Zoo собак у которых нет `photo_yadisk_url`.\n\n"
                "Каждая таска открывает Playwright браузер — используй `delay=5.0` минимум."
        ),
        request=PhotoUploadBulkSerializer,
        responses={202: OpenApiTypes.OBJECT},
        tags=["Photos"],
    )
    def post(self, request):
        from .tasks.tasks_photos import photo_fetch_zoo_bulk
        from .serializers import PhotoUploadBulkSerializer

        ser = PhotoUploadBulkSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        d = ser.validated_data

        task = photo_fetch_zoo_bulk.apply_async(kwargs={
            "id_from": d["id_from"],
            "id_to": d.get("id_to"),
            "limit": min(d["limit"], 100),  # Playwright тяжёлый - макс 100
            "delay": max(d["delay"], 5.0),  # минимум 5с между тасками
        })
        return Response({
            "task_id": task.id,
            "status": "PENDING",
            "message": f"Zoo bulk Playwright запущен (limit={min(d['limit'], 100)})",
            "check_status_url": f"/api/dogs/import/status/{task.id}/",
        }, status=202)



# dog breed stats
class PopulationStatsView(APIView):
    @extend_schema(
        summary='Популяционная аналитика породы',
        description='Возвращает статистику по всем собакам в базе. Кешируется на 6 часов.',
        responses={200: OpenApiTypes.OBJECT},
        tags=['Analytics'],
    )
    def get(self, request):
        from .services.stats_service import get_population_stats
        try:
            data = get_population_stats()
            return Response(data)
        except Exception as e:
            logger.error(f"PopulationStatsView: {e}", exc_info=True)
            return Response({"error": "Ошибка получения статистики"}, status=500)