# ✓ Successfully connected to MongoDB at mongodb:27017
# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AlembicVersion(models.Model):
    version_num = models.CharField(primary_key=True, max_length=32)

    class Meta:
        managed = False
        db_table = 'alembic_version'


class Breeder(models.Model):
    uuid = models.CharField(unique=True, blank=True, null=True)
    name = models.CharField()
    is_breeder = models.BooleanField()
    kennel = models.CharField(blank=True, null=True)
    breeder_url = models.CharField(blank=True, null=True)
    kennel_url = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'breeder'


class Dog(models.Model):
    uuid = models.CharField(unique=True)
    registered_name = models.CharField(blank=True, null=True)
    call_name = models.CharField(blank=True, null=True)
    link_name = models.CharField(blank=True, null=True)
    sex = models.IntegerField()
    year_of_birth = models.IntegerField(blank=True, null=True)
    month_of_birth = models.IntegerField(blank=True, null=True)
    day_of_birth = models.IntegerField(blank=True, null=True)
    date_of_birth = models.DateTimeField(blank=True, null=True)
    year_of_death = models.IntegerField(blank=True, null=True)
    month_of_death = models.IntegerField(blank=True, null=True)
    day_of_death = models.IntegerField(blank=True, null=True)
    date_of_death = models.DateTimeField(blank=True, null=True)
    land_of_birth = models.CharField(blank=True, null=True)
    land_of_birth_code = models.CharField(blank=True, null=True)
    land_of_standing = models.CharField(blank=True, null=True)
    size = models.FloatField(blank=True, null=True)
    weight = models.FloatField(blank=True, null=True)
    color = models.CharField(blank=True, null=True)
    color_marking = models.CharField(blank=True, null=True)
    eyes_color = models.CharField(blank=True, null=True)
    variety = models.CharField(blank=True, null=True)
    distinguishing_features = models.CharField(blank=True, null=True)
    prefix_titles = models.CharField(blank=True, null=True)
    suffix_titles = models.CharField(blank=True, null=True)
    other_titles = models.CharField(blank=True, null=True)
    registration_status = models.IntegerField(blank=True, null=True)
    registration_number = models.CharField(blank=True, null=True)
    brand_chip = models.CharField(blank=True, null=True)
    coi = models.FloatField(blank=True, null=True)
    coi_updated_on = models.DateTimeField(blank=True, null=True)
    incomplete_pedigree = models.BooleanField(blank=True, null=True)
    photo_url = models.CharField(blank=True, null=True)
    locked = models.BooleanField(blank=True, null=True)
    removed = models.BooleanField(blank=True, null=True)
    show_ad = models.BooleanField(blank=True, null=True)
    is_new = models.BooleanField(blank=True, null=True)
    modified = models.BooleanField(blank=True, null=True)
    modified_at = models.DateTimeField(blank=True, null=True)
    health_info_general = models.TextField(blank=True, null=True)  # This field type is a guess.
    health_info_genetic = models.TextField(blank=True, null=True)  # This field type is a guess.
    neutered = models.BooleanField(blank=True, null=True)
    approved_for_breeding = models.BooleanField(blank=True, null=True)
    frozen_semen = models.BooleanField(blank=True, null=True)
    artificial_insemination = models.BooleanField(blank=True, null=True)
    source = models.CharField(blank=True, null=True)
    has_conflicts = models.BooleanField(blank=True, null=True)
    conflicts = models.TextField(blank=True, null=True)  # This field type is a guess.
    kennel = models.CharField(blank=True, null=True)
    notes = models.CharField(blank=True, null=True)
    data_correctness_notes = models.CharField(blank=True, null=True)
    club = models.CharField(blank=True, null=True)
    sports = models.TextField(blank=True, null=True)  # This field type is a guess.
    dam_id = models.IntegerField(blank=True, null=True)
    dam_uuid = models.CharField(blank=True, null=True)
    dam_name = models.CharField(blank=True, null=True)
    dam_link_name = models.CharField(blank=True, null=True)
    sire_id = models.IntegerField(blank=True, null=True)
    sire_uuid = models.CharField(blank=True, null=True)
    sire_name = models.CharField(blank=True, null=True)
    sire_link_name = models.CharField(blank=True, null=True)
    birth_litter = models.ForeignKey('Litter', models.DO_NOTHING, blank=True, null=True)
    zooportal_id = models.CharField(blank=True, null=True)
    zoo_hash = models.CharField(max_length=64, blank=True, null=True, db_comment='Unique hash for dog identification across systems')

    class Meta:
        managed = False
        db_table = 'dog'


