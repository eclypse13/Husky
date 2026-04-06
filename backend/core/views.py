from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
    inline_serializer,
)
from drf_spectacular.openapi import OpenApiTypes
from rest_framework import serializers as drf_serializers
from . import models_django as models
from .serializers import *
from .permissions import IsNKPMember, IsOwnerOrReadOnly


# ============================================
# КОНТЕНТ-СПРАВОЧНИК API
# ============================================

@extend_schema_view(
    list=extend_schema(
        summary="Список контент-записей",
        description="Возвращает все записи контент-справочника. Поддерживает фильтрацию по странице и ключу.",
        parameters=[
            OpenApiParameter('page', str, description='Фильтр по странице'),
            OpenApiParameter('key', str, description='Поиск по ключу (частичное совпадение)'),
        ],
        responses={200: ContentDictionarySerializer(many=True)},
        tags=["Content Dictionary"],
    ),
    retrieve=extend_schema(
        summary="Получить запись по ID",
        responses={
            200: ContentDictionarySerializer,
            404: OpenApiResponse(description="Запись не найдена"),
        },
        tags=["Content Dictionary"],
    ),
)
class ContentDictionaryViewSet(viewsets.ReadOnlyModelViewSet):
    """API для контент-справочника"""
    queryset = models.ContentDictionary.objects.all()
    serializer_class = ContentDictionarySerializer
    permission_classes = [AllowAny]

    def list(self, request):
        queryset = self.get_queryset()

        page_filter = request.query_params.get('page')
        if page_filter:
            queryset = queryset.filter(page=page_filter)

        key_filter = request.query_params.get('key')
        if key_filter:
            queryset = queryset.filter(key__icontains=key_filter)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Получить значение по ключу",
        description="Возвращает одну запись контент-справочника по точному совпадению ключа.",
        parameters=[
            OpenApiParameter('key', str, required=True, description='Точный ключ записи'),
        ],
        responses={
            200: OpenApiResponse(
                description="Запись найдена",
                response=inline_serializer(
                    name="ContentByKeyResponse",
                    fields={
                        "key": drf_serializers.CharField(),
                        "value": drf_serializers.JSONField(),
                    },
                ),
            ),
            400: OpenApiResponse(description="Параметр key не передан"),
            404: OpenApiResponse(description="Запись с указанным ключом не найдена"),
        },
        tags=["Content Dictionary"],
    )
    @action(detail=False, methods=['get'])
    def by_key(self, request):
        """Получить значение по ключу"""
        key = request.query_params.get('key')
        if not key:
            return Response({'error': 'Key parameter required'}, status=400)

        try:
            content = models.ContentDictionary.objects.get(key=key)
            return Response({'key': content.key, 'value': content.value})
        except models.ContentDictionary.DoesNotExist:
            return Response({'error': 'Key not found'}, status=404)


# ============================================
# ПУБЛИЧНЫЕ API
# ============================================

@extend_schema_view(
    list=extend_schema(
        summary="Список новостей",
        description="Возвращает пагинированный список новостей. Поддерживает фильтрацию по избранному и тегам.",
        parameters=[
            OpenApiParameter('featured', bool, description='Только избранные новости'),
            OpenApiParameter('tag', str, description='Фильтр по тегу'),
        ],
        responses={200: NewsSerializer(many=True)},
        tags=["News"],
    ),
    retrieve=extend_schema(
        summary="Получить новость по ID",
        responses={
            200: NewsSerializer,
            404: OpenApiResponse(description="Новость не найдена"),
        },
        tags=["News"],
    ),
)
class NewsViewSet(viewsets.ReadOnlyModelViewSet):
    """API новостей"""
    queryset = models.News.objects.all()
    serializer_class = NewsSerializer
    permission_classes = [AllowAny]

    @method_decorator(cache_page(60 * 5))
    def list(self, request):
        queryset = self.get_queryset()

        if request.query_params.get('featured'):
            queryset = queryset.filter(is_featured=True)

        tag = request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(tags__contains=tag)

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="Список CMS-страниц",
        responses={200: PageSerializer(many=True)},
        tags=["Pages"],
    ),
    retrieve=extend_schema(
        summary="Получить CMS-страницу по slug",
        responses={
            200: PageSerializer,
            404: OpenApiResponse(description="Страница не найдена"),
        },
        tags=["Pages"],
    ),
)
class PageViewSet(viewsets.ReadOnlyModelViewSet):
    """API CMS страниц"""
    queryset = models.Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    @method_decorator(cache_page(60 * 10))
    def retrieve(self, request, slug=None):
        return super().retrieve(request, slug)


