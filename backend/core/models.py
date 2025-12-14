"""
Re-export Django ORM models so Django's app registry picks them up.
The actual model definitions live in models_django.py to keep the legacy MongoEngine code separate.
"""

from .models_django import *  # noqa: F401,F403

# Explicitly expose all model classes to help tools and type checkers
from .models_django import (
    ContentDictionary, ContentRevision,
    User, News, Page, Gallery,
    Judge, JudgeDetails, FastLink,
    Event, EventReport, Seminar,
    BreedStandard, BreedArticle,
    ClubDocument, BoardMember, MembershipPlan,
    Kennel, Dog, Litter,
    Application,
    Achievement, MembershipPayment,
    MemberBenefit, ProtectedMaterial,
    SiteMonitor, AuditLog,
)

__all__ = [
    'ContentDictionary', 'ContentRevision',
    'User', 'News', 'Page', 'Gallery',
    'Judge', 'JudgeDetails', 'FastLink',
    'Event', 'EventReport', 'Seminar',
    'BreedStandard', 'BreedArticle',
    'ClubDocument', 'BoardMember', 'MembershipPlan',
    'Kennel', 'Dog', 'Litter',
    'Application',
    'Achievement', 'MembershipPayment',
    'MemberBenefit', 'ProtectedMaterial',
    'SiteMonitor', 'AuditLog',
]
