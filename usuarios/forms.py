from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
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


class FormularioAutenticacaoUsuario(AuthenticationForm):
    username = forms.EmailField(label="E-mail")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "username",
                "placeholder": "voce@exemplo.com",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "current-password",
                "placeholder": "Sua senha",
            }
        )


class FormularioTokenDoisFatores(forms.Form):
    token = forms.CharField(
        label="Codigo de verificacao",
        max_length=16,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "placeholder": "000000 ou codigo de recuperacao",
            }
        ),
    )


class FormularioConfirmacaoSenha(forms.Form):
    senha_atual = forms.CharField(
        label="Senha atual",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "current-password",
                "placeholder": "Confirme sua senha",
            }
        ),
    )

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean_senha_atual(self):
        senha = self.cleaned_data["senha_atual"]
        if self.usuario is None or not self.usuario.check_password(senha):
            raise forms.ValidationError("A senha informada nao confere.")
        return senha
