from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import models
from django.forms import widgets
from mgmembers import models as mg_models
from snowpenguin.django.recaptcha2.fields import ReCaptchaField
from snowpenguin.django.recaptcha2.widgets import ReCaptchaWidget


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            'username',
            'first_name',
            'email',
            'password1',
            'password2',
            'recaptcha2',
        )

    first_name = forms.CharField(
        max_length=30,
        required=False,
        help_text='Optional.',
        label="Nickname"
    )
    email = forms.EmailField(
        max_length=254, required=False,
        help_text='Optional'
    )

    recaptcha2 = ReCaptchaField(
        label='Spam check',
        widget=ReCaptchaWidget(),
    )

class AeonicsProgressForm(models.ModelForm):
    class Meta:
        model = mg_models.AeonicsProgress
        fields = (
            'number_of_beads',
            'finished_aeonics',
            'malformed_weapon_in_progress',
            'killed_nms',
        )

    def __init__(self, *args, **kwargs):
        super(AeonicsProgressForm, self).__init__(*args, **kwargs)
        
        for x in (
            ('finished_aeonics', mg_models.AeonicGear.objects.all()),
            ('killed_nms', mg_models.AeonicNM.objects.all()),
        ):
            self.fields[x[0]].widget = widgets.CheckboxSelectMultiple()
            self.fields[x[0]].queryset = x[1]

class DynamisWave3UpdateForm(models.ModelForm):

    class Meta:
        exclude = ('character',)
        model = mg_models.DynamisWave3Registration
        widgets = {
            'wave3jobs': forms.CheckboxSelectMultiple
        }

class DynamisPlanUpdateForm(models.ModelForm):

    class Meta:
        exclude = []
        model = mg_models.DynamisWave3Plan
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'})
        }

    tank_jobs = ("RUN", "PLD")
    support_jobs = ()

    filter_map = {

    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        dyna_char_qs = mg_models.Character.objects.filter(
            dynamiswave3registration__isnull=False
        )

        for x in self.fields:
            if (x.startswith("party")
                and not (x.endswith("role") or x.endswith("other"))):
                self.fields[x].queryset = dyna_char_qs