@extend_schema_view(
    list=extend_schema(
        summary="Список галерей",
        responses={200: GallerySerializer(many=True)},
        tags=["Galleries"],
    ),
    retrieve=extend_schema(
        summary="Получить галерею по ID",
        responses={
            200: GallerySerializer,
            404: OpenApiResponse(description="Галерея не найдена"),
        },
        tags=["Galleries"],
    ),
)
class GalleryViewSet(viewsets.ReadOnlyModelViewSet):
    """API галерей"""
    queryset = models.Gallery.objects.all()
    serializer_class = GallerySerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Избранные галереи",
        description="Возвращает галереи, отмеченные как избранные (для главной страницы).",
        responses={200: GallerySerializer(many=True)},
        tags=["Galleries"],
    )
    @action(detail=False, methods=['get'])
    def highlights(self, request):
        """Избранные галереи для главной"""
        galleries = models.Gallery.objects.filter(is_highlight=True)
        serializer = self.get_serializer(galleries, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="Список мероприятий",
        description="Возвращает список мероприятий. Поддерживает фильтрацию по датам и типу.",
        parameters=[
            OpenApiParameter('from_date', str, description='От даты (YYYY-MM-DD)'),
            OpenApiParameter('to_date', str, description='До даты (YYYY-MM-DD)'),
            OpenApiParameter('type', str, description='Тип мероприятия'),
        ],
        responses={200: EventSerializer(many=True)},
        tags=["Events"],
    ),
    retrieve=extend_schema(
        summary="Получить мероприятие по ID",
        responses={
            200: EventSerializer,
            404: OpenApiResponse(description="Мероприятие не найдено"),
        },
        tags=["Events"],
    ),
)
class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """API мероприятий"""
    queryset = models.Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [AllowAny]

    def list(self, request):
        queryset = self.get_queryset()

        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        event_type = request.query_params.get('type')

        if from_date:
            queryset = queryset.filter(starts_at__gte=from_date)
        if to_date:
            queryset = queryset.filter(starts_at__lte=to_date)
        if event_type:
            queryset = queryset.filter(event_type=event_type)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="Список отчётов о мероприятиях",
        responses={200: EventReportSerializer(many=True)},
        tags=["Event Reports"],
    ),
    retrieve=extend_schema(
        summary="Получить отчёт о мероприятии по ID",
        responses={
            200: EventReportSerializer,
            404: OpenApiResponse(description="Отчёт не найден"),
        },
        tags=["Event Reports"],
    ),
)
class EventReportViewSet(viewsets.ReadOnlyModelViewSet):
    """API отчетов о мероприятиях"""
    queryset = models.EventReport.objects.all().prefetch_related("photo_items", "video_items")
    serializer_class = EventReportSerializer
    permission_classes = [AllowAny]


@extend_schema_view(
    list=extend_schema(
        summary="Список судей",
        responses={200: JudgeSerializer(many=True)},
        tags=["Judges"],
    ),
    retrieve=extend_schema(
        summary="Получить судью по ID",
        responses={
            200: JudgeSerializer,
            404: OpenApiResponse(description="Судья не найден"),
        },
        tags=["Judges"],
    ),
)
class JudgeViewSet(viewsets.ReadOnlyModelViewSet):
    """API судей"""
    queryset = models.Judge.objects.all()
    serializer_class = JudgeSerializer
    permission_classes = [AllowAny]


@extend_schema_view(
    list=extend_schema(
        summary="Список детальных профилей судей",
        responses={200: JudgeDetailsSerializer(many=True)},
        tags=["Judges"],
    ),
    retrieve=extend_schema(
        summary="Получить детальный профиль судьи",
        responses={
            200: JudgeDetailsSerializer,
            404: OpenApiResponse(description="Профиль судьи не найден"),
        },
        tags=["Judges"],
    ),
)
class JudgeDetailsViewSet(viewsets.ReadOnlyModelViewSet):
    """API детальных профилей судей"""
    queryset = models.JudgeDetails.objects.all()
    serializer_class = JudgeDetailsSerializer
    permission_classes = [AllowAny]


