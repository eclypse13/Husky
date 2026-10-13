from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, OpenApiParameter
from . import models_django as models
from .serializers import *
from .permissions import IsNKPMember, IsOwnerOrReadOnly, IsOwnerOrAdminOrReadOnly


# Контент-справочник

class ContentDictionaryViewSet(viewsets.ReadOnlyModelViewSet):
    """API для контент-справочника"""
    queryset = models.ContentDictionary.objects.all()
    serializer_class = ContentDictionarySerializer
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter('page', str, description='Фильтр по странице'),
            OpenApiParameter('key', str, description='Поиск по ключу'),
        ]
    )
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


@api_view(["GET"])
@permission_classes([AllowAny])
def site_banner(request):
    obj = models.SiteBannerSettings.objects.order_by("-updated_at").first()
    if not obj:
        return Response({"is_enabled": False, "message": "", "updated_at": None})
    return Response(SiteBannerSettingsSerializer(obj).data)


# Публичные API

class NewsViewSet(viewsets.ReadOnlyModelViewSet):
    """API новостей"""
    queryset = models.News.objects.all()
    serializer_class = NewsSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter('featured', bool, description='Только избранные'),
            OpenApiParameter('tag', str, description='Фильтр по тегу'),
        ]
    )
    @method_decorator(cache_page(60 * 5))  # Кеш на 5 минут
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


class PageViewSet(viewsets.ReadOnlyModelViewSet):
    """API CMS страниц"""
    queryset = models.Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    @method_decorator(cache_page(60 * 10))
    def retrieve(self, request, slug=None):
        return super().retrieve(request, slug)


class GalleryViewSet(viewsets.ReadOnlyModelViewSet):
    """API галерей"""
    queryset = models.Gallery.objects.all()
    serializer_class = GallerySerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def highlights(self, request):
        """Избранные галереи для главной"""
        galleries = models.Gallery.objects.filter(is_highlight=True)
        serializer = self.get_serializer(galleries, many=True)
        return Response(serializer.data)


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """API мероприятий"""
    queryset = models.Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter('from_date', str, description='От даты (YYYY-MM-DD)'),
            OpenApiParameter('to_date', str, description='До даты (YYYY-MM-DD)'),
            OpenApiParameter('type', str, description='Тип мероприятия'),
        ]
    )
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


class EventReportViewSet(viewsets.ReadOnlyModelViewSet):
    """API отчетов о мероприятиях"""
    # queryset = models.EventReport.objects.all()
    queryset = models.EventReport.objects.all().prefetch_related("photo_items", "video_items")
    serializer_class = EventReportSerializer
    permission_classes = [AllowAny]


class SeasonViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Season.objects.all().prefetch_related("races").order_by("start_date")
    serializer_class = SportsSeasonSerializer
    permission_classes = [AllowAny]


class RaceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Race.objects.select_related("season").all().order_by("date")
    serializer_class = RaceSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=["get"], url_path="results")
    def results(self, request, pk=None):
        race = self.get_object()

        if not race.results_file:
            return Response({"race": {"rows": []}})

        file_path = Path(race.results_file.path)

        if not file_path.exists():
            return Response(
                {"error": "Results file not found", "race": {"rows": []}},
                status=404,
            )

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return Response(data)
        except Exception as e:
            return Response(
                {"error": f"Invalid JSON: {str(e)}", "race": {"rows": []}},
                status=500,
            )


class JudgeViewSet(viewsets.ReadOnlyModelViewSet):
    """API судей"""
    queryset = models.Judge.objects.all()
    serializer_class = JudgeSerializer
    permission_classes = [AllowAny]


class JudgeDetailsViewSet(viewsets.ReadOnlyModelViewSet):
    """API детальных профилей судей"""
    queryset = models.JudgeDetails.objects.all()
    serializer_class = JudgeDetailsSerializer
    permission_classes = [AllowAny]


class ClubDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """API документов клуба"""
    queryset = models.ClubDocument.objects.all()
    serializer_class = ClubDocumentSerializer
    permission_classes = [AllowAny]


class ClubStatsViewSet(viewsets.ViewSet):
    """API статистики клуба (одна запись)"""
    permission_classes = [AllowAny]

    def list(self, request):
        obj = models.ClubStats.objects.order_by("-updated_at").first()
        if not obj:
            # если запись ещё не создана в админке
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


class BoardMemberViewSet(viewsets.ReadOnlyModelViewSet):
    """API членов Президиума"""
    queryset = models.BoardMember.objects.all()
    serializer_class = BoardMemberSerializer
    permission_classes = [AllowAny]


class WorkingGroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.WorkingGroup.objects.all().prefetch_related("members")
    serializer_class = WorkingGroupSerializer
    permission_classes = [AllowAny]


class BreedStandardViewSet(viewsets.ReadOnlyModelViewSet):
    """API стандартов породы"""
    queryset = models.BreedStandard.objects.all()
    serializer_class = BreedStandardSerializer
    permission_classes = [AllowAny]


class BreedArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """API статей о породе"""
    queryset = models.BreedArticle.objects.all()
    serializer_class = BreedArticleSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter('category', str, description='Категория статьи'),
        ]
    )
    def list(self, request):
        queryset = self.get_queryset()

        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# Личный кабинет

class MyProfileViewSet(viewsets.ViewSet):
    """API профиля пользователя"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Получить информацию о себе"""
        try:
            user = models.User.objects.get(email=request.user.email)
            serializer = UserProfileSerializer(user)
            return Response(serializer.data)
        except models.User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

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


class MyDogViewSet(viewsets.ModelViewSet):
    """API собак пользователя"""
    serializer_class = DogSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = models.User.objects.get(email=self.request.user.email)
        return models.Dog.objects.filter(owner=user)

    @action(detail=False, methods=['get'])
    def champions(self, request):
        """Только чемпионы"""
        queryset = self.get_queryset().filter(is_champion=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class MyKennelViewSet(viewsets.ModelViewSet):
    """API питомника пользователя"""
    serializer_class = KennelSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = models.User.objects.get(email=self.request.user.email)
        return models.Kennel.objects.filter(owner=user)


class MyLitterViewSet(viewsets.ModelViewSet):
    """API пометов пользователя"""
    serializer_class = LitterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = models.User.objects.get(email=self.request.user.email)
        kennels = models.Kennel.objects.filter(owner=user)
        return models.Litter.objects.filter(kennel__in=kennels)


class MyApplicationViewSet(viewsets.ModelViewSet):
    """API заявлений пользователя"""
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = models.User.objects.get(email=self.request.user.email)
        return models.Application.objects.filter(user=user)


class MyAchievementViewSet(viewsets.ReadOnlyModelViewSet):
    """API достижений пользователя"""
    serializer_class = AchievementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = models.User.objects.get(email=self.request.user.email)
        return models.Achievement.objects.filter(user=user)


# Аутентификация

@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'email': {'type': 'string'},
                'password': {'type': 'string'}
            }
        }
    },
    responses={200: {'description': 'Login successful'}}
)
def _build_auth_response(auth_user, email):
    """Формирует единый ответ авторизации: токен + профиль."""
    from rest_framework.authtoken.models import Token
    token, _ = Token.objects.get_or_create(user=auth_user)

    payload = {
        'success': True,
        'token': token.key,
        'user': {
            'email': email,
            'name': '',
            'first_name': '',
            'last_name': '',
            'is_nkp_member': False,
            'is_staff': bool(auth_user.is_staff or auth_user.is_superuser),
        },
    }
    try:
        profile = models.User.objects.get(email=email)
        payload['user'].update({
            'name': f'{profile.first_name} {profile.last_name}'.strip(),
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'is_nkp_member': profile.is_nkp_member,
        })
    except models.User.DoesNotExist:
        pass
    return payload


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Вход в систему. Возвращает токен для дальнейших запросов."""
    email = (request.data.get('email') or '').strip().lower()
    password = request.data.get('password')

    user = authenticate(request, username=email, password=password)
    if user:
        login(request, user)
        return Response(_build_auth_response(user, email))

    return Response({'error': 'Неверный email или пароль'}, status=401)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    Регистрация нового пользователя.

    Создаёт запись в django.contrib.auth (для входа) и профиль core.User,
    связанные по email. Возвращает токен и профиль.
    """
    from django.contrib.auth.models import User as AuthUser
    from django.contrib.auth.hashers import make_password

    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    email = data['email']

    if AuthUser.objects.filter(username=email).exists() or models.User.objects.filter(email=email).exists():
        return Response({'error': 'Пользователь с таким email уже существует'}, status=400)

    auth_user = AuthUser.objects.create_user(
        username=email,
        email=email,
        password=data['password'],
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
    )

    models.User.objects.create(
        email=email,
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
        phone=data.get('phone', ''),
        city=data.get('city', ''),
        password_hash=make_password(data['password']),
    )

    login(request, auth_user)
    return Response(_build_auth_response(auth_user, email), status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Выход из системы"""
    logout(request)
    return Response({'success': True})


# Главная страница

@extend_schema(
    responses={200: {
        'description': 'Home page data',
        'content': {
            'application/json': {
                'example': {
                    'featured_news': [],
                    'upcoming_events': [],
                    'highlight_galleries': []
                }
            }
        }
    }}
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


# ============================================
# ЩЕНКИ НА ПРОДАЖУ
# ============================================

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .images import normalize_image


class PuppyListingViewSet(viewsets.ModelViewSet):
    """
    Объявления о щенках.

    - list / retrieve — публично (только опубликованные; автор и админ видят свои черновики).
    - create / update / delete — автор объявления либо администратор.

    Фото загружаются через multipart полем `photos` (можно несколько за раз)
    и приводятся к единому размеру. Удаление фото — поле `remove_photo_ids`
    (id через запятую) при обновлении.
    """
    serializer_class = PuppyListingSerializer
    permission_classes = [IsOwnerOrAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _current_profile(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return None
        return models.User.objects.filter(email=user.email).first()

    @staticmethod
    def _parse_bool(value, default=False):
        """Разбор булева флага из multipart/JSON (строки '1'/'true'/'on')."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ('1', 'true', 'on', 'yes')

    def get_queryset(self):
        qs = models.PuppyListing.objects.all().prefetch_related('photos').select_related('owner')
        user = self.request.user

        # Полный доступ администратору
        if user and user.is_authenticated and (user.is_staff or user.is_superuser):
            base = qs
        elif user and user.is_authenticated:
            # Автор видит свои непубличные + все публичные
            from django.db.models import Q
            profile = self._current_profile()
            if profile:
                base = qs.filter(Q(is_published=True) | Q(owner=profile))
            else:
                base = qs.filter(is_published=True)
        else:
            base = qs.filter(is_published=True)

        # Фильтры
        params = self.request.query_params
        search = params.get('q')
        if search:
            from django.db.models import Q
            base = base.filter(
                Q(name__icontains=search) |
                Q(kennel_name__icontains=search) |
                Q(city__icontains=search)
            )
        sex = params.get('sex')
        if sex:
            base = base.filter(sex=sex)
        status_f = params.get('status')
        if status_f:
            base = base.filter(status=status_f)
        if params.get('nkp') in ('1', 'true', 'True'):
            base = base.filter(is_nkp_member=True)

        return base

    def _save_photos(self, listing, files):
        start = listing.photos.count()
        for i, f in enumerate(files):
            models.PuppyPhoto.objects.create(
                listing=listing,
                image=normalize_image(f),
                order=start + i,
            )

    def _remove_photos(self, listing, raw_ids):
        try:
            ids = [int(x) for x in str(raw_ids).split(',') if str(x).strip()]
        except ValueError:
            ids = []
        if ids:
            listing.photos.filter(id__in=ids).delete()

    def perform_create(self, serializer):
        profile = self._current_profile()
        if profile is None:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Профиль пользователя не найден')

        listing = serializer.save(
            owner=profile,
            is_nkp_member=profile.is_nkp_member,
            # Новое объявление по умолчанию публикуется; владелец может сразу
            # создать его скрытым, прислав is_published=false.
            is_published=self._parse_bool(self.request.data.get('is_published'), default=True),
        )
        self._save_photos(listing, self.request.FILES.getlist('photos'))

    def perform_update(self, serializer):
        listing = serializer.save()

        user = self.request.user
        is_admin = bool(user and (user.is_staff or user.is_superuser))

        update_fields = []
        # НКП-метку меняет только администратор
        if is_admin and 'is_nkp_member' in self.request.data:
            listing.is_nkp_member = self._parse_bool(
                self.request.data.get('is_nkp_member'), default=listing.is_nkp_member
            )
            update_fields.append('is_nkp_member')
        # Публикацию (скрыть / вернуть) может менять владелец объявления или админ —
        # доступ к update уже ограничен IsOwnerOrAdminOrReadOnly.
        if 'is_published' in self.request.data:
            listing.is_published = self._parse_bool(
                self.request.data.get('is_published'), default=listing.is_published
            )
            update_fields.append('is_published')
        if update_fields:
            listing.save(update_fields=update_fields)

        remove_ids = self.request.data.get('remove_photo_ids')
        if remove_ids:
            self._remove_photos(listing, remove_ids)
        self._save_photos(listing, self.request.FILES.getlist('photos'))

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def mine(self, request):
        """Мои объявления."""
        profile = self._current_profile()
        if profile is None:
            return Response([], status=200)
        qs = models.PuppyListing.objects.filter(owner=profile).prefetch_related('photos')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


@api_view(["GET"])
def active_president(request):
    president = (
        models.President.objects
        .filter(is_active=True)
        .prefetch_related("badges", "achievements")
        .first()
    )

    if not president:
        return Response(
            {"detail": "Активный президент не найден"},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = PresidentSerializer(president)
    return Response(serializer.data)