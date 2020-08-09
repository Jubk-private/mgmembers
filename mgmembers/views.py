from django import forms
from django.db.models import Q
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.forms import modelformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.shortcuts import reverse
from django.http import Http404
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic import UpdateView
from django.views.generic import View

import datetime
import json
import mgmembers.forms as mgforms
import mgmembers.models as mgmodels
import pytz
import re


class IndexView(TemplateView):
    template_name = 'mgmembers/index.html'

    def get_context_data(self, **kwargs):
        kwargs['characters'] = mgmodels.Character.objects.filter(owner__is_active=True).order_by(
            'name'
        )

        timezones = []
        for tz in pytz.common_timezones:
            offset = datetime.datetime.now(
                pytz.timezone(tz)
            ).strftime('%z')
            timezones.append(
                (tz, "(GMT " + offset[:1] + str(int(offset[1:3])) + ")")
            )
            timezones.sort(key=lambda x: x[0])

        kwargs['timezones'] = timezones
        
        kwargs['discord_link'] = settings.DISCORD_LINK

        return super().get_context_data(**kwargs)


class SignUpView(CreateView):
    model = User
    form_class = mgforms.SignUpForm
    template_name = 'mgmembers/signup.html'
    success_url = '/signup-success/'

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.is_active = False
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())


class SignUpSuccessView(TemplateView):
    template_name = 'mgmembers/signup-success.html'


class HomeView(TemplateView):
    template_name = 'mgmembers/home.html'
    user = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseRedirect("/")
        else:
            self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs['characters'] = self.user.characters.all()

        return super().get_context_data(**kwargs)


class CharacterView(DetailView):
    model = mgmodels.Character
    slug_field = "name"
    slug_url_kwarg = "name"
    template_name = 'mgmembers/character.html'
    context_object_name = 'character'

    def get_context_data(self, **kwargs):
        kwargs['can_edit'] = self.object.user_can_edit(self.request.user)

        return super().get_context_data(**kwargs)


class CharacterEditView(UpdateView):
    model = mgmodels.Character
    slug_field = "name"
    slug_url_kwarg = "name"
    template_name = 'mgmembers/character_edit.html'
    context_object_name = 'character'
    fields = ('name',)

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.user_can_edit(request.user):
            messages.error(
                request,
                "You do not have permission to edit this character"
            )
            return HttpResponseRedirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('character', args=[self.object.name])


class CharacterCreateView(CreateView):
    model = mgmodels.Character
    template_name = 'mgmembers/character_create.html'
    fields = ('name',)

    def dispatch(self, request, *args, **kwargs):
        if not self.request.user.is_authenticated:
            messages.error(
                request,
                "You do not have permission to create characters"
            )
            return HttpResponseRedirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.owner = self.request.user
        self.object.save()

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('home')


class CharacterDeleteView(DeleteView):
    model = mgmodels.Character
    slug_field = "name"
    slug_url_kwarg = "name"
    template_name = 'mgmembers/character_delete.html'
    context_object_name = 'character'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.user_can_edit(request.user):
            messages.error(
                request,
                "You do not have permission to delete this character"
            )
            return HttpResponseRedirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('home')


class JobsEditView(UpdateView):
    model = mgmodels.Character
    slug_field = "name"
    slug_url_kwarg = "name"
    template_name = 'mgmembers/jobs_edit.html'
    context_object_name = 'character'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.user_can_edit(request.user):
            messages.error(
                request,
                "You do not have permission to edit jobs for this"
            )
            return HttpResponseRedirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        unconfigured_jobs = mgmodels.Job.objects.exclude(
            name__in=[x.job.name for x in self.object.characterjobs.all()]
        )

        kwargs = {
            'queryset': self.object.characterjobs.all(),
            'initial': [{
                'character': self.object,
                'job': x.pk
            } for x in unconfigured_jobs]
        }

        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })

        return kwargs

    def get_form_class(self, *args, **kwargs):
        return modelformset_factory(
            mgmodels.CharacterJob,
            fields=('id', 'job', 'character', 'level', 'mastered',
                    'event_status', 'gear_status'),
            extra=(
                mgmodels.Job.objects.count() -
                self.object.characterjobs.count()
            )
        )

    def get_context_data(self, **kwargs):
        result = super().get_context_data(**kwargs)

        for x in result['form']:
            x['job'].name = mgmodels.Job.objects.get(pk=x['job'].value()).name

        return result

    def form_valid(self, form):
        primary_status = mgmodels.CharacterJob.GEAR_PRIMARY
        primary_gear_count = 0
        for x in form:
            if x.instance.gear_status == mgmodels.CharacterJob.GEAR_PRIMARY:
                primary_gear_count = primary_gear_count + 1
                if primary_gear_count > 2:
                    x.add_error(
                        None, "You can only have two primary gear jobs"
                    )

        if primary_gear_count > 2:
            return self.form_invalid(form)

        # Save what was created, but only if level is not none
        for x in form:
            if x.instance.pk is not None:
                if x.instance.level is None:
                    x.instance.delete()
                else:
                    x.instance.save()
            else:
                if x.instance.level is not None:
                    x.instance.save()

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('character-loot-overview', args=[self.object.name])


