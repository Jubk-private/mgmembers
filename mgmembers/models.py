from django.db import models
from django.db import transaction
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator
from django.utils import timezone
import os
import uuid
import datetime
import lupa


RECENT_EDIT_INTERVAL = datetime.timedelta(minutes=60)
EDITING_BLOCKED_INTERVAL = datetime.timedelta(days=60)

def read_lua_data_from_file(f, start_marker="return"):
    lua = lupa.LuaRuntime()
    luacode = ""
    for line in f:
        if luacode:
            if line.startswith("}"):
                luacode += "}"
                break
            else:
                luacode += line
        else:
            if line.startswith(start_marker):
                luacode = "{"

    return lua.eval(luacode)

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

    healing_job_names = (WHM, SCH, RDM, PUP)
    tank_job_names = (RUN, PLD, NIN, PUP, WAR)
    support_job_names = (GEO, COR, BRD, RDM, SMN, BLU)
    nuke_job_names = (BLM, SCH, GEO, SMN, PUP)
    dd_job_names = (
        WAR, MNK, THF, DRK, BST, RNG, SAM, NIN, DRG, SMN, BLU, COR, PUP,
        DNC, RUN
    )
    ranged_job_names = (RNG, COR, PUP, SMN, SAM)


    name = models.CharField(
        max_length=3,
        unique=True,
        null=False,
        blank=False,
        choices=job_choices,
    )

    @classmethod
    def healing_jobs(cls):
        return cls.objects.filter(name__in=cls.healing_job_names)

    @classmethod
    def tank_jobs(cls):
        return cls.objects.filter(name__in=cls.tank_job_names)

    @classmethod
    def support_jobs(cls):
        return cls.objects.filter(name__in=cls.support_job_names)

    @classmethod
    def nuke_jobs(cls):
        return cls.objects.filter(name__in=cls.nuke_job_names)

    @classmethod
    def ranged_jobs(cls):
        return cls.objects.filter(name__in=cls.ranged_job_names)

    @classmethod
    def dd_jobs(cls):
        return cls.objects.filter(name__in=cls.dd_job_names)

    @classmethod
    def create_defaults(cls):
        for x in (x[0] for x in cls.job_choices):
            try:
                cls.objects.get(name=x)
            except Job.DoesNotExist:
                new_obj = cls(name=x)
                new_obj.save()

    @classmethod
    def bitmask_to_qs(cls, bitmask):
        names = set()
        if bitmask & 1 << 1:
            names.add(Job.WAR)
        if bitmask & 1 << 2:
            names.add(Job.MNK)
        if bitmask & 1 << 3:
            names.add(Job.WHM)
        if bitmask & 1 << 4:
            names.add(Job.BLM)
        if bitmask & 1 << 5:
            names.add(Job.RDM)
        if bitmask & 1 << 6:
            names.add(Job.THF)
        if bitmask & 1 << 7:
            names.add(Job.PLD)
        if bitmask & 1 << 8:
            names.add(Job.DRK)
        if bitmask & 1 << 9:
            names.add(Job.BST)
        if bitmask & 1 << 10:
            names.add(Job.BRD)
        if bitmask & 1 << 11:
            names.add(Job.RNG)
        if bitmask & 1 << 12:
            names.add(Job.SAM)
        if bitmask & 1 << 13:
            names.add(Job.NIN)
        if bitmask & 1 << 14:
            names.add(Job.DRG)
        if bitmask & 1 << 15:
            names.add(Job.SMN)
        if bitmask & 1 << 16:
            names.add(Job.BLU)
        if bitmask & 1 << 17:
            names.add(Job.COR)
        if bitmask & 1 << 18:
            names.add(Job.PUP)
        if bitmask & 1 << 19:
            names.add(Job.DNC)
        if bitmask & 1 << 20:
            names.add(Job.SCH)
        if bitmask & 1 << 21:
            names.add(Job.GEO)
        if bitmask & 1 << 22:
            names.add(Job.RUN)

        return cls.objects.filter(name__in=names)
        

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

    last_change = models.DateTimeField(
        null=True,
        default=None
    )

    sandoria_primary = models.ForeignKey(
        Job,
        verbose_name="San d'Oria #1",
        null=True,
        blank=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="sdo_dyna_primary_choices",
        related_query_name="sdo_dyna_primary_choice",
    )
    sandoria_secondary = models.ForeignKey(
        Job,
        verbose_name="San d'Oria #2",
        null=True,
        blank=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="sdo_dyna_secondary_choices",
        related_query_name="sdo_dyna_secondary_choice",
    )

    bastok_primary = models.ForeignKey(
        Job,
        verbose_name="Bastok #1",
        null=True,
        blank=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="bastok_dyna_primary_choices",
        related_query_name="bastok_dyna_primary_choice",
    )
    bastok_secondary = models.ForeignKey(
        Job,
        verbose_name="Bastok #2",
        null=True,
        blank=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="bastok_dyna_secondary_choices",
        related_query_name="bastok_dyna_secondary_choice",
    )

    windurst_primary = models.ForeignKey(
        Job,
        verbose_name="Windurst #1",
        null=True,
        blank=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="windurst_dyna_primary_choices",
        related_query_name="windurst_dyna_primary_choice",
    )
    windurst_secondary = models.ForeignKey(
        Job,
        verbose_name="Windurst #2",
        null=True,
        blank=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="windurst_dyna_secondary_choices",
        related_query_name="windurst_dyna_secondary_choice",
    )

    jeuno_primary = models.ForeignKey(
        Job,
        verbose_name="Jeuno #1",
        null=True,
        blank=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="jeuno_dyna_primary_choices",
        related_query_name="jeuno_dyna_primary_choice",
    )
    jeuno_secondary = models.ForeignKey(
        Job,
        verbose_name="Jeuno #2",
        null=True,
        blank=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="jeuno_dyna_secondary_choices",
        related_query_name="jeuno_dyna_secondary_choice",
    )

    body_primary = models.ForeignKey(
        Job,
        verbose_name="Body #1",
        null=True,
        blank=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="body_dyna_primary_choices",
        related_query_name="body_dyna_primary_choice",
    )
    body_secondary = models.ForeignKey(
        Job,
        verbose_name="Body #2",
        null=True,
        blank=True,
        default=None,
        on_delete = models.CASCADE,
        related_name="body_dyna_secondary_choices",
        related_query_name="body_dyna_secondary_choice",
    )

    @property
    def can_be_edited(self):
        return self.recently_edited or not self.blocked_from_editing

    @property
    def recently_edited(self):
        return (
            self.last_change and
            (timezone.now() - self.last_change) < RECENT_EDIT_INTERVAL
        )

    @property
    def blocked_from_editing(self):
        return (
            self.last_change and
            (timezone.now() - self.last_change) <= EDITING_BLOCKED_INTERVAL
        )

    @property
    def recent_edit_timeout(self):
        return self.last_change + RECENT_EDIT_INTERVAL

    @property
    def next_edit_time(self):
        return self.last_change + EDITING_BLOCKED_INTERVAL

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

    def __str__(self):
        return "DynamisGearChoices for %s" % self.character