@extend_schema_view(
    list=extend_schema(
        summary="Список документов клуба",
        responses={200: ClubDocumentSerializer(many=True)},
        tags=["Club Documents"],
    ),
    retrieve=extend_schema(
        summary="Получить документ клуба по ID",
        responses={
            200: ClubDocumentSerializer,
            404: OpenApiResponse(description="Документ не найден"),
        },
        tags=["Club Documents"],
    ),
)
class ClubDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """API документов клуба"""
    queryset = models.ClubDocument.objects.all()
    serializer_class = ClubDocumentSerializer
    permission_classes = [AllowAny]


class ClubStatsViewSet(viewsets.ViewSet):
    """API статистики клуба (одна запись)"""
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Статистика клуба",
        description="Возвращает последнюю запись статистики клуба. Если данных ещё нет — возвращает нулевые значения.",
        responses={
            200: ClubStatsSerializer,
        },
        tags=["Club Stats"],
    )
    def list(self, request):
        obj = models.ClubStats.objects.order_by("-updated_at").first()
        if not obj:
            return Response(
                {
                    "members_count": 0,
                    "kennels_count": 0,
                    "dogs_in_archive_count": 0,
                    "regions_count": 0,
                    "updated_at": None,
                },
                status=status.HTTP_200_OK,
            )

        return Response(ClubStatsSerializer(obj).data)


@extend_schema_view(
    list=extend_schema(
        summary="Список членов Президиума",
        responses={200: BoardMemberSerializer(many=True)},
        tags=["Leadership"],
    ),
    retrieve=extend_schema(
        summary="Получить члена Президиума по ID",
        responses={
            200: BoardMemberSerializer,
            404: OpenApiResponse(description="Член Президиума не найден"),
        },
        tags=["Leadership"],
    ),
)
class BoardMemberViewSet(viewsets.ReadOnlyModelViewSet):
    """API членов Президиума"""
    queryset = models.BoardMember.objects.all()
    serializer_class = BoardMemberSerializer
    permission_classes = [AllowAny]


@extend_schema_view(
    list=extend_schema(
        summary="Список рабочих групп",
        description="Возвращает рабочие группы вместе с вложенными участниками.",
        responses={200: WorkingGroupSerializer(many=True)},
        tags=["Leadership"],
    ),
    retrieve=extend_schema(
        summary="Получить рабочую группу по ID",
        responses={
            200: WorkingGroupSerializer,
            404: OpenApiResponse(description="Рабочая группа не найдена"),
        },
        tags=["Leadership"],
    ),
)
class WorkingGroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.WorkingGroup.objects.all().prefetch_related("members")
    serializer_class = WorkingGroupSerializer
    permission_classes = [AllowAny]


@extend_schema_view(
    list=extend_schema(
        summary="Список стандартов породы",
        responses={200: BreedStandardSerializer(many=True)},
        tags=["Breed"],
    ),
    retrieve=extend_schema(
        summary="Получить стандарт породы по ID",
        responses={
            200: BreedStandardSerializer,
            404: OpenApiResponse(description="Стандарт не найден"),
        },
        tags=["Breed"],
    ),
)
class BreedStandardViewSet(viewsets.ReadOnlyModelViewSet):
    """API стандартов породы"""
    queryset = models.BreedStandard.objects.all()
    serializer_class = BreedStandardSerializer
    permission_classes = [AllowAny]


@extend_schema_view(
    list=extend_schema(
        summary="Список статей о породе",
        description="Возвращает список статей. Поддерживает фильтрацию по категории.",
        parameters=[
            OpenApiParameter('category', str, description='Категория статьи'),
        ],
        responses={200: BreedArticleSerializer(many=True)},
        tags=["Breed"],
    ),
    retrieve=extend_schema(
        summary="Получить статью о породе по ID",
        responses={
            200: BreedArticleSerializer,
            404: OpenApiResponse(description="Статья не найдена"),
        },
        tags=["Breed"],
    ),
)
class BreedArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """API статей о породе"""
    queryset = models.BreedArticle.objects.all()
    serializer_class = BreedArticleSerializer
    permission_classes = [AllowAny]

    def list(self, request):
        queryset = self.get_queryset()

        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# ============================================
