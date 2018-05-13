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

    def limit_to_two_primary(self):
        pjobs = CharacterJob.objects.filter(
            character=self,
            gear_status = CharacterJob.GEAR_PRIMARY
        )
        if len(pjobs) > 2:
            for x in pjobs[2:]:
                print("Changing %s %s to secondary" % (x.character, x.job))
                x.gear_status = CharacterJob.GEAR_SECONDARY
                x.save()

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


class OmenBossesClears(models.Model):
    character = models.OneToOneField(
        Character,
        on_delete=models.CASCADE
    )
    fu = models.BooleanField(
        verbose_name='Fu',
        default=False
    )
    kyou = models.BooleanField(
        verbose_name='Kyou',
        default=False
    )
    kei = models.BooleanField(
        verbose_name='Kei',
        default=False
    )
    gin = models.BooleanField(
        verbose_name='Gin',
        default=False
    )
    kin = models.BooleanField(
        verbose_name='Kin',
        default=False
    )


class OmenBossWishlist(models.Model):
    FU = 1
    KYOU = 2
    KEI = 3
    GIN = 4
    KIN = 5
    choices = (
        (None, '- None -'),
        (FU, 'Fu (BST, DRG, SMN, PUP)'),
        (KYOU, 'Kyou (BRD, COR, RNG, GEO)'),
        (KEI, 'Kei (SCH, BLM, WHM, RDM, BLU)'),
        (GIN, 'Gin (THF, NIN, DNC, RUN)'),
        (KIN, 'Kin (WAR, MNK, PLD, DRK, SAM)'),
    )
    character = models.OneToOneField(
        Character,
        on_delete=models.CASCADE
    )
    first_choice = models.IntegerField(
        choices=choices,
        null=True,
        default=None
    )
    second_choice = models.IntegerField(
        choices=choices,
        null=True,
        default=None
    )


class WarderOfCouragePops(models.Model):
    character = models.OneToOneField(
        Character,
        on_delete=models.CASCADE
    )
    primal_nazar = models.BooleanField(
        verbose_name='Primal Nazard / Full pop item',
        default=False
    )
    primary_nazar = models.BooleanField(
        verbose_name='Primary / Warder of Temperance',
        default=False
    )
    secondary_nazar = models.BooleanField(
        verbose_name='Secondary / Warder of Fortitude',
        default=False
    )
    tertiary_nazar = models.BooleanField(
        verbose_name='Tertiary / Warder of Faith',
        default=False
    )
    quaternary_nazar = models.BooleanField(
        verbose_name='Quaternary / Warder of Justice',
        default=False
    )
    quinary_nazar = models.BooleanField(
        verbose_name='Quinary / Warder of Hope',
        default=False
    )
    senary_nazar = models.BooleanField(
        verbose_name='Senary / Warder of Prudence',
        default=False
    )
    septenary_nazar = models.BooleanField(
        verbose_name='Septenary / Warder of Love',
        default=False
    )
    octonary_nazar = models.BooleanField(
        verbose_name='Octonary / Warder of Dignity',
        default=False
    )
    nonary_nazar = models.BooleanField(
        verbose_name='Nonary / Warder of Loyalty',
        default=False
    )
    denary_nazar = models.BooleanField(
        verbose_name='Denary / Warder of Mercy',
        default=False
    )


class DynamisGearChoices(models.Model):
    character = models.OneToOneField(
        Character,
        on_delete=models.CASCADE
    )

    sandoria_primary = models.ForeignKey(
        Job,
        verbose_name="San d'Oria #1",
        null=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="sdo_dyna_primary_choices",
        related_query_name="sdo_dyna_primary_choice",
    )
    sandoria_secondary = models.ForeignKey(
        Job,
        verbose_name="San d'Oria #2",
        null=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="sdo_dyna_secondary_choices",
        related_query_name="sdo_dyna_secondary_choice",
    )

    bastok_primary = models.ForeignKey(
        Job,
        verbose_name="Bastok #1",
        null=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="bastok_dyna_primary_choices",
        related_query_name="bastok_dyna_primary_choice",
    )
    bastok_secondary = models.ForeignKey(
        Job,
        verbose_name="Bastok #2",
        null=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="bastok_dyna_secondary_choices",
        related_query_name="bastok_dyna_secondary_choice",
    )

    windurst_primary = models.ForeignKey(
        Job,
        verbose_name="Windurst #1",
        null=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="windurst_dyna_primary_choices",
        related_query_name="windurst_dyna_primary_choice",
    )
    windurst_secondary = models.ForeignKey(
        Job,
        verbose_name="Windurst #2",
        null=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="windurst_dyna_secondary_choices",
        related_query_name="windurst_dyna_secondary_choice",
    )

    jeuno_primary = models.ForeignKey(
        Job,
        verbose_name="Jeuno #1",
        null=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="jeuno_dyna_primary_choices",
        related_query_name="jeuno_dyna_primary_choice",
    )
    jeuno_secondary = models.ForeignKey(
        Job,
        verbose_name="Jeuno #2",
        null=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="jeuno_dyna_secondary_choices",
        related_query_name="jeuno_dyna_secondary_choice",
    )

    body_primary = models.ForeignKey(
        Job,
        verbose_name="Body #1",
        null=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="body_dyna_primary_choices",
        related_query_name="body_dyna_primary_choice",
    )
    body_secondary = models.ForeignKey(
        Job,
        verbose_name="Body #2",
        null=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="body_dyna_secondary_choices",
        related_query_name="body_dyna_secondary_choice",
    )

    @property
    def sandoria_jobs(self):
        return [
            x.name
            for x in (self.sandoria_primary, self.sandoria_secondary) if x
        ]

    @property
    def bastok_jobs(self):
        return [
            x.name
            for x in (self.bastok_primary, self.bastok_secondary) if x
        ]

    @property
    def windurst_jobs(self):
        return [
            x.name
            for x in (self.windurst_primary, self.windurst_secondary) if x
        ]

    @property
    def jeuno_jobs(self):
        return [
            x.name
            for x in (self.jeuno_primary, self.jeuno_secondary) if x
        ]

    @property
    def body_jobs(self):
        return [
            x.name
            for x in (self.body_primary, self.body_secondary) if x
        ]

    @classmethod
    def import_from_gear_choices(cls):
        for character in Character.objects.all():
            if hasattr(character, 'dynamisgearchoices'):
                continue
            
            item = cls(character=character)

            pjobs = tuple(character.primary_gear_jobs)
            if len(pjobs) > 0:
                item.sandoria_primary = pjobs[0]
                item.bastok_primary = pjobs[0]
                item.windurst_primary = pjobs[0]
            if len(pjobs) > 1:
                item.sandoria_secondary = pjobs[1]
                item.bastok_secondary = pjobs[1]
                item.windurst_secondary = pjobs[1]

            item.save()
