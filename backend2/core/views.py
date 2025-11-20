from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import *
from .serializers import *
from .permissions import IsNKPMember, IsOwnerOrReadOnly


# ============================================
# КОНТЕНТ-СПРАВОЧНИК API
# ============================================

class ContentDictionaryViewSet(viewsets.ReadOnlyModelViewSet):
    """API для контент-справочника"""
    queryset = ContentDictionary.objects.all()
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
            content = ContentDictionary.objects.get(key=key)
            return Response({'key': content.key, 'value': content.value})
        except ContentDictionary.DoesNotExist:
            return Response({'error': 'Key not found'}, status=404)


# ============================================
# ПУБЛИЧНЫЕ API
# ============================================

class NewsViewSet(viewsets.ReadOnlyModelViewSet):
    """API новостей"""
    queryset = News.objects.all()
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
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    
    @method_decorator(cache_page(60 * 10))
    def retrieve(self, request, slug=None):
        return super().retrieve(request, slug)


class GalleryViewSet(viewsets.ReadOnlyModelViewSet):
    """API галерей"""
    queryset = Gallery.objects.all()
    serializer_class = GallerySerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'])
    def highlights(self, request):
        """Избранные галереи для главной"""
        galleries = Gallery.objects.filter(is_highlight=True)
        serializer = self.get_serializer(galleries, many=True)
        return Response(serializer.data)


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """API мероприятий"""
    queryset = Event.objects.all()
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
    queryset = EventReport.objects.all()
    serializer_class = EventReportSerializer
    permission_classes = [AllowAny]


class JudgeViewSet(viewsets.ReadOnlyModelViewSet):
    """API судей"""
    queryset = Judge.objects.all()
    serializer_class = JudgeSerializer
    permission_classes = [AllowAny]


class ClubDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """API документов клуба"""
    queryset = ClubDocument.objects.all()
    serializer_class = ClubDocumentSerializer
    permission_classes = [AllowAny]


class BoardMemberViewSet(viewsets.ReadOnlyModelViewSet):
    """API членов Президиума"""
    queryset = BoardMember.objects.all()
    serializer_class = BoardMemberSerializer
    permission_classes = [AllowAny]


class BreedStandardViewSet(viewsets.ReadOnlyModelViewSet):
    """API стандартов породы"""
    queryset = BreedStandard.objects.all()
    serializer_class = BreedStandardSerializer
    permission_classes = [AllowAny]


class BreedArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """API статей о породе"""
    queryset = BreedArticle.objects.all()
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


# ============================================
# ЛИЧНЫЙ КАБИНЕТ API
# ============================================

class MyProfileViewSet(viewsets.ViewSet):
    """API профиля пользователя"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Получить информацию о себе"""
        try:
            user = User.objects.get(email=request.user.email)
            serializer = UserProfileSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
    
    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        """Обновить профиль"""
        try:
            user = User.objects.get(email=request.user.email)
            serializer = UserProfileSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)


class MyDogViewSet(viewsets.ModelViewSet):
    """API собак пользователя"""
    serializer_class = DogSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        user = User.objects.get(email=self.request.user.email)
        return Dog.objects.filter(owner=user)
    
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
        user = User.objects.get(email=self.request.user.email)
        return Kennel.objects.filter(owner=user)


class MyLitterViewSet(viewsets.ModelViewSet):
    """API пометов пользователя"""
    serializer_class = LitterSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = User.objects.get(email=self.request.user.email)
        kennels = Kennel.objects.filter(owner=user)
        return Litter.objects.filter(kennel__in=kennels)


class MyApplicationViewSet(viewsets.ModelViewSet):
    """API заявлений пользователя"""
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = User.objects.get(email=self.request.user.email)
        return Application.objects.filter(user=user)


class MyAchievementViewSet(viewsets.ReadOnlyModelViewSet):
    """API достижений пользователя"""
    serializer_class = AchievementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = User.objects.get(email=self.request.user.email)
        return Achievement.objects.filter(user=user)


# ============================================
# АУТЕНТИФИКАЦИЯ API
# ============================================

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
            mongo_user = User.objects.get(email=email)
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Выход из системы"""
    logout(request)
    return Response({'success': True})


# ============================================
# ГЛАВНАЯ СТРАНИЦА API
# ============================================

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
    featured_news = News.objects.filter(is_featured=True)[:3]
    upcoming_events = Event.objects.filter(starts_at__gte=datetime.utcnow())[:5]
    highlight_galleries = Gallery.objects.filter(is_highlight=True)[:2]
    
    return Response({
        'featured_news': NewsSerializer(featured_news, many=True).data,
        'upcoming_events': EventSerializer(upcoming_events, many=True).data,
        'highlight_galleries': GallerySerializer(highlight_galleries, many=True).data,
    })
