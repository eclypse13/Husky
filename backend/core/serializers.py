from rest_framework import serializers
from . import models_django as models


class ContentDictionarySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ContentDictionary
        fields = '__all__'


class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.News
        fields = '__all__'


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Page
        fields = '__all__'
        lookup_field = 'slug'


class GallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Gallery
        fields = '__all__'


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Event
        fields = '__all__'


# class EventReportSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.EventReport
#         fields = '__all__'

# serializers.py


class EventReportSerializer(serializers.ModelSerializer):
    event_title_key = serializers.CharField(source="event.title_key", read_only=True)
    event_description_key = serializers.CharField(source="event.description_key", read_only=True)
    event_starts_at = serializers.DateTimeField(source="event.starts_at", read_only=True)
    event_location = serializers.CharField(source="event.location", read_only=True)

    class Meta:
        model = models.EventReport
        fields = [
            "id",
            "event",                 # id события
            "event_title_key",       # ключ заголовка (потом переведёшь через dict на фронте)
            "event_description_key",
            "event_starts_at",
            "event_location",
            "photos",
            "videos",
            "results",
            "created_at",
        ]



class JudgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Judge
        fields = '__all__'

class JudgeDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.JudgeDetails
        fields = '__all__'


class ClubDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ClubDocument
        fields = '__all__'


class BoardMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BoardMember
        fields = '__all__'


class BreedStandardSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BreedStandard
        fields = '__all__'


class BreedArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BreedArticle
        fields = '__all__'


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone', 'city',
            'is_nkp_member', 'membership_type', 'membership_expires_at'
        ]


class KennelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Kennel
        fields = '__all__'


class DogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Dog
        fields = '__all__'


class LitterSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Litter
        fields = '__all__'


class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Application
        fields = '__all__'


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Achievement
        fields = '__all__'
