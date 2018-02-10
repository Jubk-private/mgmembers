from django import forms
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
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import TemplateView
from django.views.generic import UpdateView
import mgmembers.forms as mgforms
import mgmembers.models as mgmodels


class IndexView(TemplateView):
    template_name = 'mgmembers/index.html'

    def get_context_data(self, **kwargs):
        kwargs['characters'] = mgmodels.Character.objects.all().order_by(
            'name'
        )

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
        return reverse('character', args=[self.object.name])


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
                name=self.kwargs.get("name")
            )
        except mgmodels.Character.DoesNotExist:
            raise Http404("Character not found")

        if hasattr(self.character, 'omenbosswishlist'):
            return self.character.omenbosswishlist
        else:
            return self.model(character=self.character)

    def get_success_url(self):
        return reverse('character', args=[self.character.name])


class OmenBossesClearsView(UpdateView):
    model = mgmodels.OmenBossesClears
    template_name = 'mgmembers/omenbossesclears.html'
    fields = ('fu', 'kyou', 'kei', 'gin', 'kin')

    def get_object(self):
        try:
            self.character = mgmodels.Character.objects.get(
                name=self.kwargs.get("name")
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
                name=self.kwargs.get("name")
            )
        except mgmodels.Character.DoesNotExist:
            raise Http404("Character not found")

        if hasattr(self.character, 'warderofcouragepops'):
            return self.character.warderofcouragepops
        else:
            return self.model(character=self.character)

    def get_success_url(self):
        return reverse('character', args=[self.character.name])