class CreateLoginNonceView(CreateView):
    model = mgmodels.OneTimeLoginNonce
    template_name = 'mgmembers/loginnonce_create.html'
    fields = ('target_user',)

    def dispatch(self, request, *args, **kwargs):
        if (
            not self.request.user.is_authenticated or
            not self.request.user.is_superuser
        ):
            messages.error(
                request,
                "You do not have permission to create login nonces"
            )
            return HttpResponseRedirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.fields['target_user'].queryset = User.objects.exclude(
            pk__in=[x.target_user.pk for x in self.model.objects.all()]
        )
        return form

    def get_context_data(self, **kwargs):
        kwargs['existing_nonces'] = self.model.objects.all()

        return super().get_context_data(**kwargs)

    def get_success_url(self):
        return reverse('loginnonce-create')


class LoginByNonceView(DetailView):
    model = mgmodels.OneTimeLoginNonce

    def get(self, request, *args, **kwargs):
        if "bot/" in request.META['HTTP_USER_AGENT'].lower():
            raise Http404("Bots can not log in")

        self.object = self.get_object()
        self.object.target_user.is_active = True
        self.object.target_user.save()
        login(request, self.object.target_user)
        messages.success(
            request,
            'User %s logged successfully in' % self.object.target_user
        )
        self.object.delete()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('change-password')