class RemaAugmentChoice(models.Model):
    RELIC = 1
    MYTHIC = 2
    EMPYREAN = 3
    AEONIC = 4
    ERGON = 5
    choices = (
        (None, '- None -'),
        (RELIC, 'Relic / Ancient'),
        (MYTHIC, 'Mythic / Balrahn'),
        (EMPYREAN, 'Empyrean / Secret Moogle'),
        (AEONIC, 'Aeonic / Familair'),
        (ERGON, 'Ergon / Mysterious')
    )
    player = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )
    rema_choice=models.IntegerField(
        choices=choices,
        null=True,
        default=None
    )

class RegisteredAlliance(models.Model):
    register_time = models.DateTimeField(default=timezone.now)
    registered_by = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )
    zone = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    characters = models.ManyToManyField(Character)

    def __str__(self):
        return '%s, %s in %s: %d members' % (
            self.registered_by,
            self.register_time.strftime("%Y-%m-%d %H:%M:%S"),
            self.zone,
            self.characters.count()
        )


class Race(models.Model):
    name = models.CharField(max_length=60)
    name_ja = models.CharField(max_length=60)
    gender = models.CharField(max_length=3, null=True)

    GENDER_MALE = "♂"
    GENDER_FEMALE = "♀"

    defaults = [
        dict(id=0,en="Precomposed NPC",ja="合成済みのNPC",gender=None),
        dict(id=1,en="Hume ♂",ja="ヒューム♂",gender="♂"),
        dict(id=2,en="Hume ♀",ja="ヒューム♀",gender="♀"),
        dict(id=3,en="Elvaan ♂",ja="エㇽバン♂",gender="♂"),
        dict(id=4,en="Elvaan ♀",ja="エㇽバン♀",gender="♀"),
        dict(id=5,en="Tarutaru ♂",ja="タルタル♂",gender="♂"),
        dict(id=6,en="Tarutaru ♀",ja="タルタル♀",gender="♀"),
        dict(id=7,en="Mithra",ja="ミスラ",gender="♀"),
        dict(id=8,en="Galka",ja="ガㇽカ",gender="♂"),
        dict(id=29,en="Mithra Child",ja="ミスラの子",gender="♀"),
        dict(id=30,en="Elvaan Hume Child ♀",ja="エㇽ・ヒュームの子♀",gender="♀"),
        dict(id=31,en="Elvaan Hume Child ♂",ja="エㇽ・ヒュームの子♂",gender="♂"),
        dict(id=32,en="Chocobo Rounsey",ja="チョコボ黄",gender=None),
        dict(id=33,en="Chocobo Destrier",ja="チョコボ黒",gender=None),
        dict(id=34,en="Chocobo Palfrey",ja="チョコボ赤",gender=None),
        dict(id=35,en="Chocobo Courser",ja="チョコボ青",gender=None),
        dict(id=36,en="Chocobo Jennet",ja="チョコボ緑",gender=None),
    ]

    def __str__(self):
        return self.name

    @classmethod
    def create_defaults(cls):
        for x in cls.defaults:
            data = dict(
                id=x["id"],
                name=x["en"],
                name_ja=x["ja"],
                gender=x["gender"],
            )
            try:
                obj = cls.objects.get(pk=data["id"])
                del data["id"]
                cls.objects.filter(pk=obj.pk).update(**data)
            except cls.DoesNotExist:
                obj = cls(**data)
                obj.save()

    @classmethod
    def bitmask_to_qs(cls, bitmask):
        ids = []
        for data in cls.defaults:
            if bitmask & (1 << data["id"]):
                ids.append(data["id"])

        return cls.objects.filter(pk__in=ids)

