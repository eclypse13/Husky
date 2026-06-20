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
from .models import Dog, Breeder, Owner, Title, MedicalRecord, ShowEvent, ShowResult
from .serializers import (
    DogListSerializer,
    DogDetailSerializer,
    BreederSerializer,
    OwnerSerializer,
    TitleSerializer,
    # LitterSerializer,
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
    ImportResultsForDateRangeSerializer,
    PhotoUploadBulkSerializer,
    PhotoBackfillHashesSerializer,
    PhotoBackfillHashesFromSourceSerializer,
)
from .utils.coi_calculator import calculate_coi, save_coi

logger = logging.getLogger(__name__)


# СОБАКИ
class DogViewSet(viewsets.ReadOnlyModelViewSet):
    # none() нужен DRF для роутера; реальный queryset строится в get_queryset через репозиторий
    queryset = Dog.objects.using('dogs_db').none()
    filter_backends = [SearchFilter, OrderingFilter]
    ordering_fields = ['rating', 'registered_name', 'id']

    def get_serializer_class(self):
        return DogListSerializer if self.action == 'list' else DogDetailSerializer

    def get_object(self):
        if self.action in ('retrieve', 'pedigree', 'calculate_coi'):
            from .repositories import dog_repository as dog_repo
            return dog_repo.get_detail(self.kwargs[self.lookup_field])
        return super().get_object()

    def get_queryset(self):
        from .repositories import dog_repository as dog_repo
        p = self.request.query_params

        def _int(key):
            v = p.get(key)
            try:
                return int(v) if v else None
            except (ValueError, TypeError):
                return None

        return dog_repo.search_filtered(
            search=p.get('q'),
            sex=_int('sex'),
            year=_int('year'),
            year_from=_int('year_from'),
            year_to=_int('year_to'),
            color=p.get('color'),
            kennel=p.get('kennel'),
            country=p.get('country'),
        )

    @action(detail=True, methods=['get'])
    def pedigree(self, request, pk=None):
        dog = self.get_object()
        generations = max(1, min(int(request.query_params.get('generations', 3)), 10))
        serializer = PedigreeSerializer(
            dog,
            context={'request': request, 'depth': generations, 'current_depth': 1}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def siblings(self, request, pk=None):
        from .repositories import dog_repository as dog_repo
        dog = self.get_object()
        siblings = dog_repo.get_siblings(dog)
        return Response(DogListSerializer(siblings, many=True).data)

    @action(detail=True, methods=['get'])
    def offspring(self, request, pk=None):
        from .repositories import dog_repository as dog_repo
        dog = self.get_object()
        qs = dog_repo.get_offspring(dog)
        return Response(DogListSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        from .repositories import dog_repository as dog_repo
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'Query parameter required'}, status=400)
        dogs = dog_repo.search_by_name(query)
        return Response(DogListSerializer(dogs, many=True).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        from .repositories import dog_repository as dog_repo
        return Response(dog_repo.get_overview_stats())

    @action(detail=False, methods=['get'])
    def hero(self, request):
        from django.core.cache import cache
        from .services.show_service import get_hero_dog

        data = cache.get('home:hero_dog')
        if data is None:
            dog = get_hero_dog()
            data = DogListSerializer(dog).data if dog else None
            cache.set('home:hero_dog', data, timeout=1800)
        return Response(data)

    @action(detail=True, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def calculate_coi(self, request, pk=None):
        dog = self.get_object()
        generations = max(1, min(int(request.data.get('generations', 5)), 10))
        use_ancestor_coi = bool(request.data.get('use_ancestor_coi', False))
        result = calculate_coi(dog, generations=generations, use_ancestor_coi=use_ancestor_coi)

        if not result.is_valid:
            return Response({'error': result.error, 'coi': None}, status=422)

        save_coi(dog, result)
        dog.refresh_from_db(using='dogs_db')

        return Response({
            'coi': result.coi,
            'coi_updated_on': dog.coi_updated_on,
            'generations': result.generations,
            'common_ancestors': result.common_ancestors,
            'total_ancestors_sire': result.total_ancestors_sire,
            'total_ancestors_dam': result.total_ancestors_dam,
            'ancestor_contributions': result.ancestor_contributions,
        })

    @action(detail=True, methods=['get'])
    def show_results(self, request, pk=None):
        from .repositories import show_repository as show_repo
        from .services.show_service import get_rating_period

        year = request.query_params.get('year')
        date_from = date_to = None
        if year:
            date_from, date_to = get_rating_period(int(year))

        qs = show_repo.get_results_for_dog(pk, date_from, date_to)
        return Response(ShowResultSerializer(qs, many=True).data)

    # Rating
    @action(detail=False, methods=['get'])
    def rating(self, request):
        from .services.show_service import get_rating_leaderboard, get_rating_year
        from .serializers import DogListSerializer
        nomination = request.query_params.get('nomination', 'main')
        year = request.query_params.get('year')
        rating_year = int(year) if year else get_rating_year()

        leaderboard = get_rating_leaderboard(nomination=nomination, rating_year=rating_year, limit=50)

        data = []
        for entry in leaderboard:
            row = DogListSerializer(entry['dog']).data
            row['points'] = entry['points']
            data.append(row)
        return Response(data)


# СПРАВОЧНИКИ

class BreederViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Breeder.objects.using('dogs_db').none()
    serializer_class = BreederSerializer


class OwnerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Owner.objects.using('dogs_db').none()
    serializer_class = OwnerSerializer


class TitleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Title.objects.using('dogs_db').none()
    serializer_class = TitleSerializer


# class LitterViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = Litter.objects.using('dogs_db').none()
#     serializer_class = LitterSerializer


class MedicalRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MedicalRecord.objects.using('dogs_db').none()
    serializer_class = MedicalRecordSerializer
    pagination_class = None

    def get_queryset(self):
        from .repositories import medical_record_repository as med_repo
        return med_repo.filter_records(
            dog_id=self.request.query_params.get('dog_id'),
            source=self.request.query_params.get('source'),
        )


# ВЫСТАВКИ

class ShowEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ShowEvent.objects.using('dogs_db').none()
    serializer_class = ShowEventSerializer

    def get_queryset(self):
        from .repositories import show_repository as show_repo
        return show_repo.search_events(
            year=self.request.query_params.get('year'),
            city=self.request.query_params.get('city'),
            show_type=self.request.query_params.get('show_type'),
            has_results=self.request.query_params.get('has_results') == '1',
        )

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """GET /api/dogs/shows/{id}/results/"""
        from .repositories import show_repository as show_repo
        event = self.get_object()
        results = show_repo.get_results_for_event(event)
        return Response(ShowResultSerializer(results, many=True).data)


# СТАТУС ЗАДАЧИ

class ImportTaskStatusView(APIView):

    @extend_schema(
        summary='Статус задачи',
        parameters=[OpenApiParameter('task_id', str, OpenApiParameter.PATH)],
        responses={200: OpenApiTypes.OBJECT},
        tags=['Status'],
    )
    def get(self, request, task_id):
        try:
            task_result = AsyncResult(task_id)
            response_data = {'task_id': task_id, 'status': task_result.status}

            if task_result.state == 'PENDING':
                response_data['message'] = 'Задача в очереди'
            elif task_result.state == 'PROGRESS':
                response_data['message'] = 'Выполняется'
                response_data['progress'] = task_result.info
            elif task_result.state == 'SUCCESS':
                response_data['message'] = 'Завершена'
                response_data['result'] = task_result.result
            elif task_result.state == 'FAILURE':
                response_data['message'] = 'Ошибка'
                response_data['error'] = str(task_result.info)

            return Response(response_data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


# ИМПОРТ — ZOOPORTAL

class ImportZooportalDogView(APIView):
    @extend_schema(summary='Импорт одной собаки', request=ImportZooportalDogSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Zooportal'])
    def post(self, request):
        ser = ImportZooportalDogSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        zoo_id = ser.validated_data['zooportal_id']
        from .tasks.tasks_zooportal import import_zooportal_dog_task
        task = import_zooportal_dog_task.apply_async(args=[zoo_id], countdown=1)
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
        d = ser.validated_data
        from .tasks.tasks_zooportal import import_zooportal_page_task
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
        d = ser.validated_data
        from .tasks.tasks_zooportal import import_zooportal_range_task
        task = import_zooportal_range_task.apply_async(
            args=[d['start_page'], d['end_page'], d.get('max_dogs_per_page', 11), d.get('delay', 2.0)],
            countdown=1,
        )
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f"Импорт страниц {d['start_page']}–{d['end_page']} запущен",
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


# ИМПОРТ — BREEDARCHIVE

class ImportBreedarchiveDogView(APIView):
    @extend_schema(summary='Импорт собаки из BA', request=ImportBreedarchiveDogSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import BreedArchive'])
    def post(self, request):
        ser = ImportBreedarchiveDogSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        d = ser.validated_data
        from .tasks.tasks_breedarchive import fetch_breedarchive_dog_task
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
        d = ser.validated_data
        from .tasks.tasks_breedarchive import fetch_full_pedigree_task
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
        d = ser.validated_data
        from .tasks.tasks_breedarchive import sync_breedarchive_recent_task
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
        from .tasks.tasks_breedarchive import sync_breedarchive_browse_task
        task = sync_breedarchive_browse_task.apply_async(args=[ser.validated_data['recent_days']])
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': 'Browse BA запущен',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


# ИМПОРТ — HYBRID

class ImportHybridDogView(APIView):
    @extend_schema(summary='Гибридный импорт собаки Zoo→BA', request=ImportHybridDogSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Hybrid'])
    def post(self, request):
        ser = ImportHybridDogSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        from .tasks.tasks_zooportal import import_hybrid_dog_task
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
        from .tasks.tasks_zooportal import import_hybrid_page_task
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
        from .tasks.tasks_zooportal import import_hybrid_range_task
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
        d = ser.validated_data
        from .tasks.tasks_breedarchive import import_hybrid_full_dog_task
        task = import_hybrid_full_dog_task.apply_async(kwargs={
            'zooportal_id': d['zooportal_id'],
            'generations': d.get('generations', 3),
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
        d = ser.validated_data
        from .tasks.tasks_breedarchive import import_hybrid_full_page_task
        task = import_hybrid_full_page_task.apply_async(kwargs={
            'page_num': d['page_num'],
            'max_dogs': d.get('max_dogs', 11),
            'generations': d.get('generations', 3),
            'delay': d.get('delay', 2.0),
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
        from .tasks.tasks_breedarchive import import_hybrid_full_range_task
        task = import_hybrid_full_range_task.apply_async(kwargs=ser.validated_data)
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': 'Полный гибридный импорт диапазона запущен',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


# ИМПОРТ — OFA

class ImportOFADogView(APIView):
    @extend_schema(summary='Импорт OFA для одной собаки', request=ImportOFADogSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['OFA'])
    def post(self, request):
        ser = ImportOFADogSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        d = ser.validated_data
        from .tasks.tasks_ofa import fetch_ofa_dog_task
        task = fetch_ofa_dog_task.apply_async(kwargs={
            'dog_id': d.get('dog_id'),
            'registered_name': d.get('registered_name'),
            'registration_number': d.get('registration_number'),
            'ofa_number': d.get('ofa_number'),
        }, countdown=1)
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f"OFA импорт запущен: dog_id={d.get('dog_id')}",
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportOFABulkByRegView(APIView):
    @extend_schema(summary='Bulk OFA по рег. номеру', request=ImportOFABulkByRegSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['OFA'])
    def post(self, request):
        ser = ImportOFABulkByRegSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        from .tasks.tasks_ofa import fetch_ofa_bulk_by_reg_task
        task = fetch_ofa_bulk_by_reg_task.apply_async(kwargs=ser.validated_data, countdown=1)
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': 'OFA bulk (рег. номер) запущен',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportOFABulkByNameView(APIView):
    @extend_schema(summary='Bulk OFA по имени', request=ImportOFABulkByNameSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['OFA'])
    def post(self, request):
        ser = ImportOFABulkByNameSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        from .tasks.tasks_ofa import fetch_ofa_bulk_by_name_task
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


# ИМПОРТ — ВЫСТАВКИ

class ImportShowListView(APIView):
    @extend_schema(summary='Найти выставки за дату', request=ImportShowListSerializer,
                   responses={202: OpenApiTypes.OBJECT}, tags=['Import Shows'])
    def post(self, request):
        ser = ImportShowListSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        date_str = ser.validated_data['date_str']
        from .tasks.tasks_shows import import_show_list_task
        task = import_show_list_task.apply_async(args=[date_str], countdown=1)
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
        d = ser.validated_data
        from .tasks.tasks_shows import import_show_results_task
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
        d = ser.validated_data
        from .tasks.tasks_shows import import_show_date_range_task
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
        from .tasks.tasks_shows import recalculate_ratings_task
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
        from .tasks.tasks_shows import process_all_pending_results_task
        task = process_all_pending_results_task.apply_async()
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': 'Линковка результатов запущена',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


# COI

class RecalculateAllCoiView(APIView):
    def post(self, request):
        from .tasks.tasks_coi import recalculate_all_coi_task
        generations = max(1, min(int(request.data.get('generations', 5)), 10))
        only_missing = bool(request.data.get('only_missing', True))
        use_ancestor_coi = bool(request.data.get('use_ancestor_coi', False))
        batch_size = max(10, min(int(request.data.get('batch_size', 100)), 500))
        task = recalculate_all_coi_task.apply_async(
            args=[generations, batch_size, only_missing, use_ancestor_coi]
        )
        return Response({
            'task_id': task.id, 'status': 'PENDING',
            'message': f'Пересчёт COI запущен: gen={generations}, only_missing={only_missing}',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


# ML / ПОДБОР ПАР

class BreedingPredictView(APIView):
    def get(self, request):
        from .services.ml_dog_service import predict_pair

        sire_id = request.query_params.get('sire_id')
        dam_id = request.query_params.get('dam_id')

        if not sire_id or not dam_id:
            return Response({'error': 'Нужны sire_id и dam_id'}, status=400)
        try:
            sire_id, dam_id = int(sire_id), int(dam_id)
        except ValueError:
            return Response({'error': 'sire_id и dam_id должны быть числами'}, status=400)

        result = predict_pair(sire_id, dam_id)
        if 'error' in result:
            return Response(result, status=503)
        return Response(result)


# Мероприятий/соревнования/выставки с Zooportal
class ImportShowsFullView(APIView):

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

        from .tasks.tasks_shows import import_shows_full_task
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

        from .tasks.tasks_shows import import_results_for_date_range_task
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


# Health поиск по медицинским тестам из БД
class HealthSearchView(APIView):
    """GET /api/dogs/health/search/"""

    def get(self, request):
        from .services.health_service import search_health_records, DEFAULT_PER_PAGE

        try:
            page = int(request.query_params.get("page", 1))
            per_page = int(request.query_params.get("per_page", DEFAULT_PER_PAGE))
        except ValueError:
            page, per_page = 1, DEFAULT_PER_PAGE

        return Response(search_health_records(
            q=request.query_params.get("q", "").strip(),
            registry=request.query_params.get("registry", "").strip(),
            conclusion=request.query_params.get("conclusion", "").strip(),
            page=page, per_page=per_page,
        ))


class HealthRegistriesView(APIView):
    """GET /api/dogs/health/registries/ — релевантные тесты, что есть в БД."""

    def get(self, request):
        from .services.health_service import get_available_registries
        return Response(get_available_registries())


class HealthStatsView(APIView):
    """GET /api/dogs/health/stats/ — статистика по тестам. Кэш 1 час."""

    def get(self, request):
        from .services.health_service import get_health_stats
        return Response(get_health_stats())


class DogHealthRecordsView(APIView):
    """GET /api/dogs/health/records/?dog_id=123"""

    def get(self, request):
        from .services.health_service import get_dog_health_records
        dog_id = request.query_params.get('dog_id')
        if not dog_id:
            return Response({"error": "dog_id required"}, status=400)
        try:
            return Response(get_dog_health_records(dog_id))
        except Exception as e:
            return Response({"error": str(e)}, status=500)


# Yandex Photo
class PhotoStatsView(APIView):
    @extend_schema(
        summary="Статистика фото на Яндекс.Диске",
        description=(
                "Синхронный GET — результат виден сразу, без Celery задачи.\n\n"
                "Возвращает:\n"
                "- total: сколько собак в БД\n"
                "- with_photo_url: есть photo_url (источник)\n"
                "- with_yadisk: уже залито на ЯД (есть photo_yadisk_path)\n"
                "- with_hash: есть photo_hash (дедупликация работает)\n"
                "- without_yadisk: осталось залить\n"
                "- placeholders: заглушки (совпадают с DEFAULT_PHOTO_HASHES)"
        ),
        responses={200: OpenApiTypes.OBJECT},
        tags=["Photos"],
    )
    def get(self, request):
        from .services.photo_service import get_photo_stats
        return Response(get_photo_stats())


class PhotoUploadBulkView(APIView):
    @extend_schema(
        summary="Bulk загрузка фото БД → Яндекс.Диск (BreedArchive)",
        description=(
                "Запускает Celery задачу. Скачивает photo_url с BreedArchive (HTTP) и заливает на ЯД.\n\n"
                "Сравнивает хэш файла — не перекачивает если фото не изменилось.\n\n"
                "Параметры:\n"
                "- id_from / id_to: диапазон dog_id для батчевой обработки\n"
                "- limit: сколько собак за один прогон (рекомендуется 500)\n"
                "- delay: пауза между загрузками (0.5с достаточно для BA)\n"
                "- only_without_yadisk: True = только новые, False = проверить все\n\n"
                "Только для BA-собак. Zoo-собаки требуют Playwright — используй /fetch-zoo/bulk/"
        ),
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
        description=(
                "Автоматически выбирает метод по источнику:\n"
                "- BA-собака (photo_url содержит breedarchive) → прямой HTTP запрос\n"
                "- Zoo-собака (photo_url содержит zooportal) → Playwright браузер\n\n"
                "Используй для точечного исправления когда bulk уже отработал."
        ),
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
        summary="Восстановить пути ЯД → БД (по именам файлов)",
        description=(
                "Сканирует папку disk:/dogs/photos/ на Яндекс.Диске.\n"
                "По имени файла (12345.jpg → dog_id=12345) обновляет photo_yadisk_path в БД.\n\n"
                "Когда использовать:\n"
                "- после ручной загрузки файлов на ЯД\n"
                "- после восстановления БД из бэкапа (пути сбились)\n"
                "- если photo_yadisk_path пустой у собак у которых фото на ЯД точно есть"
        ),
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
            "limit": min(d["limit"], 500),  # Playwright тяжёлый - макс 500
            "delay": max(d["delay"], 5.0),  # минимум 5с между тасками
        })
        return Response({
            "task_id": task.id,
            "status": "PENDING",
            "message": f"Zoo bulk Playwright запущен (limit={min(d['limit'], 100)})",
            "check_status_url": f"/api/dogs/import/status/{task.id}/",
        }, status=202)


class PhotoDeleteSingleView(APIView):
    @extend_schema(
        summary="Удалить фото одной собаки с Яндекс.Диска",
        responses={202: OpenApiTypes.OBJECT},
        tags=["Photos"],
    )
    def post(self, request, dog_id: int):
        from .tasks.tasks_photos import photo_delete_one
        task = photo_delete_one.apply_async(kwargs={"dog_id": dog_id})
        return Response({
            "task_id": task.id,
            "status": "PENDING",
            "message": f"Удаление фото dog_id={dog_id} запущено",
            "check_status_url": f"/api/dogs/import/status/{task.id}/",
        }, status=202)


class PhotoBackfillHashesView(APIView):
    @extend_schema(
        summary="Посчитать photo_hash из ЯД (для Zoo-собак)",
        description=(
                "Считает photo_hash для собак у которых есть photo_yadisk_path но нет hash.\n"
                "Скачивает файл с ЯД для вычисления hash.\n\n"
                "Используй для Zoo-собак — их фото нельзя повторно скачать с Zooportal напрямую,\n"
                "поэтому hash считается уже с сохранённого файла на ЯД.\n\n"
                "Для BA-собак удобнее /backfill-hashes-from-source/ — скачивает с оригинального URL.\n\n"
                "Повторяй пока scanned > 0 в ответе задачи."
        ),
        request=PhotoBackfillHashesSerializer,
        responses={202: OpenApiTypes.OBJECT},
        tags=["Photos"],
    )
    def post(self, request):
        from .tasks.tasks_photos import photo_backfill_hashes

        ser = PhotoBackfillHashesSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        d = ser.validated_data
        task = photo_backfill_hashes.apply_async(
            kwargs={
                "limit": d["limit"],
                "id_from": d["id_from"],
                "id_to": d.get("id_to"),
            }
        )
        return Response({
            "task_id": task.id,
            "status": "PENDING",
            "message": f"Backfill хэшей запущен (limit={d['limit']}, id={d['id_from']}–{d.get('id_to') or '∞'})",
            "check_status_url": f"/api/dogs/import/status/{task.id}/",
        }, status=202)


class PhotoBackfillHashesFromSourceView(APIView):
    @extend_schema(
        summary="Посчитать photo_hash из оригинального photo_url (BreedArchive)",
        description=(
                "Считает photo_hash напрямую с оригинального photo_url через HTTP.\n"
                "Не требует скачивания с ЯД — быстрее и дешевле по трафику.\n\n"
                "Применимость:\n"
                "- BreedArchive-собаки: скачивает по HTTP\n"
                "- Zoo-собаки: пропускаются (Zooportal блокирует прямые запросы)\n\n"
                "Для Zoo используй /backfill-hashes/ (скачивает с ЯД).\n\n"
                "Повторяй пока scanned > 0 в ответе задачи."
        ),
        request=PhotoBackfillHashesFromSourceSerializer,
        responses={202: OpenApiTypes.OBJECT},
        tags=["Photos"],
    )
    def post(self, request):
        from .tasks.tasks_photos import photo_backfill_hashes_from_source

        ser = PhotoBackfillHashesFromSourceSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        d = ser.validated_data
        task = photo_backfill_hashes_from_source.apply_async(
            kwargs={
                "limit": d["limit"],
                "id_from": d["id_from"],
                "id_to": d.get("id_to"),
            }
        )
        return Response({
            "task_id": task.id,
            "status": "PENDING",
            "message": (
                f"Backfill хешей из source запущен "
                f"(limit={d['limit']}, id={d['id_from']}–{d.get('id_to') or '∞'})"
            ),
            "check_status_url": f"/api/dogs/import/status/{task.id}/",
        }, status=202)


class PhotoCleanupPlaceholdersView(APIView):
    @extend_schema(
        summary="Удалить дефолтные заглушки с ЯД",
        description=(
                "Удаляет файлы с ЯД у которых photo_hash совпадает с DEFAULT_PHOTO_HASHES.\n"
                "Чистит photo_yadisk_path, photo_yadisk_url, photo_hash в БД.\n\n"
                "Перед запуском убедись что DEFAULT_PHOTO_HASHES в config/yadisk.py заполнен.\n"
                "Как получить hash заглушки:\n"
                "  1. Залей заглушку как фото любой собаки\n"
                "  2. Запусти /backfill-hashes/ для этой собаки\n"
                "  3. Скопируй photo_hash из БД в DEFAULT_PHOTO_HASHES"
        ),
        responses={202: OpenApiTypes.OBJECT},
        tags=["Photos"],
    )
    def post(self, request):
        from .tasks.tasks_photos import photo_cleanup_placeholders
        task = photo_cleanup_placeholders.apply_async()
        return Response({
            "task_id": task.id,
            "status": "PENDING",
            "message": "Очистка заглушек с ЯД запущена",
            "check_status_url": f"/api/dogs/import/status/{task.id}/",
        }, status=202)


class DogPhotoRawView(APIView):
    """/api/dogs/photos/<dog_id>/raw/ — постоянная ссылка, редирект на свежий href ЯД."""
    permission_classes = [AllowAny]

    def get(self, request, dog_id: int):
        from .services.photo_service import get_fresh_download_href
        from django.http import Http404
        from django.http import HttpResponseRedirect

        href = get_fresh_download_href(dog_id)
        if not href:
            raise Http404

        resp = HttpResponseRedirect(href)
        resp["Cache-Control"] = "public, max-age=86400"
        return resp


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