class ChangePasswordView(FormView):
    form_class = SetPasswordForm
    template_name = 'mgmembers/change_password.html'

    def dispatch(self, request, *args, **kwargs):
        if not self.request.user.is_authenticated:
            messages.error(request, "You must be logged in to change password")
            return HttpResponseRedirect(
                reverse('login') + '?next=' + reverse('change-password')
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user

        return kwargs

    def form_valid(self, form):
        user = form.save()
        update_session_auth_hash(self.request, user)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('home')


class OmenBossWishlistView(UpdateView):
    model = mgmodels.OmenBossWishlist
    template_name = 'mgmembers/omenbosswishlist.html'
    fields = ('first_choice', 'second_choice')

    def get_object(self):
        try:
            self.character = mgmodels.Character.objects.get(
                name=self.kwargs.get("name"),
                owner=self.request.user
            )
        except mgmodels.Character.DoesNotExist:
            raise Http404("Character not found")

        if hasattr(self.character, 'omenbosswishlist'):
            return self.character.omenbosswishlist
        else:
            return self.model(character=self.character)

    def get_success_url(self):
        return reverse('character-loot-overview', args=[self.character.name])


class OmenBossesClearsView(UpdateView):
    model = mgmodels.OmenBossesClears
    template_name = 'mgmembers/omenbossesclears.html'
    fields = ('fu', 'kyou', 'kei', 'gin', 'kin')

    def get_object(self):
        try:
            self.character = mgmodels.Character.objects.get(
                name=self.kwargs.get("name"),
                owner=self.request.user
            )
        except mgmodels.Character.DoesNotExist:
            raise Http404("Character not found")

        if hasattr(self.character, 'omenbossesclears'):
            return self.character.omenbossesclears
        else:
            return self.model(character=self.character)

    def get_success_url(self):
        return reverse('character', args=[self.character.name])


class WarderOfCouragePopsView(UpdateView):
    model = mgmodels.WarderOfCouragePops
    template_name = 'mgmembers/warderofcouragepops.html'
    fields = (
        'primal_nazar',
        'primary_nazar',
        'secondary_nazar',
        'tertiary_nazar',
        'quaternary_nazar',
        'quinary_nazar',
        'senary_nazar',
        'septenary_nazar',
        'octonary_nazar',
        'nonary_nazar',
        'denary_nazar',
    )

    def get_object(self):
        try:
            self.character = mgmodels.Character.objects.get(
                name=self.kwargs.get("name"),
                owner=self.request.user
            )
        except mgmodels.Character.DoesNotExist:
            raise Http404("Character not found")

        if hasattr(self.character, 'warderofcouragepops'):
            return self.character.warderofcouragepops
        else:
            return self.model(character=self.character)

    def get_success_url(self):
        return reverse('character', args=[self.character.name])


class GearChoicesOverview(TemplateView):
    template_name = 'mgmembers/gear_overview.html'

    def get_context_data(self, **kwargs):
        result = super().get_context_data(**kwargs)

        jobs = []

        for val, desc in mgmodels.Job.job_choices:
            if not val:
                continue

            charjobs = mgmodels.CharacterJob.objects.filter(
                job__name=val,
                character__owner__is_active=True
            )
            cj = mgmodels.CharacterJob

            jobs.append({
                'name': val,
                'primary': [
                    x.character
                    for x in charjobs.filter(gear_status=cj.GEAR_PRIMARY)
                ],
                'secondary': [
                    x.character
                    for x in charjobs.filter(gear_status=cj.GEAR_SECONDARY)
                ],
            })

        result['jobs'] = jobs

        return result

class DynamisGearView(UpdateView):
    model = mgmodels.DynamisGearChoices
    template_name = 'mgmembers/dynamisgear.html'
    fields = (
        'sandoria_primary',
        'sandoria_secondary',
        'bastok_primary',
        'bastok_secondary',
        'windurst_primary',
        'windurst_secondary',
        'jeuno_primary',
        'jeuno_secondary',
        'body_primary',
        'body_secondary',
    )

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.pk is not None and not obj.can_be_edited:
            return HttpResponseRedirect(self.get_success_url())

        return super(DynamisGearView, self).dispatch(request, *args, **kwargs)

    def get_object(self):
        try:
            self.character = mgmodels.Character.objects.get(
                name=self.kwargs.get("name"),
                owner=self.request.user
            )
        except mgmodels.Character.DoesNotExist:
            raise Http404("Character not found")

        if hasattr(self.character, 'dynamisgearchoices'):
            return self.character.dynamisgearchoices
        else:
            return self.model(character=self.character)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.last_change = timezone.now()
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('character-loot-overview', args=[self.character.name])


class OmenScalesOverview(TemplateView):
    template_name = 'mgmembers/gear_omen_scales.html'

    def get_context_data(self, **kwargs):
        result = super().get_context_data(**kwargs)

        bosses = []

        for val, name in mgmodels.OmenBossWishlist.choices:
            if val is None:
                continue
            bosses.append({
                'name': name,
                'characters': mgmodels.Character.objects.filter(
                    Q(omenbosswishlist__first_choice=val) |
                    Q(omenbosswishlist__second_choice=val)
                ).filter(
                    owner__is_active=True
                )
            })

        result['bosses'] = bosses

        return result


class DynamisGearOverview(TemplateView):
    template_name = 'mgmembers/gear_dynamis_overview.html'

    def get_context_data(self, **kwargs):
        result = super().get_context_data(**kwargs)


        sdo_jobs = []
        bastok_jobs = []
        windurst_jobs = []
        jeuno_jobs = []
        body_jobs = []

        for val, desc in mgmodels.Job.job_choices:
            if not val:
                continue

            sdo_jobs.append({
                'name': val,
                'characters': mgmodels.Character.objects.filter(
                    Q(dynamisgearchoices__sandoria_primary__name=val) |
                    Q(dynamisgearchoices__sandoria_secondary__name=val)
                ).filter(
                    owner__is_active=True
                )
            })
            bastok_jobs.append({
                'name': val,
                'characters': mgmodels.Character.objects.filter(
                    Q(dynamisgearchoices__bastok_primary__name=val) |
                    Q(dynamisgearchoices__bastok_secondary__name=val)
                ).filter(
                    owner__is_active=True
                )
            })
            windurst_jobs.append({
                'name': val,
                'characters': mgmodels.Character.objects.filter(
                    Q(dynamisgearchoices__windurst_primary__name=val) |
                    Q(dynamisgearchoices__windurst_secondary__name=val)
                ).filter(
                    owner__is_active=True
                )
            })
            jeuno_jobs.append({
                'name': val,
                'characters': mgmodels.Character.objects.filter(
                    Q(dynamisgearchoices__jeuno_primary__name=val) |
                    Q(dynamisgearchoices__jeuno_secondary__name=val)
                ).filter(
                    owner__is_active=True
                )
            })
            body_jobs.append({
                'name': val,
                'characters': mgmodels.Character.objects.filter(
                    Q(dynamisgearchoices__body_primary__name=val) |
                    Q(dynamisgearchoices__body_secondary__name=val)
                ).filter(
                    owner__is_active=True
                )
            })

        result['sdo_jobs'] = sdo_jobs
        result['bastok_jobs'] = bastok_jobs
        result['windurst_jobs'] = windurst_jobs
        result['jeuno_jobs'] = jeuno_jobs
        result['body_jobs'] = body_jobs

        return result


class LSInformationView(TemplateView):
    template_name = 'mgmembers/ls_information.html'


class RemaAugmentChoiceView(UpdateView):
    model = mgmodels.RemaAugmentChoice
    template_name = 'mgmembers/rema_augment_choice.html'
    fields = ('rema_choice',)

    def get_object(self):
        user = self.request.user
        if not user:
            raise Http404("User not found")

        if hasattr(user, 'remaaugmentchoice'):
            return user.remaaugmentchoice
        else:
            return self.model(player=user)

    def get_success_url(self):
        return reverse('home')


class RemaOverview(TemplateView):
    template_name = 'mgmembers/gear_rema_overview.html'

    def get_context_data(self, **kwargs):
        result = super().get_context_data(**kwargs)

        choices = []

        for x in mgmodels.RemaAugmentChoice.choices:
            if x[0] is None:
                continue
            qs = User.objects.filter(
                remaaugmentchoice__rema_choice=x[0]
            )
            choices.append({
                'name': x[1],
                'players': qs,
                'count': qs.count()
            })


        result['choices'] = choices

        return result

@method_decorator(csrf_exempt, name='dispatch')
class LootJsonView(View):

    general_loot = {
        "Niqmaddu Ring": ["WAR", "MNK", "DRK", "SAM", "DRG", "PUP", "RUN"],
        "Shulmanu collar": ["BST", "DRG", "SMN", "PUP"],
        "Nisroch jerkin": ["RNG", "COR"],
        "Enmerkar earring": ["BST", "DRG", "SMN", "PUP"],
        "Iskur gorget": ["THF", "RNG", "NIN", "COR"],
        "Udug jacket": ["BST", "SMN", "PUP"],
        "Ammurapi shield": ["WHM", "BLM", "RDM", "BRD", "SMN", "SCH", "GEO"],
        "Lugalbanda earring": ["BLM", "SMN", "SCH", "GEO"],
        "Shamash robe": ["WHM", "BLM", "RDM", "BLU", "SCH", "GEO"],
        "Yamarang": ["THF", "NIN", "DNC", "RUN"],
        "Dingir ring": ["THF", "RNG", "NIN", "COR"],
        "Ashera harness": ["MNK", "THF", "BRD", "NIN", "DNC", "RUN"],
        "Utu grip": ["WAR", "DRK", "SAM", "DRG", "RUN"],
        "Ilabrat ring": [
            "MNK", "WHM", "RDM", "THF", "BST", "BRD", "RNG", "SAM", "NIN",
            "BLU", "COR", "DNC", "RUN"
        ],
        "Dagon breastplate": ["WAR", "PLD", "DRK", "SAM", "DRG"],
        "Regal belt": ["SMN"],
        "Regal captain's gloves": ["WAR", "MNK", "DRK", "SAM", "PUP"],
        "Regal cuffs": ["WHM", "BLM", "RDM", "SMN", "BLU", "SCH", "GEO"],
        "Regal earring": ["WHM", "BLM", "RDM", "BRD", "BLU", "SCH", "GEO"],
        "Regal gauntlets": ["PLD", "RUN"],
        "Regal gem": ["RDM"],
        "Regal gloves": [
            "THF", "BST", "BRD", "RNG", "NIN", "DRG", "COR", "DNC"
        ],
        "Regal necklace": ["COR"],
        "Regal ring": [
            "WAR", "MNK", "THF", "PLD", "DRK", "BST", "RNG", "SAM", "NIN",
            "DRG", "COR", "PUP", "DNC", "RUN"
        ],
        "Nusku shield": ["RNG", "COR"],
        "Sherida earring": [
            "MNK", "RDM", "THF", "BST", "RNG", "DRG", "DNC", "RUN"
        ],
        "Anu torque": ["MNK", "RDM", "THF", "BST", "RNG", "DRG", "DNC", "RUN"],
        "Kishar ring": [
            "WHM", "BLM", "RDM", "PLD", "DRK", "BRD", "NIN", "SMN", "BLU",
            "COR", "SCH", "GEO", "RUN"
        ],
        "Enki strap": ["WHM", "BLM", "RDM", "BRD", "SMN", "SCH", "GEO"],
        "Erra pendant": [
            "WHM", "BLM", "RDM", "PLD", "DRK", "SMN", "BLU", "SCH", "GEO",
            "RUN"
        ],
        "Adad amulet": ["BST", "DRG", "SMN", "PUP"],
        "Knobkierrie": ["WAR", "MNK", "DRK", "SAM", "DRG", "RUN"],
        "Adapa shield": ["WAR", "DRK", "BST"],
    }

    general_items_by_job = {}

    for item,jobs in general_loot.items():
        for job in jobs:
            if job not in general_items_by_job:
                general_items_by_job[job] = set()
            general_items_by_job[job].add(item)

    scale_map = {
        mgmodels.OmenBossWishlist.KIN: "Kin's Scale",
        mgmodels.OmenBossWishlist.GIN: "Gin's Scale",
        mgmodels.OmenBossWishlist.KEI: "Kei's Scale",
        mgmodels.OmenBossWishlist.KYOU: "Kyou's Scale",
        mgmodels.OmenBossWishlist.FU: "Fu's Scale",
    }


    def get(self, request, *args, **kwargs):
        loot = {}

        for item in self.general_loot.keys():
            loot[item] = {}

        # Add empty entries for all jobs
        for job in mgmodels.Job.objects.all():
            loot["Footshard: " + job.name] = {}
            loot["Voidfoot: " + job.name] = {}
            loot["Handshard: " + job.name] = {}
            loot["Voidhand: " + job.name] = {}
            loot["Headshard: " + job.name] = {}
            loot["Voidhead: " + job.name] = {}
            loot["Legshard: " + job.name] = {}
            loot["Voidleg: " + job.name] = {}
            loot["Torsoshard: " + job.name] = {}
            loot["Voidtorso: " + job.name] = {}

        for item in self.scale_map.values():
            loot[item] = {}

        already_registered = {}
        for x in mgmodels.LootItem.objects.all():
            already_registered[x.name] = {}
            for c in x.character_set.all():
                already_registered[x.name][c.name] = True

        def add_lotter(item, name):
            if item not in loot:
                loot[item] = {}

            if not already_registered.get(item, {}).get(name, False):
                loot[item][name] = True

        qs = mgmodels.Character.objects.filter(
            owner__is_active=True
        ).prefetch_related(
            "jobs", "dynamisgearchoices", "omenbosswishlist"
        )

        for character in qs:
            name = character.name

            for job in character.primary_gear_jobs:
                for item in self.general_items_by_job[job.name]:
                    add_lotter(item, name)

            if hasattr(character, "dynamisgearchoices"):
                dgs = character.dynamisgearchoices

                for x in dgs.sandoria_jobs:
                    add_lotter("Footshard: " + x, name)
                    add_lotter("Voidfoot: " + x, name)

                for x in dgs.bastok_jobs:
                    add_lotter("Handshard: " + x, name)
                    add_lotter("Voidhand: " + x, name)

                for x in dgs.windurst_jobs:
                    add_lotter("Headshard: " + x, name)
                    add_lotter("Voidhead: " + x, name)

                for x in dgs.jeuno_jobs:
                    add_lotter("Legshard: " + x, name)
                    add_lotter("Voidleg: " + x, name)

                for x in dgs.body_jobs:
                    add_lotter("Torsoshard: " + x, name)
                    add_lotter("Voidtorso: " + x, name)


            if hasattr(character, "omenbosswishlist"):
                osc = character.omenbosswishlist
                osc_first = self.scale_map.get(osc.first_choice)
                if osc_first:
                    add_lotter(osc_first, name)

                osc_second = self.scale_map.get(osc.second_choice)
                if osc_second:
                    add_lotter(osc_second, name)

        # Mark priority lot items
        priority_items = mgmodels.ItemQueue.item_dict()
        for itemname in priority_items.keys():
            queue = priority_items[itemname]
            if itemname not in loot:
                loot[itemname] = {}
            
            loot[itemname]["_priority_queue"] = [
                x.character.name for x in queue.positions.all()
            ]

        return JsonResponse(
            loot,
            json_dumps_params={"indent": "  ", "sort_keys": True}
        )

    def post(self, request, *args, **kwargs):
        alliance_json_str = request.POST.get("alliance_json")

        if alliance_json_str:
            data = json.loads(alliance_json_str)
            if "zone" in data and "members" in data:
                reg = mgmodels.RegisteredAlliance(
                    zone=data["zone"],
                    registered_by=data.get("uploaded_by"),
                )
                reg.save()
                members = data.get("members", [])
                for x in members:
                    try:
                        char = mgmodels.Character.objects.get(name=x)
                        reg.characters.add(char)
                    except mgmodels.Character.DoesNotExist:
                        pass

        return self.get(request, *args, **kwargs)


class PartyBuilder(TemplateView):
    template_name = 'mgmembers/party_builder.html'

    def get_joblist(self, joblist):
        jobs = []
        for job in joblist:
            event_chars = job.characterjobs.filter(
                event_status=mgmodels.CharacterJob.EVENT_PRIMARY,
                character__owner__is_active=True
            )
            if(event_chars.exists()):
                jobs.append({
                    "name": job.name,
                    "characters": event_chars
                })
        return jobs

    def get_context_data(self, **kwargs):
        roles = []

        roles.append({
            "role": "Healing",
            "jobs": self.get_joblist(mgmodels.Job.healing_jobs())
        })
        roles.append({
            "role": "Tanking",
            "jobs": self.get_joblist(mgmodels.Job.tank_jobs())
        })
        roles.append({
            "role": "Support",
            "jobs": self.get_joblist(mgmodels.Job.support_jobs())
        })
        roles.append({
            "role": "Nuking",
            "jobs": self.get_joblist(mgmodels.Job.nuke_jobs())
        })
        roles.append({
            "role": "Ranged",
            "jobs": self.get_joblist(mgmodels.Job.ranged_jobs())
        })
        roles.append({
            "role": "DD",
            "jobs": self.get_joblist(mgmodels.Job.dd_jobs())
        })

        for x in roles:
            x["count"] = len(x["jobs"])

        kwargs['roles'] = roles

        return super().get_context_data(**kwargs)


class AeonicsProgressView(UpdateView):
    model = mgmodels.AeonicsProgress
    template_name = 'mgmembers/aeonicsprogressupdate.html'
    form_class = mgforms.AeonicsProgressForm

    def get_object(self):
        try:
            self.character = mgmodels.Character.objects.get(
                name=self.kwargs.get("name"),
                owner=self.request.user
            )
        except mgmodels.Character.DoesNotExist:
            raise Http404("Character not found")

        if hasattr(self.character, 'aeonicsprogress'):
            return self.character.aeonicsprogress
        else:
            return self.model(character=self.character)


    def get_context_data(self, **kwargs):
        result = super().get_context_data(**kwargs)

        last_area = None
        last_type = None
        new_area_pks = {}
        new_type_pks = {}
        for x in result["form"]["killed_nms"].field.queryset:
            if last_area != x.area:
                new_area_pks[x.pk] = x.get_area_display()
                last_area = x.area
            if last_type != x.type:
                new_type_pks[x.pk] = x.get_type_display()
                last_type = x.type

        result["new_area_pks"] = new_area_pks
        result["new_type_pks"] = new_type_pks

        return result

    def get_success_url(self):
        return reverse('character', args=[self.character.name])


class AeonicsOverview(TemplateView):
    template_name = 'mgmembers/aeonics_overview.html'

    def get_context_data(self, **kwargs):
        result = super().get_context_data(**kwargs)

        chars = []
        non_aeonic_chars = []

        for c in mgmodels.AeonicsProgress.objects.all().order_by(
            "character__name"
        ):
            working_on = None
            if c.malformed_weapon_in_progress:
                working_on = c.malformed_weapon_in_progress

                chars.append({
                    "id": c.character.id,
                    "name": c.character.name,
                    "beads": c.number_of_beads,
                    "working_on": working_on,
                    "killed_nms": set([x.id for x in c.killed_nms.all()])
                })
            else:
                non_aeonic_chars.append({
                    "name": c.character.name,
                    "beads": c.number_of_beads
                })

        result['characters'] = chars
        areas = []
        current_area = { "id": -1 }
        current_type = { "id": -1 }
        for x in mgmodels.AeonicNM.objects.all().order_by(
            "area", "type", "pk"
        ):
            if current_area["id"] != x.area:
                current_area = {
                    "id": x.area,
                    "name": x.get_area_display(),
                    "types": [],
                    "characters": []
                }
                areas.append(current_area)

            if current_type["id"] != x.type:
                current_type = {
                    "id": x.type,
                    "name": x.get_type_display(),
                    "nms": [],
                }
                current_area["types"].append(current_type)

            current_type["nms"].append(x)

        for area in areas:
            partial_completion_characters = set()

            for type in area["types"]:
                for nm in type["nms"]:
                    for char in chars:
                        if not nm.id in char["killed_nms"]:
                            partial_completion_characters.add(char["id"])
            next_area_chars = []

            # Filter current characters: Any with a partial completion for this
            # area are stored on the area, the rest passes on to the next area.
            for char in chars:
                if char["id"] in partial_completion_characters:
                    area["characters"].append(char)
                else:
                    next_area_chars.append(char)

            area["number_of_characters"] = len(area["characters"])

            chars = next_area_chars

        result["characters_not_working_on_aeonics"] = non_aeonic_chars
        result["areas"] = areas
        result["fully_completed_characters"] = chars

        return result

class DynamisWave3UpdateView(UpdateView):
    model = mgmodels.DynamisWave3Registration
    template_name = 'mgmembers/dynawave3update.html'
    form_class = mgforms.DynamisWave3UpdateForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        form.fields['wave3jobs'].queryset = self.character.primary_event_jobs
        return form

    def get_object(self):
        try:
            self.character = mgmodels.Character.objects.get(
                name=self.kwargs.get("name"),
                owner=self.request.user
            )
        except mgmodels.Character.DoesNotExist:
            raise Http404("Character not found")

        if hasattr(self.character, 'dynamiswave3registration'):
            return self.character.dynamiswave3registration
        else:
            return self.model(character=self.character)

    def get_success_url(self):
        return reverse('character', args=[self.character.name])


class DynamisWave3Overview(TemplateView):
    template_name = "mgmembers/dynawave3overview.html"

    def get_context_data(self, **kwargs):
        result = super().get_context_data(**kwargs)

        result['characters'] = mgmodels.Character.objects.filter(
            owner__is_active=True
        ).order_by("name")

        plan_pk = self.request.GET.get("plan_id", -1)
        plan = None
        try:
            plan = mgmodels.DynamisWave3Plan.objects.get(pk=plan_pk)
        except mgmodels.DynamisWave3Plan.DoesNotExist:
            pass
        if not plan:
            plan = mgmodels.DynamisWave3Plan.objects.filter(
                date__gte=timezone.now(),
            ).first() or mgmodels.DynamisWave3Plan.objects.order_by(
                "-date"
            ).first()

        if plan:
            result["plan"] = plan
            parties = []
            for party_nr in range(1, 4):
                party = {
                    "nr": party_nr,
                    "slots": []
                }
                for slot_nr in range(1, 7):
                    party["slots"].append({
                        "role": plan.role_display_for_slot(party_nr, slot_nr),
                        "jobs": plan.jobs_for_slot(party_nr, slot_nr),
                        "character": plan.character_for_slot(party_nr, slot_nr),
                        "character_display": plan.character_for_slot_display(party_nr, slot_nr),
                    })
                parties.append(party)
            result["plan_parties"] = parties

        result["plans"] = mgmodels.DynamisWave3Plan.objects.order_by("-date")

        return result


class DynamisPlanUpdateView(UpdateView):
    model = mgmodels.DynamisWave3Plan
    template_name = 'mgmembers/dynaplanupdate.html'
    form_class = mgforms.DynamisPlanUpdateForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user or not request.user.is_superuser:
            return HttpResponseRedirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        pk = self.kwargs.get("pk")
        if(pk):
            return self.model.objects.get(pk=pk)
        else:
            return self.model()

    def get_context_data(self, **kwargs):
        result = super().get_context_data(**kwargs)

        result["jobs_by_role_json"] = json.dumps(self.model.jobs_by_role)
        result["jobs_by_character"] = {}
        result["backup_characters"] = {}

        for c in mgmodels.Character.objects.filter(
            dynamiswave3registration__isnull=False
        ):
            if c.dynamiswave3registration.backup_character:
                result["backup_characters"][c.id] = True

            jobs = {}
            for x in c.dynamiswave3registration.wave3jobs.all():
                jobs[x.name] = True
            result["jobs_by_character"][c.id] = jobs

        result["jobs_by_character_json"] = json.dumps(
            result["jobs_by_character"]
        )
        result["backup_characters_json"] = json.dumps(
            result["backup_characters"]
        )

        return result

    def get_success_url(self):

        return reverse('dynamis-wave3-overview') + "?plan_id=%s" % (self.object.pk)


class RegisteredDropsView(UpdateView):
    model = mgmodels.Character
    template_name = 'mgmembers/registered_drops.html'
    fields = ("registered_drops",)

    def get_object(self):
        try:
            self.character = mgmodels.Character.objects.get(
                name=self.kwargs.get("name"),
                owner=self.request.user
            )
        except mgmodels.Character.DoesNotExist:
            raise Http404("Character not found")

        return self.character

    def get_context_data(self, **kwargs):
        result = super().get_context_data(**kwargs)

        selected = set()
        for x in result["form"].initial["registered_drops"]:
            selected.add(x.id)

        loot_items = []
        current_category = None
        current_2nd_category = None
        for x in mgmodels.LootItem.objects.all():
            if not current_category or x.category != current_category["id"]:
                current_category = {
                    "id": x.category,
                    "name": x.get_category_display(),
                    "subcategories": [],
                }
                loot_items.append(current_category)
            if (not current_2nd_category or 
                current_2nd_category["name"] != x.second_category):
                current_2nd_category = {
                    "name": x.second_category,
                    "items": []
                }
                current_category["subcategories"].append(current_2nd_category)
            if x.id in selected:
                x.selected = True
            else:
                x.selected = False
            current_2nd_category["items"].append(x)

        result["loot_items"] = loot_items
        result["selected"] = {}

        return result


    def get_success_url(self):
        return reverse('character-loot-overview', args=[self.character.name])

class CharacterLootOverviewView(DetailView):
    template_name = 'mgmembers/character_loot_overview.html'

    def get_object(self):
        try:
            self.character = mgmodels.Character.objects.get(
                name=self.kwargs.get("name")
            )
        except mgmodels.Character.DoesNotExist:
            raise Http404("Character not found")

        return self.character

    def get_context_data(self, **kwargs):
        result = super().get_context_data(**kwargs)

        character = self.character

        items_from_jobs = []

        for job in character.primary_gear_jobs:
            for item in LootJsonView.general_items_by_job[job.name]:
                items_from_jobs.append({
                    "item": item,
                    "from": "primary gear job: " + job.name
                })

        items_from_dynamis_choices = []

        if hasattr(character, "dynamisgearchoices"):
            dgs = character.dynamisgearchoices

            for x in dgs.sandoria_jobs:
                items_from_dynamis_choices.append(
                    {"item": "Footshard: " + x,
                     "from": "Dynamis San d'Oria settings"}
                )
                items_from_dynamis_choices.append(
                    {"item": "Voidfoot: " + x,
                     "from": "Dynamis San d'Oria settings"}
                )

            for x in dgs.bastok_jobs:
                items_from_dynamis_choices.append(
                    {"item": "Handshard: " + x,
                     "from": "Dynamis Bastok settings"}
                )
                items_from_dynamis_choices.append(
                    {"item": "Voidhand: " + x,
                     "from": "Dynamis Bastok settings"}
                )

            for x in dgs.windurst_jobs:
                items_from_dynamis_choices.append(
                    {"item": "Headshard: " + x,
                     "from": "Dynamis Windurst settings"}
                )
                items_from_dynamis_choices.append(
                    {"item": "Voidhead: " + x,
                     "from": "Dynamis Windurst settings"}
                )

            for x in dgs.jeuno_jobs:
                items_from_dynamis_choices.append(
                    {"item": "Legshard: " + x,
                     "from": "Dynamis Jeuno settings"}
                )
                items_from_dynamis_choices.append(
                    {"item": "Voidleg: " + x,
                     "from": "Dynamis Jeuno settings"}
                )

            for x in dgs.body_jobs:
                items_from_dynamis_choices.append(
                    {"item": "Torsoshard: " + x,
                     "from": "Dynamis body settings (all zones)"}
                )
                items_from_dynamis_choices.append(
                    {"item": "Voidtorso: " + x,
                     "from": "Dynamis body settings (all zones)"}
                )

        items_from_omen_choices = []

        if hasattr(character, "omenbosswishlist"):
            osc = character.omenbosswishlist
            osc_first = LootJsonView.scale_map.get(osc.first_choice)
            if osc_first:
                items_from_omen_choices.append({
                    "item": osc_first,
                    "from": "Omen scale choices (first choice)"
                })

            osc_second = LootJsonView.scale_map.get(osc.second_choice)
            if osc_second:
                items_from_omen_choices.append({
                    "item": osc_second,
                    "from": "Omen scale choices (second choice)"
                })

        filtered_items = set()
        registered_drops = []

        if hasattr(character, "registered_drops"):
            for x in character.registered_drops.all():
                filtered_items.add(x.name)
                registered_drops.append(x)

        # Figure out which queued items are relevant for this character
        all_queued_items = mgmodels.ItemQueue.item_dict()
        queued_items = []
        for collection in (
            items_from_jobs,
            items_from_dynamis_choices,
            items_from_omen_choices
        ): 
            for x in collection:
                if x["item"] in all_queued_items:
                    queue = all_queued_items[x["item"]]
                    queued_items.append({
                        "queue": queue,
                        # Since we got it from an existing loot list this
                        # character will be able to do a non-priority lot
                        # on the item.
                        "without_priority": True,
                        "with_priority": queue.character_has_priority(
                            character.name
                        )
                    })
                    x["queued"] = True
                    # filtered_items.add(x["item"])
                    del all_queued_items[x["item"]]
        for queue in all_queued_items.values():
            if queue.character_has_priority(character.name):
                queued_items.append({
                    "queue": queue,
                    "without_priority": False,
                    "with_priority": True
                })
        queued_items.sort(key=lambda i: i["queue"].item.name)

        result["character"] = character

        result["from_jobs"] = [
            x for x in items_from_jobs if x["item"] not in filtered_items
        ]
        result["from_jobs"].sort(key=lambda i: i['item'])

        result["from_dynamis"] = [
            x for x in items_from_dynamis_choices if x["item"] not in filtered_items
        ]

        result["omen_scales"] = [
            x for x in items_from_omen_choices if x["item"] not in filtered_items
        ]

        result["queued_items"] = queued_items

        result["registered_drops"] = registered_drops
        result["registered_drops"].sort(key=lambda i: i.name)


        return result


class AdminOnlyMixin(object):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(
                request,
                "You do not have permission to access this page"
            )
            return HttpResponseRedirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)


