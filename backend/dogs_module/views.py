# dogs_module/views.py
"""
API Views для модуля собак
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from celery.result import AsyncResult

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.openapi import OpenApiTypes
import httpx
from django.http import HttpResponse

from .models import Dog, Breeder, Owner, Title, Litter, MedicalRecord
from .serializers import (
    DogListSerializer,
    DogDetailSerializer,
    BreederSerializer,
    OwnerSerializer,
    TitleSerializer,
    LitterSerializer,
    PedigreeSerializer,
    MedicalRecordSerializer,
    ImportZooportalDogSerializer,
    ImportZooportalPageSerializer,
    ImportZooportalRangeSerializer, ImportHybridRangeSerializer, ImportHybridPageSerializer, ImportHybridDogSerializer,
)
from .tasks.tasks_zooportal import (
    import_zooportal_dog_task,
    import_zooportal_page_task,
    import_zooportal_range_task, import_hybrid_range_task, import_hybrid_page_task, import_hybrid_dog_task
)
from .tasks.tasks_breedarchive import (
    sync_breedarchive_recent_task,
    sync_breedarchive_browse_task,
    fetch_breedarchive_dog_task,
)

from .serializers import (
    ImportBreedarchiveDogSerializer,
    ImportBreedarchiveRecentSerializer,
    ImportBreedarchiveBrowseSerializer,
)
from .utils.coi_calculator import calculate_coi, save_coi

logger = logging.getLogger(__name__)

class DogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для собак
    """
    queryset = Dog.objects.using('dogs_db').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return DogListSerializer
        return DogDetailSerializer

    def get_queryset(self):
        """Фильтрация и поиск"""
        queryset = super().get_queryset()

        # Поиск по имени
        search = self.request.query_params.get('q', None)
        if search:
            queryset = queryset.filter(registered_name__icontains=search)

        # Фильтр по полу
        sex = self.request.query_params.get('sex', None)
        if sex:
            queryset = queryset.filter(sex=sex)

        # Фильтр по году рождения
        year = self.request.query_params.get('year', None)
        if year:
            queryset = queryset.filter(year_of_birth=year)

        return queryset.select_related('dam', 'sire')



    @action(detail=True, methods=['get'])
    def pedigree(self, request, pk=None):
        """
        Получить родословную собаки

        GET /api/dogs/{id}/pedigree/?generations=3
        """
        dog = self.get_object()
        generations = int(request.query_params.get('generations', 3))
        generations = max(1, min(generations, 10))  # clamp 1–10

        serializer = PedigreeSerializer(
            dog,
            context={
                'request': request,
                'depth': generations,
                'current_depth': 1,  # 1=корень, глубина считается от него
            }
        )
        return Response(serializer.data)



    @action(detail=True, methods=['get'])
    def siblings(self, request, pk=None):
        """
        Получить сиблингов собаки

        GET /api/dogs/{id}/siblings/
        """
        dog = self.get_object()

        siblings = Dog.objects.using('dogs_db').filter(
            dam=dog.dam,
            sire=dog.sire
        ).exclude(id=dog.id)

        serializer = DogListSerializer(siblings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def offspring(self, request, pk=None):
        """
        Получить потомков собаки

        GET /api/dogs/{id}/offspring/
        """
        dog = self.get_object()

        if dog.sex == 1:  # Кобель
            offspring = Dog.objects.using('dogs_db').filter(sire=dog)
        elif dog.sex == 2:  # Сука
            offspring = Dog.objects.using('dogs_db').filter(dam=dog)
        else:
            offspring = Dog.objects.using('dogs_db').none()

        serializer = DogListSerializer(offspring, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Поиск собак по имени

        GET /api/dogs/search/?q=NAME
        """
        query = request.query_params.get('q', '')

        if not query:
            return Response({'error': 'Query parameter required'}, status=400)

        dogs = Dog.objects.using('dogs_db').filter(
            registered_name__icontains=query
        )[:20]

        serializer = DogListSerializer(dogs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Статистика по собакам

        GET /api/dogs/stats/
        """
        total = Dog.objects.using('dogs_db').count()
        males = Dog.objects.using('dogs_db').filter(sex=1).count()
        females = Dog.objects.using('dogs_db').filter(sex=2).count()

        return Response({
            'total': total,
            'males': males,
            'females': females,
            'breeders': Breeder.objects.using('dogs_db').count(),
            'with_zooportal_id': Dog.objects.using('dogs_db').filter(
                zooportal_id__isnull=False
            ).count(),
            'with_uuid': Dog.objects.using('dogs_db').filter(
                uuid__isnull=False
            ).count()
        })

    @action(detail=True, methods=['post'])
    def calculate_coi(self, request, pk=None):
        """
        Рассчитывает и сохраняет COI для одной собаки.

        POST /api/dogs/{id}/calculate_coi/
        Body (всё опционально):
          {
            "generations": 5,           // 1–10, стандарт = 5
            "use_ancestor_coi": false   // учитывать F_A предков
          }

        Возвращает:
          {
            "coi": 6.25,
            "coi_updated_on": "2026-03-01T12:00:00Z",
            "generations": 5,
            "common_ancestors": 3,
            "total_ancestors_sire": 15,
            "total_ancestors_dam": 14,
            "ancestor_contributions": {"123": 3.125, "456": 1.5625}
          }
        """
        dog = self.get_object()
        generations = max(1, min(int(request.data.get('generations', 5)), 10))
        use_ancestor_coi = bool(request.data.get('use_ancestor_coi', False))

        logger.info(
            f"🧮 COI расчёт: {dog.registered_name} (id={dog.id}) | "
            f"gen={generations} | ancestor_coi={use_ancestor_coi}"
        )

        result = calculate_coi(dog, generations=generations, use_ancestor_coi=use_ancestor_coi)

        if not result.is_valid:
            return Response(
                {'error': result.error, 'coi': None},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

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


class ImportZooportalDogView(APIView):
    """Импорт одной собаки по ID из Zooportal"""

    @extend_schema(
        summary="Импорт одной собаки",
        description="Запускает асинхронный импорт собаки по её ID из Zooportal.",
        request=ImportZooportalDogSerializer,
        responses={
            202: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
        },
        tags=["Import Zooportal"],
    )
    def post(self, request):
        serializer = ImportZooportalDogSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        zooportal_id = serializer.validated_data['zooportal_id']
        logger.info(f"🚀 Запуск импорта собаки: {zooportal_id}")

        try:
            task = import_zooportal_dog_task.apply_async(args=[zooportal_id], countdown=1)
            return Response({
                'task_id': task.id,
                'status': 'PENDING',
                'message': f'Import started for dog {zooportal_id}',
                'check_status_url': f'/api/dogs/import/status/{task.id}/',
                'zooportal_id': zooportal_id
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return Response({'error': str(e)}, status=500)

class ImportZooportalPageView(APIView):
    """Импорт страницы поиска Zooportal"""

    @extend_schema(
        summary="Импорт страницы поиска",
        description="Импортирует всех собак с указанной страницы поиска Zooportal.",
        request=ImportZooportalPageSerializer,
        responses={
            202: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
        },
        tags=["Import Zooportal"],
    )
    def post(self, request):
        serializer = ImportZooportalPageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        page_num = serializer.validated_data['page_num']
        max_dogs = serializer.validated_data.get('max_dogs', 11)
        delay = serializer.validated_data.get('delay', 2.0)

        logger.info(f"📄 Запуск импорта страницы: {page_num}")

        try:
            task = import_zooportal_page_task.apply_async(args=[page_num, max_dogs, delay], countdown=1)
            return Response({
                'task_id': task.id,
                'status': 'PENDING',
                'message': f'Import started for page {page_num}',
                'check_status_url': f'/api/dogs/import/status/{task.id}/',
                'page_num': page_num,
                'max_dogs': max_dogs
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return Response({'error': str(e)}, status=500)

class ImportZooportalRangeView(APIView):
    """Импорт диапазона страниц Zooportal"""

    @extend_schema(
        summary="Импорт диапазона страниц",
        description="Импортирует собак из нескольких страниц поиска Zooportal.",
        request=ImportZooportalRangeSerializer,
        responses={
            202: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
        },
        tags=["Import Zooportal"],
    )
    def post(self, request):
        serializer = ImportZooportalRangeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        start_page = serializer.validated_data['start_page']
        end_page = serializer.validated_data['end_page']
        max_dogs_per_page = serializer.validated_data.get('max_dogs_per_page', 11)
        delay = serializer.validated_data.get('delay', 2.0)

        logger.info(f"📚 Запуск импорта диапазона: {start_page}-{end_page}")

        try:
            task = import_zooportal_range_task.apply_async(
                args=[start_page, end_page, max_dogs_per_page, delay],
                countdown=1
            )
            return Response({
                'task_id': task.id,
                'status': 'PENDING',
                'message': f'Import started for pages {start_page}-{end_page}',
                'check_status_url': f'/api/dogs/import/status/{task.id}/',
                'start_page': start_page,
                'end_page': end_page,
                'total_pages': end_page - start_page + 1
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return Response({'error': str(e)}, status=500)

class ImportTaskStatusView(APIView):
    """Проверка статуса задачи импорта"""

    @extend_schema(
        summary="Статус задачи импорта",
        description="Получить статус выполнения задачи по её ID.",
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="UUID задачи Celery",
                required=True,
            )
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
        },
        tags=["Status of Import Task"],
    )
    def get(self, request, task_id):
        logger.info(f"📊 Проверка статуса задачи: {task_id}")

        try:
            task_result = AsyncResult(task_id)
            response_data = {
                'task_id': task_id,
                'status': task_result.status
            }

            if task_result.state == 'PENDING':
                response_data['message'] = 'Task is waiting in queue'
            elif task_result.state == 'PROGRESS':
                response_data['message'] = 'Task is in progress'
                response_data['progress'] = task_result.info
            elif task_result.state == 'SUCCESS':
                response_data['message'] = 'Task completed successfully'
                response_data['result'] = task_result.result
            elif task_result.state == 'FAILURE':
                response_data['message'] = 'Task failed'
                response_data['error'] = str(task_result.info)
            else:
                response_data['message'] = f'Task state: {task_result.state}'

            return Response(response_data)
        except Exception as e:
            logger.error(f"❌ Ошибка проверки статуса: {e}")
            return Response({'error': str(e)}, status=500)


class BreederViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для заводчиков"""
    queryset = Breeder.objects.using('dogs_db').all()
    serializer_class = BreederSerializer


class OwnerViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для владельцев"""
    queryset = Owner.objects.using('dogs_db').all()
    serializer_class = OwnerSerializer


class TitleViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для титулов"""
    queryset = Title.objects.using('dogs_db').all()
    serializer_class = TitleSerializer


class LitterViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для помётов"""
    queryset = Litter.objects.using('dogs_db').all()
    serializer_class = LitterSerializer


class MedicalRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для медицинских записей"""
    queryset = MedicalRecord.objects.using('dogs_db').all()
    serializer_class = MedicalRecordSerializer

class ImportBreedarchiveDogView(APIView):
    """Импорт одной собаки из BreedArchive по UUID."""

    @extend_schema(
        summary="Импорт одной собаки из BreedArchive",
        request=ImportBreedarchiveDogSerializer,
        responses={202: OpenApiTypes.OBJECT},
        tags=["Import BreedArchive"],
    )
    def post(self, request):
        serializer = ImportBreedarchiveDogSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        uuid = serializer.validated_data['uuid']
        generations = serializer.validated_data.get('generations', 5)
        force_update = serializer.validated_data.get('force_update', False)

        task = fetch_breedarchive_dog_task.apply_async(args=[uuid, force_update])
        return Response({
            'task_id': task.id,
            'status': 'PENDING',
            'message': f'Import started for UUID {uuid}',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportBreedarchiveRecentView(APIView):
    """Импорт последних обновлённых собак из BreedArchive (operation=all)."""

    @extend_schema(
        summary="Импорт последних обновлений BreedArchive",
        request=ImportBreedarchiveRecentSerializer,
        responses={202: OpenApiTypes.OBJECT},
        tags=["Import BreedArchive"],
    )
    def post(self, request):
        serializer = ImportBreedarchiveRecentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        pages_count = serializer.validated_data['pages_count']
        start_page = serializer.validated_data['start_page']
        is_full_sync = serializer.validated_data['is_full_sync']

        task = sync_breedarchive_recent_task.apply_async(
            args=[pages_count, start_page, is_full_sync]
        )
        return Response({
            'task_id': task.id,
            'status': 'PENDING',
            'message': f'Recent sync started (pages={pages_count}, start={start_page}, full={is_full_sync})',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


class ImportBreedarchiveBrowseView(APIView):
    """Импорт собак, изменённых за последние N дней, через browse-страницу (Playwright)."""

    @extend_schema(
        summary="Импорт собак через browse-страницу BreedArchive",
        request=ImportBreedarchiveBrowseSerializer,
        responses={202: OpenApiTypes.OBJECT},
        tags=["Import BreedArchive"],
    )
    def post(self, request):
        serializer = ImportBreedarchiveBrowseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        recent_days = serializer.validated_data['recent_days']

        task = sync_breedarchive_browse_task.apply_async(args=[recent_days])
        return Response({
            'task_id': task.id,
            'status': 'PENDING',
            'message': f'Browse sync started for last {recent_days} days',
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=202)


# ---- hybrid

class ImportHybridDogView(APIView):

    @extend_schema(
        summary="Гибридный импорт одной собаки Zoo→BA",
        description=(
            "Zoo страница по zooportal_id → поиск в BA по имени → "
            "BA дерево предков (до 5 поколений) → Zoo патч "
            "(registered_name uppercase, zooportal_id всегда из Zoo)."
        ),
        request=ImportHybridDogSerializer,
        responses={202: OpenApiTypes.OBJECT},
        tags=["Import Hybrid"],
    )
    def post(self, request):
        serializer = ImportHybridDogSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        data = serializer.validated_data
        try:
            task = import_hybrid_dog_task.apply_async(kwargs=data, countdown=1)
            return Response({
                'task_id': task.id,
                'status':  'PENDING',
                'message': f"Гибридный импорт собаки {data['zooportal_id']} запущен",
                'check_status_url': f"/api/dogs/import/status/{task.id}/",
            }, status=202)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class ImportHybridPageView(APIView):

    @extend_schema(
        summary="Гибридный импорт страницы Zoo→BA",
        description=(
            "Для каждой собаки на странице Zoo: "
            "Zoo страница → поиск в BA → BA дерево предков (до 5 поколений) → Zoo патч."
        ),
        request=ImportHybridPageSerializer,
        responses={202: OpenApiTypes.OBJECT},
        tags=["Import Hybrid"],
    )
    def post(self, request):
        serializer = ImportHybridPageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        data = serializer.validated_data
        try:
            task = import_hybrid_page_task.apply_async(kwargs=data, countdown=1)
            return Response({
                'task_id': task.id,
                'status':  'PENDING',
                'message': f"Гибридный импорт страницы {data['page_num']} запущен",
                'check_status_url': f"/api/dogs/import/status/{task.id}/",
            }, status=202)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class ImportHybridRangeView(APIView):

    @extend_schema(
        summary="Гибридный импорт диапазона страниц Zoo→BA",
        description="Диспатчит гибридный импорт для каждой страницы из диапазона.",
        request=ImportHybridRangeSerializer,
        responses={202: OpenApiTypes.OBJECT},
        tags=["Import Hybrid"],
    )
    def post(self, request):
        serializer = ImportHybridRangeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        data = serializer.validated_data
        try:
            task = import_hybrid_range_task.apply_async(kwargs=data, countdown=1)
            return Response({
                'task_id': task.id,
                'status':  'PENDING',
                'message': f"Гибридный импорт страниц {data['start_page']}–{data['end_page']} запущен",
                'check_status_url': f"/api/dogs/import/status/{task.id}/",
            }, status=202)
        except Exception as e:
            return Response({'error': str(e)}, status=500)



class RecalculateAllCoiView(APIView):
    """
    Массовый пересчёт COI для всех собак — запускает Celery-задачу.

    POST /api/dogs/coi/recalculate/
    Body:
      {
        "generations": 5,           // 1–10, стандарт = 5
        "only_missing": true,       // true = только Dog.coi IS NULL
        "use_ancestor_coi": false,  // учитывать COI предков (точнее, медленнее)
        "batch_size": 100           // размер батча (10–500)
      }

    Возвращает task_id. Прогресс: GET /api/dogs/import/status/{task_id}/
    """

    def post(self, request):
        from .tasks.tasks_coi import recalculate_all_coi_task

        generations = max(1, min(int(request.data.get('generations', 5)), 10))
        only_missing = bool(request.data.get('only_missing', True))
        use_ancestor_coi = bool(request.data.get('use_ancestor_coi', False))
        batch_size = max(10, min(int(request.data.get('batch_size', 100)), 500))

        task = recalculate_all_coi_task.apply_async(
            args=[generations, batch_size, only_missing, use_ancestor_coi]
        )

        logger.info(
            f"🔄 Запущен массовый пересчёт COI: "
            f"gen={generations}, only_missing={only_missing} | task={task.id}"
        )

        return Response({
            'task_id':          task.id,
            'status':           'PENDING',
            'message':          (
                f'COI recalculation started: '
                f'generations={generations}, only_missing={only_missing}'
            ),
            'check_status_url': f'/api/dogs/import/status/{task.id}/',
        }, status=status.HTTP_202_ACCEPTED)