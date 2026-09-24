from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    no_telepon = forms.CharField(max_length=15, required=False, label="No. Telepon")
    alamat = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2", "no_telepon", "alamat"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = User.ROLE_PELANGGAN
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)