# ЛИЧНЫЙ КАБИНЕТ API
# ============================================

class MyProfileViewSet(viewsets.ViewSet):
    """API профиля пользователя"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Получить свой профиль",
        description="Возвращает профиль текущего авторизованного пользователя.",
        responses={
            200: UserProfileSerializer,
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
            404: OpenApiResponse(description="Профиль пользователя не найден"),
        },
        tags=["Profile"],
    )
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Получить информацию о себе"""
        try:
            user = models.User.objects.get(email=request.user.email)
            serializer = UserProfileSerializer(user)
            return Response(serializer.data)
        except models.User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

    @extend_schema(
        summary="Обновить свой профиль",
        description="Частичное обновление профиля текущего пользователя.",
        request=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
            404: OpenApiResponse(description="Профиль пользователя не найден"),
        },
        tags=["Profile"],
    )
    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        """Обновить профиль"""
        try:
            user = models.User.objects.get(email=request.user.email)
            serializer = UserProfileSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except models.User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)


@extend_schema_view(
    list=extend_schema(
        summary="Список моих собак",
        responses={
            200: DogSerializer(many=True),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
        },
        tags=["My Dogs"],
    ),
    retrieve=extend_schema(
        summary="Получить мою собаку по ID",
        responses={
            200: DogSerializer,
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
            404: OpenApiResponse(description="Собака не найдена"),
        },
        tags=["My Dogs"],
    ),
    create=extend_schema(
        summary="Добавить собаку",
        responses={
            201: DogSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
        },
        tags=["My Dogs"],
    ),
    update=extend_schema(
        summary="Обновить данные собаки",
        responses={
            200: DogSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
            403: OpenApiResponse(description="Нет доступа (не аутентифицирован или не владелец)"),
            404: OpenApiResponse(description="Собака не найдена"),
        },
        tags=["My Dogs"],
    ),
    partial_update=extend_schema(
        summary="Частично обновить данные собаки",
        responses={
            200: DogSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
            403: OpenApiResponse(description="Нет доступа (не аутентифицирован или не владелец)"),
            404: OpenApiResponse(description="Собака не найдена"),
        },
        tags=["My Dogs"],
    ),
    destroy=extend_schema(
        summary="Удалить собаку",
        responses={
            204: OpenApiResponse(description="Собака удалена"),
            403: OpenApiResponse(description="Нет доступа (не аутентифицирован или не владелец)"),
            404: OpenApiResponse(description="Собака не найдена"),
        },
        tags=["My Dogs"],
    ),
)
class MyDogViewSet(viewsets.ModelViewSet):
    """API собак пользователя"""
    serializer_class = DogSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = models.User.objects.get(email=self.request.user.email)
        return models.Dog.objects.filter(owner=user)

    @extend_schema(
        summary="Список моих чемпионов",
        description="Возвращает только собак с титулом чемпиона.",
        responses={
            200: DogSerializer(many=True),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
        },
        tags=["My Dogs"],
    )
    @action(detail=False, methods=['get'])
    def champions(self, request):
        """Только чемпионы"""
        queryset = self.get_queryset().filter(is_champion=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="Список моих питомников",
        responses={
            200: KennelSerializer(many=True),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
        },
        tags=["My Kennels"],
    ),
    retrieve=extend_schema(
        summary="Получить мой питомник по ID",
        responses={
            200: KennelSerializer,
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
            404: OpenApiResponse(description="Питомник не найден"),
        },
        tags=["My Kennels"],
    ),
    create=extend_schema(
        summary="Создать питомник",
        responses={
            201: KennelSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
        },
        tags=["My Kennels"],
    ),
    update=extend_schema(
        summary="Обновить питомник",
        responses={
            200: KennelSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
            403: OpenApiResponse(description="Нет доступа (не аутентифицирован или не владелец)"),
            404: OpenApiResponse(description="Питомник не найден"),
        },
        tags=["My Kennels"],
    ),
    partial_update=extend_schema(
        summary="Частично обновить питомник",
        responses={
            200: KennelSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
            403: OpenApiResponse(description="Нет доступа (не аутентифицирован или не владелец)"),
            404: OpenApiResponse(description="Питомник не найден"),
        },
        tags=["My Kennels"],
    ),
    destroy=extend_schema(
        summary="Удалить питомник",
        responses={
            204: OpenApiResponse(description="Питомник удалён"),
            403: OpenApiResponse(description="Нет доступа (не аутентифицирован или не владелец)"),
            404: OpenApiResponse(description="Питомник не найден"),
        },
        tags=["My Kennels"],
    ),
)
class MyKennelViewSet(viewsets.ModelViewSet):
    """API питомника пользователя"""
    serializer_class = KennelSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = models.User.objects.get(email=self.request.user.email)
        return models.Kennel.objects.filter(owner=user)