class Dogbreederlink(models.Model):
    dog = models.OneToOneField(Dog, models.DO_NOTHING, primary_key=True)  # The composite primary key (dog_id, breeder_id) found, that is not supported. The first column is selected.
    breeder = models.ForeignKey(Breeder, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'dogbreederlink'
        unique_together = (('dog', 'breeder'),)


class Dogownerlink(models.Model):
    dog = models.OneToOneField(Dog, models.DO_NOTHING, primary_key=True)  # The composite primary key (dog_id, owner_id) found, that is not supported. The first column is selected.
    owner = models.ForeignKey('Owner', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'dogownerlink'
        unique_together = (('dog', 'owner'),)


class Dogsiblinglink(models.Model):
    dog = models.OneToOneField(Dog, models.DO_NOTHING, primary_key=True)  # The composite primary key (dog_id, sibling_id) found, that is not supported. The first column is selected.
    sibling = models.ForeignKey(Dog, models.DO_NOTHING, related_name='dogsiblinglink_sibling_set')

    class Meta:
        managed = False
        db_table = 'dogsiblinglink'
        unique_together = (('dog', 'sibling'),)


class Litter(models.Model):
    date_of_birth = models.DateTimeField(blank=True, null=True)
    litter_male_count = models.IntegerField(blank=True, null=True)
    litter_female_count = models.IntegerField(blank=True, null=True)
    litter_undef_count = models.IntegerField(blank=True, null=True)
    sire = models.ForeignKey(Dog, models.DO_NOTHING, blank=True, null=True)
    dam = models.ForeignKey(Dog, models.DO_NOTHING, related_name='litter_dam_set', blank=True, null=True)
    mating_partner = models.ForeignKey(Dog, models.DO_NOTHING, related_name='litter_mating_partner_set', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'litter'


class MedicalRecord(models.Model):
    registry = models.CharField()
    test_date = models.DateTimeField(blank=True, null=True)
    report_date = models.DateTimeField(blank=True, null=True)
    age_in_months = models.IntegerField(blank=True, null=True)
    conclusion = models.CharField(blank=True, null=True)
    ofa_number = models.CharField(blank=True, null=True)
    source = models.CharField()
    notes = models.CharField(blank=True, null=True)
    dog = models.ForeignKey(Dog, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'medical_record'


class Mergelog(models.Model):
    dog = models.ForeignKey(Dog, models.DO_NOTHING)
    resolved_fields = models.TextField(blank=True, null=True)  # This field type is a guess.
    old_values = models.TextField(blank=True, null=True)  # This field type is a guess.
    new_values = models.TextField(blank=True, null=True)  # This field type is a guess.
    conflicts = models.TextField(blank=True, null=True)  # This field type is a guess.
    resolved_date = models.DateTimeField()
    resolved_by_user_id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mergelog'


class Owner(models.Model):
    uuid = models.CharField(unique=True, blank=True, null=True)
    name = models.CharField()
    is_main_owner = models.BooleanField()
    kennel = models.CharField(blank=True, null=True)
    owner_url = models.CharField(blank=True, null=True)
    kennel_url = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'owner'


class Title(models.Model):
    short_name = models.CharField()
    long_name = models.CharField(blank=True, null=True)
    is_prefix = models.BooleanField()
    has_winner_year = models.BooleanField(blank=True, null=True)
    winner_year = models.IntegerField(blank=True, null=True)
    dog = models.ForeignKey(Dog, models.DO_NOTHING)
    country = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'title'
        unique_together = (('dog', 'short_name', 'country'),)