class ItemCategory(models.Model):
    name = models.CharField(max_length=60)

    @classmethod
    def get_or_create(cls, name):
        try:
            obj = cls.objects.get(name=name)
        except cls.DoesNotExist:
            obj = cls(name=name)
            obj.save()

        return obj

    def __str__(self):
        return self.name


class ItemType(models.Model):
    name = models.CharField(max_length=60)

    defaults = (
        (1, "General"),
        (2, "General II"),
        (3, "Big Fish"),
        (4, "Weapon"),
        (5, "Armor"),
        (6, "Linkshell"),
        (7, "Tool / Key"),
        (7, "Crystal"),
        (10, "Furniture"),
        (11, "Seeds"),
        (12, "Flowerpot"),
        (14, "Mannequin"),
        (15, "PvP related"),
        (16, "Chocobo raising related"),
        (17, "Chocobo racing related"),
        (18, "Soul plate / Fiend plate"),
        (19, "Soul reflector"),
        (20, "Assault logs"),
        (21, "Mog Bonana Marble"),
        (22, "MMM related"),
        (23, "MMM related II"),
        (24, "MMM related III"),
        (25, "MMM related IV"),
        (26, "Evolith"),
        (27, "Storage slip"),
        (28, "Legion pass"),
        (29, "Meeble Burrows related"),
        (31, "Crafting set"),
    )

    def __str__(self):
        return self.name

    @classmethod
    def create_defaults(cls):
        for (id, name) in cls.defaults:
            try:
                obj = cls.objects.get(pk=id)
            except cls.DoesNotExist:
                obj = cls(pk=id)
            obj.name = name
            obj.save()

    @classmethod
    def get_or_create(cls, id):
        try:
            obj = cls.objects.get(pk=id)
        except cls.DoesNotExist:
            obj = cls(pk=id)
            obj.name = 'Unknown type with id <%s>' % (id)
            obj.save()

        return obj


class Target(models.Model):
    name = models.CharField(max_length=60)

    defaults = (
        (0x01, 'Self'),
        (0x02, 'Player'),
        (0x04, 'Party'),
        (0x08, 'Ally'),
        (0x10, 'NPC'),
        (0x20, 'Enemy'),
        (0x60, 'Object'),
        (0x9D, 'Corpse'),
    )

    def __str__(self):
        return self.name

    @classmethod
    def create_defaults(cls):
        for (id, name) in cls.defaults:
            try:
                obj = cls.objects.get(pk=id)
            except cls.DoesNotExist:
                obj = cls(pk=id)
            obj.name = name
            obj.save()


    @classmethod
    def bitmask_to_qs(cls, bitmask):
        ids = []
        for (id, name) in cls.defaults:
            if bitmask & id:
                ids.append(id)
        
        return cls.objects.filter(pk__in=ids)


class ItemFlag(models.Model):
    name = models.CharField(max_length=60)

    defaults = (
        (0x0001, 'Flag00'),
        (0x0002, 'Flag01'),
        (0x0004, 'Flag02'),
        (0x0008, 'Flag03'),
        (0x0010, 'Can Send POL'),
        (0x0020, 'Inscribable'),
        (0x0040, 'No Auction'),
        (0x0080, 'Scroll'),
        (0x0100, 'Linkshell'),
        (0x0200, 'Usable'),
        (0x0400, 'NPC Tradeable'),
        (0x0800, 'Equippable'),
        (0x1000, 'No NPC Sale'),
        (0x2000, 'No Delivery'),
        (0x4000, 'No PC Trade'),
        (0x8000, 'Rare'),
        (0x6040, 'Exclusive'),
    )

    def __str__(self):
        return self.name

    @classmethod
    def create_defaults(cls):
        for (id, name) in cls.defaults:
            try:
                obj = cls.objects.get(pk=id)
            except cls.DoesNotExist:
                obj = cls(pk=id)
            obj.name = name
            obj.save()


    @classmethod
    def bitmask_to_qs(cls, bitmask):
        ids = []
        for (id, name) in cls.defaults:
            if bitmask & id:
                ids.append(id)

        return cls.objects.filter(pk__in=ids)