@extend_schema_view(
    list=extend_schema(
        summary="Список моих помётов",
        responses={
            200: LitterSerializer(many=True),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
        },
        tags=["My Litters"],
    ),
    retrieve=extend_schema(
        summary="Получить мой помёт по ID",
        responses={
            200: LitterSerializer,
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
            404: OpenApiResponse(description="Помёт не найден"),
        },
        tags=["My Litters"],
    ),
    create=extend_schema(
        summary="Создать помёт",
        responses={
            201: LitterSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
        },
        tags=["My Litters"],
    ),
    update=extend_schema(
        summary="Обновить помёт",
        responses={
            200: LitterSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
            404: OpenApiResponse(description="Помёт не найден"),
        },
        tags=["My Litters"],
    ),
    partial_update=extend_schema(
        summary="Частично обновить помёт",
        responses={
            200: LitterSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
            404: OpenApiResponse(description="Помёт не найден"),
        },
        tags=["My Litters"],
    ),
    destroy=extend_schema(
        summary="Удалить помёт",
        responses={
            204: OpenApiResponse(description="Помёт удалён"),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
            404: OpenApiResponse(description="Помёт не найден"),
        },
        tags=["My Litters"],
    ),
)
class MyLitterViewSet(viewsets.ModelViewSet):
    """API пометов пользователя"""
    serializer_class = LitterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = models.User.objects.get(email=self.request.user.email)
        kennels = models.Kennel.objects.filter(owner=user)
        return models.Litter.objects.filter(kennel__in=kennels)


@extend_schema_view(
    list=extend_schema(
        summary="Список моих заявлений",
        responses={
            200: ApplicationSerializer(many=True),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
        },
        tags=["My Applications"],
    ),
    retrieve=extend_schema(
        summary="Получить моё заявление по ID",
        responses={
            200: ApplicationSerializer,
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
            404: OpenApiResponse(description="Заявление не найдено"),
        },
        tags=["My Applications"],
    ),
    create=extend_schema(
        summary="Создать заявление",
        responses={
            201: ApplicationSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
        },
        tags=["My Applications"],
    ),
    update=extend_schema(
        summary="Обновить заявление",
        responses={
            200: ApplicationSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
            404: OpenApiResponse(description="Заявление не найдено"),
        },
        tags=["My Applications"],
    ),
    partial_update=extend_schema(
        summary="Частично обновить заявление",
        responses={
            200: ApplicationSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
            404: OpenApiResponse(description="Заявление не найдено"),
        },
        tags=["My Applications"],
    ),
    destroy=extend_schema(
        summary="Удалить заявление",
        responses={
            204: OpenApiResponse(description="Заявление удалено"),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
            404: OpenApiResponse(description="Заявление не найдено"),
        },
        tags=["My Applications"],
    ),
)
class MyApplicationViewSet(viewsets.ModelViewSet):
    """API заявлений пользователя"""
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = models.User.objects.get(email=self.request.user.email)
        return models.Application.objects.filter(user=user)


@extend_schema_view(
    list=extend_schema(
        summary="Список моих достижений",
        responses={
            200: AchievementSerializer(many=True),
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
        },
        tags=["My Achievements"],
    ),
    retrieve=extend_schema(
        summary="Получить моё достижение по ID",
        responses={
            200: AchievementSerializer,
            403: OpenApiResponse(description="Учётные данные не были предоставлены"),
            404: OpenApiResponse(description="Достижение не найдено"),
        },
        tags=["My Achievements"],
    ),
)
class MyAchievementViewSet(viewsets.ReadOnlyModelViewSet):
    """API достижений пользователя"""
    serializer_class = AchievementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = models.User.objects.get(email=self.request.user.email)
        return models.Achievement.objects.filter(user=user)


