from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import ReadOnlyPasswordHashField

Usuario = get_user_model()


class FormularioBaseBootstrap(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            classe = campo.widget.attrs.get("class", "")
            campo.widget.attrs["class"] = f"{classe} form-control".strip()


class FormularioCriacaoUsuario(forms.ModelForm):
    password1 = forms.CharField(label="Senha", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmação de senha", widget=forms.PasswordInput)

    class Meta:
        model = Usuario
        fields = ("email", "nome_completo", "campanha", "nivel_acesso")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs["class"] = "form-control"

    def clean_password2(self):
        senha1 = self.cleaned_data.get("password1")
        senha2 = self.cleaned_data.get("password2")
        if senha1 and senha2 and senha1 != senha2:
            raise forms.ValidationError("As senhas informadas não conferem.")
        return senha2

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password1"])
        if commit:
            usuario.save()
        return usuario


class FormularioAlteracaoUsuario(FormularioBaseBootstrap):
    password = ReadOnlyPasswordHashField(label="Senha")

    class Meta:
        model = Usuario
        fields = (
            "email",
            "password",
            "nome_completo",
            "nome_exibicao",
            "telefone",
            "foto_perfil",
            "campanha",
            "nivel_acesso",
            "is_active",
            "is_staff",
        )


class FormularioPerfilUsuario(FormularioBaseBootstrap):
    class Meta:
        model = Usuario
        fields = (
            "nome_completo",
            "nome_exibicao",
            "email",
            "telefone",
            "foto_perfil",
            "tema_escuro",
        )