class ItemSlot(models.Model):
    name = models.CharField(max_length=60)

    defaults = (
        # Note that database IDs will be incremented by one
        dict(id=0,en="Main"),
        dict(id=1,en="Sub"),
        dict(id=2,en="Range"),
        dict(id=3,en="Ammo"),
        dict(id=4,en="Head"),
        dict(id=5,en="Body"),
        dict(id=6,en="Hands"),
        dict(id=7,en="Legs"),
        dict(id=8,en="Feet"),
        dict(id=9,en="Neck"),
        dict(id=10,en="Waist"),
        dict(id=11,en="Left Ear"),
        dict(id=12,en="Right Ear"),
        dict(id=13,en="Left Ring"),
        dict(id=14,en="Right Ring"),
        dict(id=15,en="Back"),
    )

    def __str__(self):
        return self.name

    @classmethod
    def create_defaults(cls):
        for x in cls.defaults:
            try:
                obj = cls.objects.get(pk=x["id"])
                obj.name = x["en"]
                obj.save()
            except cls.DoesNotExist:
                obj = cls(pk=x["id"], name=x["en"])
                obj.save()

    @classmethod
    def bitmask_to_qs(cls, bitmask):
        ids = []
        for x in cls.defaults:
            if bitmask & (1 << x["id"]):
                ids.append(x["id"])

        return cls.objects.filter(pk__in=ids)


class SkillCategory(models.Model):
    name = models.CharField(max_length=60, null=True)

    @classmethod
    def get_or_create(cls, name):
        try:
            obj = cls.objects.get(name=name)
        except cls.DoesNotExist:
            obj = cls(name=name)
            obj.save()

        return obj

    def __str__(self):
        return self.name


class Skill(models.Model):
    name = models.CharField(max_length=60)
    name_ja = models.CharField(max_length=60)
    category = models.ForeignKey(
        SkillCategory,
        on_delete=models.SET_NULL,
        null=True,
    )

    defaults = (
        dict(id=0,en="(N/A)",ja="(N/A)",category=None),
        dict(id=1,en="Hand-to-Hand",ja="格闘",category="Combat"),
        dict(id=2,en="Dagger",ja="短剣",category="Combat"),
        dict(id=3,en="Sword",ja="片手剣",category="Combat"),
        dict(id=4,en="Great Sword",ja="両手剣",category="Combat"),
        dict(id=5,en="Axe",ja="片手斧",category="Combat"),
        dict(id=6,en="Great Axe",ja="両手斧",category="Combat"),
        dict(id=7,en="Scythe",ja="両手鎌",category="Combat"),
        dict(id=8,en="Polearm",ja="両手槍",category="Combat"),
        dict(id=9,en="Katana",ja="片手刀",category="Combat"),
        dict(id=10,en="Great Katana",ja="両手刀",category="Combat"),
        dict(id=11,en="Club",ja="片手棍",category="Combat"),
        dict(id=12,en="Staff",ja="両手棍",category="Combat"),
        dict(id=22,en="Automaton Melee",ja="白兵戦",category="Puppet"),
        dict(id=23,en="Automaton Archery",ja="射撃戦",category="Puppet"),
        dict(id=24,en="Automaton Magic",ja="魔法戦",category="Puppet"),
        dict(id=25,en="Archery",ja="弓術",category="Combat"),
        dict(id=26,en="Marksmanship",ja="射撃",category="Combat"),
        dict(id=27,en="Throwing",ja="投てき",category="Combat"),
        dict(id=28,en="Guard",ja="ガード",category="Combat"),
        dict(id=29,en="Evasion",ja="回避",category="Combat"),
        dict(id=30,en="Shield",ja="盾",category="Combat"),
        dict(id=31,en="Parrying",ja="受け流し",category="Combat"),
        dict(id=32,en="Divine Magic",ja="神聖魔法",category="Magic"),
        dict(id=33,en="Healing Magic",ja="回復魔法",category="Magic"),
        dict(id=34,en="Enhancing Magic",ja="強化魔法",category="Magic"),
        dict(id=35,en="Enfeebling Magic",ja="弱体魔法",category="Magic"),
        dict(id=36,en="Elemental Magic",ja="精霊魔法",category="Magic"),
        dict(id=37,en="Dark Magic",ja="暗黒魔法",category="Magic"),
        dict(id=38,en="Summoning Magic",ja="召喚魔法",category="Magic"),
        dict(id=39,en="Ninjutsu",ja="忍術",category="Magic"),
        dict(id=40,en="Singing",ja="歌唱",category="Magic"),
        dict(id=41,en="Stringed Instrument",ja="弦楽器",category="Magic"),
        dict(id=42,en="Wind Instrument",ja="管楽器",category="Magic"),
        dict(id=43,en="Blue Magic",ja="青魔法",category="Magic"),
        dict(id=44,en="Geomancy",ja="風水魔法",category="Magic"),
        dict(id=45,en="Handbell",ja="風水鈴",category="Magic"),
        dict(id=48,en="Fishing",ja="釣り",category="Synthesis"),
        dict(id=49,en="Woodworking",ja="木工",category="Synthesis"),
        dict(id=50,en="Smithing",ja="鍛冶",category="Synthesis"),
        dict(id=51,en="Goldsmithing",ja="彫金",category="Synthesis"),
        dict(id=52,en="Clothcraft",ja="裁縫",category="Synthesis"),
        dict(id=53,en="Leathercraft",ja="革細工",category="Synthesis"),
        dict(id=54,en="Bonecraft",ja="骨細工",category="Synthesis"),
        dict(id=55,en="Alchemy",ja="錬金術",category="Synthesis"),
        dict(id=56,en="Cooking",ja="調理",category="Synthesis"),
        dict(id=57,en="Synergy",ja="錬成",category="Synthesis"),
    )

    def __str__(self):
        return self.name

    @classmethod
    def create_defaults(cls):
        for x in cls.defaults:
            data = dict(
                id=x["id"],
                name=x["en"],
                name_ja=x["ja"],
                category=SkillCategory.get_or_create(x["category"])
            )
            try:
                obj = cls.objects.get(pk=data["id"])
                del data["id"]
                cls.objects.filter(pk=obj.pk).update(**data)
            except cls.DoesNotExist:
                obj = cls(**data)

            obj.save()

    @classmethod
    def get_or_create(cls, id):
        try:
            obj = cls.objects.get(id=id)
        except cls.DoesNotExist:
            obj = cls(
                id=id,
                name="Unknown skill with id %s" % (id,),
                category=None,
            )
            obj.save()