# ============================================
# АУТЕНТИФИКАЦИЯ API
# ============================================

_LoginRequestSerializer = inline_serializer(
    name="LoginRequest",
    fields={
        "email": drf_serializers.EmailField(help_text="Email пользователя"),
        "password": drf_serializers.CharField(help_text="Пароль"),
    },
)

_LoginSuccessSerializer = inline_serializer(
    name="LoginSuccess",
    fields={
        "success": drf_serializers.BooleanField(),
        "user": inline_serializer(
            name="LoginUser",
            fields={
                "email": drf_serializers.EmailField(),
                "name": drf_serializers.CharField(),
                "is_nkp_member": drf_serializers.BooleanField(),
            },
        ),
    },
)


@extend_schema(
    summary="Вход в систему",
    description="Аутентификация пользователя по email и паролю. Устанавливает сессионный cookie.",
    request=_LoginRequestSerializer,
    responses={
        200: OpenApiResponse(response=_LoginSuccessSerializer, description="Успешная аутентификация"),
        401: OpenApiResponse(description="Неверный email или пароль"),
    },
    tags=["Auth"],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Вход в систему"""
    email = request.data.get('email')
    password = request.data.get('password')

    # Django auth
    user = authenticate(request, username=email, password=password)
    if user:
        login(request, user)

        # Получаем MongoDB пользователя
        try:
            mongo_user = models.User.objects.get(email=email)
            return Response({
                'success': True,
                'user': {
                    'email': mongo_user.email,
                    'name': f"{mongo_user.first_name} {mongo_user.last_name}",
                    'is_nkp_member': mongo_user.is_nkp_member
                }
            })
        except:
            return Response({'success': True, 'user': {'email': email}})

    return Response({'error': 'Invalid credentials'}, status=401)


@extend_schema(
    summary="Выход из системы",
    description="Завершает текущую сессию пользователя.",
    request=None,
    responses={
        200: OpenApiResponse(description="Сессия завершена"),
        403: OpenApiResponse(description="Учётные данные не были предоставлены"),
    },
    tags=["Auth"],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Выход из системы"""
    logout(request)
    return Response({'success': True})


# ============================================
# ГЛАВНАЯ СТРАНИЦА API
# ============================================

_HomeResponseSerializer = inline_serializer(
    name="HomeResponse",
    fields={
        "featured_news": NewsSerializer(many=True),
        "upcoming_events": EventSerializer(many=True),
        "highlight_galleries": GallerySerializer(many=True),
    },
)


@extend_schema(
    summary="Данные для главной страницы",
    description="Возвращает избранные новости (до 3), ближайшие мероприятия (до 5) и избранные галереи (до 2).",
    responses={200: _HomeResponseSerializer},
    tags=["Home"],
)
@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(60 * 5)
def home_api(request):
    """API главной страницы"""
    featured_news = models.News.objects.filter(is_featured=True)[:3]
    upcoming_events = models.Event.objects.filter(starts_at__gte=datetime.utcnow())[:5]
    highlight_galleries = models.Gallery.objects.filter(is_highlight=True)[:2]

    return Response({
        'featured_news': NewsSerializer(featured_news, many=True).data,
        'upcoming_events': EventSerializer(upcoming_events, many=True).data,
        'highlight_galleries': GallerySerializer(highlight_galleries, many=True).data,
    })


import json
from pathlib import Path

_ActivityFeedSerializer = inline_serializer(
    name="ActivityFeedResponse",
    fields={
        "results": drf_serializers.ListField(
            child=drf_serializers.JSONField(),
            help_text="Список последних сообщений из Telegram-канала",
        ),
    },
)


@extend_schema(
    summary="Лента активности",
    description="Возвращает последние сообщения из Telegram-канала клуба (кешируется на 1 минуту).",
    responses={200: _ActivityFeedSerializer},
    tags=["Home"],
)
@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(60 * 1)
def activity_feed(request):
    path = Path("/shared/latest_messages.json")

    if not path.exists():
        return Response({"results": []})

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return Response({"results": []})

    return Response({"results": data})
