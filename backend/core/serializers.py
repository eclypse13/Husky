from rest_framework import serializers
from .models import *


class ContentDictionarySerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    key = serializers.CharField()
    value = serializers.CharField()
    page = serializers.CharField()
    locale = serializers.CharField()
    updated_by = serializers.CharField(required=False)
    updated_at = serializers.DateTimeField(read_only=True)


class NewsSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title_key = serializers.CharField()
    lead_key = serializers.CharField(required=False)
    body_key = serializers.CharField(required=False)
    slug = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    is_featured = serializers.BooleanField(default=False)
    published_at = serializers.DateTimeField(read_only=True)


class PageSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    slug = serializers.CharField()
    title_key = serializers.CharField()
    sections = serializers.ListField(required=False)
    is_published = serializers.BooleanField(default=True)


class GallerySerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title_key = serializers.CharField()
    description_key = serializers.CharField(required=False)
    images = serializers.ListField(required=False)
    is_highlight = serializers.BooleanField(default=False)


class EventSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title_key = serializers.CharField()
    description_key = serializers.CharField(required=False)
    event_type = serializers.CharField()
    location = serializers.CharField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField(required=False)
    registration_link = serializers.URLField(required=False)


class EventReportSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    event = serializers.CharField()
    results = serializers.ListField(required=False)
    created_at = serializers.DateTimeField(read_only=True)


class JudgeSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    rank = serializers.CharField(required=False)
    bio_key = serializers.CharField(required=False)


class ClubDocumentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title_key = serializers.CharField()
    description_key = serializers.CharField(required=False)
    document_type = serializers.CharField()
    uploaded_at = serializers.DateTimeField(read_only=True)


class BoardMemberSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    position = serializers.CharField(required=False)
    bio_key = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    order = serializers.IntegerField(default=0)


class BreedStandardSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title_key = serializers.CharField()
    content_key = serializers.CharField(required=False)
    fci_number = serializers.CharField(required=False)
    version = serializers.CharField(required=False)


class BreedArticleSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title_key = serializers.CharField()
    content_key = serializers.CharField(required=False)
    category = serializers.CharField()


class UserProfileSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    is_nkp_member = serializers.BooleanField()
    membership_type = serializers.CharField(required=False)
    membership_expires_at = serializers.DateTimeField(required=False)


class KennelSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    prefix = serializers.CharField(required=False)
    site_url = serializers.URLField(required=False)
    created_at = serializers.DateTimeField(read_only=True)


class DogSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    registered_name = serializers.CharField(required=False)
    sex = serializers.CharField()
    date_of_birth = serializers.DateTimeField(required=False)
    pedigree_number = serializers.CharField(required=False)
    is_champion = serializers.BooleanField(default=False)


class LitterSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    whelped_at = serializers.DateTimeField(required=False)
    puppies_count = serializers.IntegerField(required=False)
    status = serializers.CharField()


class ApplicationSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    application_type = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)


class AchievementSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField()
    place = serializers.IntegerField(required=False)
    achieved_at = serializers.DateTimeField(required=False)