class Item(models.Model):

    STACK_SINGLE = 1
    STACK_SMALL = 12
    STACK_LARGE = 99

    name = models.CharField(max_length=60)
    name_ja = models.CharField(max_length=60)
    stack = models.IntegerField(
        choices = (
            (STACK_SINGLE, STACK_SINGLE),
            (STACK_SMALL, STACK_SMALL),
            (STACK_LARGE, STACK_LARGE),
        ),
        null=True,
    )
    cast_time = models.IntegerField(null=True)
    level = models.IntegerField(null=True)
    cast_delay = models.IntegerField(null=True)
    max_charges = models.IntegerField(null=True)
    recast_delay = models.IntegerField(null=True)
    shield_size = models.IntegerField(null=True)
    damage = models.IntegerField(null=True)
    delay = models.IntegerField(null=True)
    item_level = models.IntegerField(null=True)
    superior_level = models.IntegerField(null=True)

    category = models.ForeignKey(
        ItemCategory,
        on_delete=models.SET_NULL,
        null=True
    )
    type = models.ForeignKey(
        ItemType,
        on_delete=models.SET_NULL,
        null=True
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.SET_NULL,
        null=True
    )
    jobs = models.ManyToManyField(Job)
    races = models.ManyToManyField(Race)
    flags = models.ManyToManyField(ItemFlag)
    targets = models.ManyToManyField(Target)
    slots = models.ManyToManyField(ItemSlot)

    description =  models.TextField()

    def __str__(self):
        return self.name

    def set_jobs_by_bitmask(self, bitmask):
        new_jobs = Job.get_jobs_from_bitmask(bitmask)
        self.jobs.exclude(pk__in=new_jobs).delete()
        self.jobs.add(new_jobs)

    @classmethod
    @transaction.atomic
    def create_defaults(cls):
        items_file = os.path.join(settings.FFXI_RES_FILES_DIR, "items.lua")
        with open(items_file, encoding="utf8") as f:
            lua_items = read_lua_data_from_file(f)


            for lua_item in lua_items.values():
                print("Importing item %s" % (lua_item["id"]))
                try:
                    item = cls.objects.get(id=lua_item["id"])
                except cls.DoesNotExist:
                    item = cls()
                for attr, key in (
                    ("id", "id"),
                    ("name", "en"),
                    ("name_ja", "ja"),
                    ("stack", "stack"),
                    ("cast_time", "cast_time"),
                    ("level", "level"),
                    ("cast_delay", "cast_delay"),
                    ("max_charges","max_charges"),
                    ("recast_delay", "recast_delay"),
                    ("shield_size", "shield_size"),
                    ("damage", "damage"),
                    ("delay", "delay"), 
                    ("item_level", "item_level"),
                    ("superior_level", "superior_level"),
                ):
                    if key in lua_item:
                        setattr(item, attr, lua_item[key])

                if "category" in lua_item:
                    value = lua_item["category"]
                    item.category = ItemCategory.get_or_create(value)

                if "type" in lua_item:
                    value = lua_item["type"]
                    item.type = ItemType.get_or_create(value)

                if "skill" in lua_item:
                    value = lua_item["skill"]
                    item.skill = Skill.get_or_create(value)

                item.save()

                if "flags" in lua_item:
                    value = int(lua_item["flags"])
                    qs = ItemFlag.bitmask_to_qs(value)
                    item.flags.clear()
                    for x in qs:
                        item.flags.add(x)

                if "targets" in lua_item:
                    value = int(lua_item["targets"])
                    qs = Target.bitmask_to_qs(value)
                    item.targets.clear()
                    for x in qs:
                        item.targets.add(x)

                if "jobs" in lua_item:
                    value = int(lua_item["jobs"])
                    qs = Job.bitmask_to_qs(value)
                    item.jobs.clear()
                    for x in qs:
                        item.jobs.add(x)

                if "races" in lua_item:
                    value = int(lua_item["races"])
                    qs = Race.bitmask_to_qs(value)
                    item.races.clear()
                    for x in qs:
                        item.races.add(x)

                if "slots" in lua_item:
                    value = int(lua_item["slots"])
                    qs = ItemSlot.bitmask_to_qs(value)
                    item.slots.clear()
                    for x in qs:
                        item.slots.add(x)


