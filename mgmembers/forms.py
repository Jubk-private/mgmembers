from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            'username',
            'first_name',
            'email',
            'password1',
            'password2',
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
