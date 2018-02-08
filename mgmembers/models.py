from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator

import uuid

class Character(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='characters',
        related_query_name='character',
    )

    name = models.CharField(
        unique=True,
        max_length=255,
        null=False,
        blank=False,
    )

    jobs = models.ManyToManyField(
        'Job',
        through='CharacterJob',
        related_name='characters',
        related_query_name='character',
    )

    @property
    def primary_event_jobs(self):
        return self.jobs.filter(
            characterjob__event_status=CharacterJob.EVENT_PRIMARY
        )

    @property
    def secondary_event_jobs(self):
        return self.jobs.filter(
            characterjob__event_status=CharacterJob.EVENT_SECONDARY
        )

    @property
    def event_jobs_html(self):
        result = []
        result.append(", ".join(
            '<strong>%s</strong>' % (x.name) for x in self.primary_event_jobs
        ))
        result.append(", ".join(x.name for x in self.secondary_event_jobs))

        return ", ".join(x for x in result if x)

    @property
    def primary_gear_jobs(self):
        return self.jobs.filter(
            characterjob__gear_status=CharacterJob.GEAR_PRIMARY
        )

    @property
    def secondary_gear_jobs(self):
        return self.jobs.filter(
            characterjob__gear_status=CharacterJob.GEAR_SECONDARY
        )

    @property
    def gear_jobs_html(self):
        result = []
        result.append(", ".join(
            '<strong>%s</strong>' % (x.name) for x in self.primary_gear_jobs
        ))
        result.append(", ".join(x.name for x in self.secondary_gear_jobs))

        return ", ".join(x for x in result if x)

    def user_can_edit(self, user):
        if not user.is_authenticated:
            return False
        return self.owner.pk == user.pk

    def __str__(self):
        return self.name


class CharacterJob(models.Model):

    class Meta:
        ordering = ['event_status', 'gear_status', 'job_id']

    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name='characterjobs',
        related_query_name='characterjob',
    )
    job = models.ForeignKey(
        'Job',
        on_delete=models.CASCADE,
        related_name='characterjobs',
        related_query_name='characterjob',
    )

    level = models.PositiveIntegerField(
        choices=(
            ((None, "Not listed"),) +
            tuple((x, x) for x in range(1, 100))
        ),
        null=True,
        blank=True,
    )
    mastered = models.BooleanField(default=False)

    EVENT_PRIMARY = 1
    EVENT_SECONDARY = 2
    EVENT_NONE = 3

    event_status_choices = (
        (EVENT_NONE, "Do not use for events"),
        (EVENT_PRIMARY, "Primary event job"),
        (EVENT_SECONDARY, "Secondary event job"),
    )

    event_status = models.IntegerField(
        choices=event_status_choices,
        default=EVENT_NONE
    )

    GEAR_PRIMARY = 1
    GEAR_SECONDARY = 2
    GEAR_NONE = 3

    gear_status_choices = (
        (GEAR_NONE, "Not gearing this job"),
        (GEAR_PRIMARY, "Primary job for gear"),
        (GEAR_SECONDARY, "Secondary job for gear"),
    )

    gear_status = models.IntegerField(
        choices=gear_status_choices,
        default=GEAR_NONE
    )

    @property
    def mastered_html(self):
        if self.mastered:
            return (
                '<span class="fa fa-star master fa-xs"></span>'
                '<span class="fa fa-star master"></span>'
                '<span class="fa fa-star master fa-xs"></span>'
            )
        else:
            return ""

    @property
    def event_status_simple_display(self):
        if self.event_status == CharacterJob.EVENT_NONE:
            return ""
        else:
            return self.get_event_status_display()

    @property
    def gear_status_simple_display(self):
        if self.gear_status == CharacterJob.GEAR_NONE:
            return ""
        else:
            return self.get_gear_status_display()

    def __str__(self):
        return '%s (%s)' % (
            self.character.name if hasattr(self, 'character') else "<none>",
            self.job.name if hasattr(self, 'job') else "<none>"
        )


class Job(models.Model):

    class Meta:
        ordering = ['pk']

    WAR = "WAR"
    MNK = "MNK"
    WHM = "WHM"
    BLM = "BLM"
    RDM = "RDM"
    THF = "THF"
    PLD = "PLD"
    DRK = "DRK"
    BST = "BST"
    BRD = "BRD"
    RNG = "RNG"
    SAM = "SAM"
    NIN = "NIN"
    DRG = "DRG"
    SMN = "SMN"
    BLU = "BLU"
    COR = "COR"
    PUP = "PUP"
    DNC = "DNC"
    SCH = "SCH"
    GEO = "GEO"
    RUN = "RUN"

    job_choices = (
        (WAR, "Warrior"),
        (MNK, "Monk"),
        (WHM, "White Mage"),
        (BLM, "Black Mage"),
        (RDM, "Red Mage"),
        (THF, "Thief"),
        (PLD, "Paladin"),
        (DRK, "Dark Knight"),
        (BST, "Beastmaster"),
        (BRD, "Bard"),
        (RNG, "Ranger"),
        (SAM, "Samurai"),
        (NIN, "Ninja"),
        (DRG, "Dragoon"),
        (SMN, "Summoner"),
        (BLU, "Blue Mage"),
        (COR, "Corsair"),
        (PUP, "Puppetmaster"),
        (DNC, "Dancer"),
        (SCH, "Scholar"),
        (GEO, "Geomancer"),
        (RUN, "Rune Fencer"),
    )

    FULL_NAMES = {x[0]: x[1] for x in job_choices}

    name = models.CharField(
        max_length=3,
        unique=True,
        null=False,
        blank=False,
        choices=job_choices,
    )

    @classmethod
    def create_defaults(cls):
        for x in (x[0] for x in cls.job_choices):
            try:
                cls.objects.get(name=x)
            except Job.DoesNotExist:
                new_obj = cls(name=x)
                new_obj.save()

    @property
    def full_name(self):
        return Job.FULL_NAMES[self.name]

    def __str__(self):
        return self.full_name

    def __unicode__(self):
        return self.full_name


class OneTimeLoginNonce(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    target_user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        unique=True
    )

    def __str__(self):
        return 'Login nonce for %s' % self.target_user