class ItemQueueList(ListView):
    template_name = 'mgmembers/itemqueues/list.html'
    model = mgmodels.ItemQueue

    def get_context_object_name(self, object_list):
        return "itemqueues"

    def get_success_url(self):
        return reverse('home')

class ItemQueueEdit(AdminOnlyMixin, UpdateView):
    template_name = 'mgmembers/itemqueues/edit.html'
    model = mgmodels.ItemQueue
    fields = ()

    def get_context_data(self, **kwargs):
        result = super().get_context_data(**kwargs)

        result["characters"] = mgmodels.Character.objects.filter(
            owner__is_active=True
        ).order_by('name')

        return result

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        self.object = form.save()

        # Make a map of existing elements
        existing_elements = {}
        for x in self.object.positions.all():
            existing_elements[x.character.id] = x

        selected_characters = self.request.POST.getlist("characterposition", [])

        # Loop over incoming character ids, update positions
        # for ones we already know about and add new ones.
        # Also remove recurring characters from the existing_elements
        # dictionary
        new_position = 0
        for x in selected_characters:
            new_position = new_position + 1

            if x in existing_elements:
                existing_elements[x].position = new_position
                existing_elements[x].save()
                del existing_elements[x]
            else:
                new_item = mgmodels.ItemQueuePosition(
                    character=mgmodels.Character.objects.get(pk=x),
                    position=new_position,
                    queue=self.object
                )
                new_item.save()
            
        
        # Remaining elements in existing_elements should be deleted
        for x in existing_elements.values():
            x.delete()

        return super().form_valid(form)


    def get_success_url(self):
        return reverse('item-queue-list')