class AeonicNM(models.Model):
    name = models.CharField(max_length=60)
    
    AREA_ZITAH = 1 
    AREA_RUAUN = 2 
    AREA_REISENJIMA = 3 
    
    area_choices = (
        (AREA_ZITAH, "Escha - Zi'Tah"),
        (AREA_RUAUN, "Escha - Ru'Aun"),
        (AREA_REISENJIMA, "Reisenjima"),
    )
        
    area = models.IntegerField(
        choices=area_choices,
        default=AREA_ZITAH
    )

    TYPE_TIER_1 = 1
    TYPE_TIER_2 = 2
    TYPE_TIER_3 = 3
    TYPE_ARK_ANGELS = 4
    TYPE_HEAVENLY_BEASTS = 5
    TYPE_NAZAR = 6
    TYPE_HELM_1 = 7
    TYPE_HELM_2 = 8

    type_choices = (
        (TYPE_TIER_1, "Tier 1"),
        (TYPE_TIER_2, "Tier 2"),
        (TYPE_TIER_3, "Tier 3"),
        (TYPE_ARK_ANGELS, "Ark Angels"),
        (TYPE_HEAVENLY_BEASTS, "Heavenly Beasts"),
        (TYPE_NAZAR, "Nazar NM"),
        (TYPE_HELM_1, "H.E.L.M. tier 1"),
        (TYPE_HELM_2, "H.E.L.M. tier 2"),
    )

    type = models.IntegerField(
        choices = type_choices,
        default = TYPE_TIER_1
    )

    @classmethod
    def create_defaults(cls):
        for x in (
            # Zitah tier 1
            ("Aglaophotis", cls.AREA_ZITAH, cls.TYPE_TIER_1),
            ("Angrboda", cls.AREA_ZITAH, cls.TYPE_TIER_1),
            ("Cunnast", cls.AREA_ZITAH, cls.TYPE_TIER_1),
            ("Ferrodon", cls.AREA_ZITAH, cls.TYPE_TIER_1),
            ("Gestalt", cls.AREA_ZITAH, cls.TYPE_TIER_1),
            ("Gulltop", cls.AREA_ZITAH, cls.TYPE_TIER_1),
            ("Lustful Lydia", cls.AREA_ZITAH, cls.TYPE_TIER_1),
            ("Revetaur", cls.AREA_ZITAH, cls.TYPE_TIER_1),
            ("Tangata Manu", cls.AREA_ZITAH, cls.TYPE_TIER_1),
            ("Vidala", cls.AREA_ZITAH, cls.TYPE_TIER_1),
            ("Vyala", cls.AREA_ZITAH, cls.TYPE_TIER_1),
            ("Wepwawet", cls.AREA_ZITAH, cls.TYPE_TIER_1),
            # Zitah tier 2
            ("Brittlis", cls.AREA_ZITAH, cls.TYPE_TIER_2),
            ("Ionos", cls.AREA_ZITAH, cls.TYPE_TIER_2),
            ("Kamohoalii", cls.AREA_ZITAH, cls.TYPE_TIER_2),
            ("Nosoi", cls.AREA_ZITAH, cls.TYPE_TIER_2),
            ("Sensual Sandy", cls.AREA_ZITAH, cls.TYPE_TIER_2),
            ("Umdhlebi", cls.AREA_ZITAH, cls.TYPE_TIER_2),
            # Zitah tier 3
            ("Fleetstalker", cls.AREA_ZITAH, cls.TYPE_TIER_3),
            ("Shockmaw", cls.AREA_ZITAH, cls.TYPE_TIER_3),
            ("Urmahlullu", cls.AREA_ZITAH, cls.TYPE_TIER_3),
            # Zitah HELM tier 1
            ("Alphuachra, Bucca & Puca", cls.AREA_ZITAH, cls.TYPE_HELM_1),
            ("Blazewing", cls.AREA_ZITAH, cls.TYPE_HELM_1),
            ("Pazuzu", cls.AREA_ZITAH, cls.TYPE_HELM_1),
            # Zitah HELM tier 2
            ("Wrathare", cls.AREA_ZITAH, cls.TYPE_HELM_2),

            # Ru'Aun tier 1
            ("Asida", cls.AREA_RUAUN, cls.TYPE_TIER_1),
            ("Bia", cls.AREA_RUAUN, cls.TYPE_TIER_1),
            ("Emputa", cls.AREA_RUAUN, cls.TYPE_TIER_1),
            ("Khon", cls.AREA_RUAUN, cls.TYPE_TIER_1),
            ("Khun", cls.AREA_RUAUN, cls.TYPE_TIER_1),
            ("Ma", cls.AREA_RUAUN, cls.TYPE_TIER_1),
            ("Met", cls.AREA_RUAUN, cls.TYPE_TIER_1),
            ("Peirithoos", cls.AREA_RUAUN, cls.TYPE_TIER_1),
            ("Ruea", cls.AREA_RUAUN, cls.TYPE_TIER_1),
            ("Sava Savanovic", cls.AREA_RUAUN, cls.TYPE_TIER_1),
            ("Tenodera", cls.AREA_RUAUN, cls.TYPE_TIER_1),
            ("Wasserspeier", cls.AREA_RUAUN, cls.TYPE_TIER_1),
            # Ru'Aun tier 2
            ("Amymone", cls.AREA_RUAUN, cls.TYPE_TIER_2),
            ("Hanbi", cls.AREA_RUAUN, cls.TYPE_TIER_2),
            ("Kammavaca", cls.AREA_RUAUN, cls.TYPE_TIER_2),
            ("Naphula", cls.AREA_RUAUN, cls.TYPE_TIER_2),
            ("Palila", cls.AREA_RUAUN, cls.TYPE_TIER_2),
            ("Yilan", cls.AREA_RUAUN, cls.TYPE_TIER_2),
            # Ru'Aun tier 3
            ("Duke Vepar", cls.AREA_RUAUN, cls.TYPE_TIER_3),
            ("Pakecet", cls.AREA_RUAUN, cls.TYPE_TIER_3),
            ("Vir'ava", cls.AREA_RUAUN, cls.TYPE_TIER_3),
            # Ru'Aun Ark Angels
            ("Ark Angel EV", cls.AREA_RUAUN, cls.TYPE_ARK_ANGELS),
            ("Ark Angel GK", cls.AREA_RUAUN, cls.TYPE_ARK_ANGELS),
            ("Ark Angel HM", cls.AREA_RUAUN, cls.TYPE_ARK_ANGELS),
            ("Ark Angel MR", cls.AREA_RUAUN, cls.TYPE_ARK_ANGELS),
            ("Ark Angel TT", cls.AREA_RUAUN, cls.TYPE_ARK_ANGELS),
            # Ru'Aun Heavenly Beasts
            ("Byakko", cls.AREA_RUAUN, cls.TYPE_HEAVENLY_BEASTS),
            ("Genbu", cls.AREA_RUAUN, cls.TYPE_HEAVENLY_BEASTS),
            ("Kirin", cls.AREA_RUAUN, cls.TYPE_HEAVENLY_BEASTS),
            ("Seiryu", cls.AREA_RUAUN, cls.TYPE_HEAVENLY_BEASTS),
            ("Suzaku", cls.AREA_RUAUN, cls.TYPE_HEAVENLY_BEASTS),
            # Ru'Aun Nazar NM
            ("Warder of Courage", cls.AREA_RUAUN, cls.TYPE_NAZAR),

            # Riesenjima tier 1
            ("Belphegor", cls.AREA_REISENJIMA, cls.TYPE_TIER_1),
            ("Crom Dubh", cls.AREA_REISENJIMA, cls.TYPE_TIER_1),
            ("Dazzling Dolores", cls.AREA_REISENJIMA, cls.TYPE_TIER_1),
            ("Golden Kist", cls.AREA_REISENJIMA, cls.TYPE_TIER_1),
            ("Kabandha", cls.AREA_REISENJIMA, cls.TYPE_TIER_1),
            ("Mauve-wristed Gomberry", cls.AREA_REISENJIMA, cls.TYPE_TIER_1),
            ("Oryx", cls.AREA_REISENJIMA, cls.TYPE_TIER_1),
            ("Sabotender Royal", cls.AREA_REISENJIMA, cls.TYPE_TIER_1),
            ("Sang Buaya", cls.AREA_REISENJIMA, cls.TYPE_TIER_1),
            ("Selkit", cls.AREA_REISENJIMA, cls.TYPE_TIER_1),
            ("Taelmoth the Diremaw", cls.AREA_REISENJIMA, cls.TYPE_TIER_1),
            ("Zduhac", cls.AREA_REISENJIMA, cls.TYPE_TIER_1),
            # Riesenjima tier 2
            ("Bashmu", cls.AREA_REISENJIMA, cls.TYPE_TIER_2),
            ("Gajasimha", cls.AREA_REISENJIMA, cls.TYPE_TIER_2),
            ("Ironside", cls.AREA_REISENJIMA, cls.TYPE_TIER_2),
            ("Old Shuck", cls.AREA_REISENJIMA, cls.TYPE_TIER_2),
            ("Sarsaok", cls.AREA_REISENJIMA, cls.TYPE_TIER_2),
            ("Strophadia", cls.AREA_REISENJIMA, cls.TYPE_TIER_2),
            # Riesenjima tier 2
            ("Maju", cls.AREA_REISENJIMA, cls.TYPE_TIER_3),
            ("Neak", cls.AREA_REISENJIMA, cls.TYPE_TIER_3),
            ("Yakshi", cls.AREA_REISENJIMA, cls.TYPE_TIER_3),
            # Riesenjima helm 1
            ("Albumen", cls.AREA_REISENJIMA, cls.TYPE_HELM_1),
            ("Erinys", cls.AREA_REISENJIMA, cls.TYPE_HELM_1),
            ("Onychophora", cls.AREA_REISENJIMA, cls.TYPE_HELM_1),
            ("Schah", cls.AREA_REISENJIMA, cls.TYPE_HELM_1),
            ("Teles", cls.AREA_REISENJIMA, cls.TYPE_HELM_1),
            ("Vinipata", cls.AREA_REISENJIMA, cls.TYPE_HELM_1),
            ("Zerde", cls.AREA_REISENJIMA, cls.TYPE_HELM_1),
        ):
            try:
                cls.objects.get(name=x[0])
            except cls.DoesNotExist:
                new = cls(
                    name=x[0],
                    area=x[1],
                    type=x[2]
                )
                new.save()

    def __str__(self):
        return '%s (%s %s)' % (
            self.name, self.get_area_display(), self.get_type_display()
        )


