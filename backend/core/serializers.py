import mimetypes
import os

from rest_framework import serializers
from . import models_django as models


class ContentDictionarySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ContentDictionary
        fields = '__all__'


class SiteBannerSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SiteBannerSettings
        fields = ("is_enabled", "message", "updated_at")


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

    photos = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()

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
            "result_description",
            "created_at",
        ]

    def get_photos(self, obj):
        request = self.context.get("request")
        urls = []
        for p in obj.photo_items.all():
            url = p.file.url
            urls.append(request.build_absolute_uri(url) if request else url)
        return urls

    def get_videos(self, obj):
        request = self.context.get("request")
        urls = []
        for v in obj.video_items.all():
            url = v.file.url
            urls.append(request.build_absolute_uri(url) if request else url)
        return urls


class RaceSerializer(serializers.ModelSerializer):
    tabLabel = serializers.SerializerMethodField()
    club = serializers.CharField(source="organization", default="")
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = models.Race
        fields = [
            "id",
            "tabLabel",
            "title",
            "date",
            "location",
            "club",
            "organizers",
            "judge",
            "distances",
            "status",
            "status_display",
        ]

    def get_tabLabel(self, obj):
        return f"🏁 «{obj.title}» — {obj.date.strftime('%d %b.')}"


class SportsSeasonSerializer(serializers.ModelSerializer):
    badge = serializers.CharField(source="name")
    title = serializers.SerializerMethodField()
    meta = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    races = RaceSerializer(many=True, read_only=True)

    class Meta:
        model = models.Season
        fields = [
            "id",
            "badge",
            "title",
            "meta",
            "stats",
            "races",
        ]

    def get_title(self, obj):
        return f"Сезон {obj.name.lower()}"

    def get_meta(self, obj):
        races = obj.races.all()
        participants = sum(r.participants_count or 0 for r in races)
        cities = [r.city for r in races if r.city]
        cities_text = " · ".join(dict.fromkeys(cities)) if cities else "—"

        return [
            f"📅 {obj.start_date.strftime('%d.%m.%Y')}–{obj.end_date.strftime('%d.%m.%Y')}",
            f"🐕 {participants} участников",
            f"📍 {cities_text}",
        ]

    def get_stats(self, obj):
        races = obj.races.all()
        participants = sum(r.participants_count or 0 for r in races)
        judges = len(set(r.judge for r in races if r.judge))

        return {
            "races": str(races.count()),
            "participants": str(participants),
            "judges": str(judges),
            "disciplines": "—",
            "purebred": "100%",
        }

class JudgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Judge
        fields = '__all__'

class JudgeDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.JudgeDetails
        fields = '__all__'


class ClubDocumentSerializer(serializers.ModelSerializer):
    file_size = serializers.SerializerMethodField()
    file_ext = serializers.SerializerMethodField()
    # можно ещё mime_type, если надо:
    mime_type = serializers.SerializerMethodField()

    class Meta:
        model = models.ClubDocument
        fields = (
            "id", "title_key", "description_key", "file", "document_type", "uploaded_at",
            "file_size", "file_ext", "mime_type", "order",
        )

    def get_file_size(self, obj):
        f = getattr(obj, "file", None)
        if not f:
            return None
        try:
            return f.size  # байты
        except Exception:
            return None

    def get_file_ext(self, obj):
        f = getattr(obj, "file", None)
        if not f or not getattr(f, "name", None):
            return None
        ext = os.path.splitext(f.name)[1].lstrip(".").upper()
        return ext or None

    def get_mime_type(self, obj):
        f = getattr(obj, "file", None)
        if not f or not getattr(f, "name", None):
            return None
        mime, _ = mimetypes.guess_type(f.name)
        return mime


class ClubStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ClubStats
        fields = (
            "members_count",
            "kennels_count",
            "dogs_in_archive_count",
            "regions_count",
            "updated_at",
        )


class BoardMemberSerializer(serializers.ModelSerializer):
    working_group_id = serializers.IntegerField(read_only=True)
    class Meta:
        model = models.BoardMember
        fields = '__all__'


class WorkingGroupSerializer(serializers.ModelSerializer):
    members = BoardMemberSerializer(many=True, read_only=True)

    class Meta:
        model = models.WorkingGroup
        fields = ("id", "name", "members")

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