class AeonicGear(models.Model):
    name = models.CharField(max_length=60)

    @classmethod
    def create_defaults(cls):
        for x in (
            "Godhands",
            "Aeneas",
            "Sequence",
            "Lionheart",
            "Tri-edge",
            "Chango",
            "Anguta",
            "Trishula",
            "Heishi Shorinken",
            "Dojikiri Yasutsuna",
            "Tishtrya",
            "Khatvanga",
            "Fail-Not",
            "Fomalhaut",
            "Marsyas",
            "Srivatsa",
        ):
            try:
                cls.objects.get(name=x)
            except cls.DoesNotExist:
                new = cls(name=x)
                new.save()

    def __str__(self):
        return self.name


class AeonicsProgress(models.Model):
    character = models.OneToOneField(
        Character,
        on_delete=models.CASCADE
    )
    number_of_beads = models.IntegerField(
        default=0
    )
    finished_aeonics = models.ManyToManyField(
        AeonicGear,
        related_name="finished_for",
        blank=True,
    )
    malformed_weapon_in_progress = models.ForeignKey(
        AeonicGear,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="in_progress_for",
    )
    killed_nms = models.ManyToManyField(
        AeonicNM,
        blank=True
    )

    def __str__(self):
        return 'Aeonics progress for %s' % (self.character.name)


class DynamisWave3Registration(models.Model):
    character = models.OneToOneField(
        Character,
        on_delete=models.CASCADE
    )

    wave3jobs = models.ManyToManyField(
        Job,
        verbose_name='Jobs ready for dynamis wave 3',
        blank=True,
    )

    BOOL_CHOICES = ((True, 'Yes'), (False, 'No'))

    backup_character = models.BooleanField(
        default=False,
        verbose_name="Backup character or mule",
        choices=BOOL_CHOICES
    )

    windurst_mask_clear = models.BooleanField(default=False)
    bastok_mask_clear = models.BooleanField(default=False)
    san_doria_mask_clear = models.BooleanField(default=False)
    jeuno_mask_clear = models.BooleanField(default=False)

    windurst_boss_clear = models.BooleanField(default=False)
    bastok_boss_clear = models.BooleanField(default=False)
    san_doria_boss_clear = models.BooleanField(default=False)
    jeuno_boss_clear = models.BooleanField(default=False)

    @property
    def jobs_shortname_list(self):
        return ",".join(x.name for x in self.wave3jobs.all())


