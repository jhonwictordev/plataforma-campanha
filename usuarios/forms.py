from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, ReadOnlyPasswordHashField
from django.contrib.auth.password_validation import validate_password

from campanhas.models import Campanha
from usuarios.policies import papeis_gerenciaveis_por_usuario, usuario_pode_gerir_multicampanha

Usuario = get_user_model()


def aplicar_estilo_bootstrap(campo):
    if isinstance(campo.widget, forms.CheckboxInput):
        classe_padrao = "form-check-input"
    elif isinstance(campo.widget, (forms.Select, forms.SelectMultiple)):
        classe_padrao = "form-select"
    else:
        classe_padrao = "form-control"
    classe = campo.widget.attrs.get("class", "")
    campo.widget.attrs["class"] = f"{classe} {classe_padrao}".strip()


class FormularioBaseBootstrap(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            aplicar_estilo_bootstrap(campo)


class FormularioCriacaoUsuario(forms.ModelForm):
    password1 = forms.CharField(label="Senha", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmacao de senha", widget=forms.PasswordInput)

    class Meta:
        model = Usuario
        fields = ("email", "nome_completo", "campanha", "nivel_acesso")

    def __init__(self, *args, usuario_logado=None, **kwargs):
        self.usuario_logado = usuario_logado
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            aplicar_estilo_bootstrap(campo)
        aplicar_estilo_bootstrap(self.fields["password1"])
        aplicar_estilo_bootstrap(self.fields["password2"])
        self.fields["campanha"].queryset = Campanha.objects.filter(excluido_em__isnull=True).order_by("nome_campanha")
        self._configurar_restricoes_gerenciais()

    def _configurar_restricoes_gerenciais(self):
        if self.usuario_logado is None:
            return

        niveis_permitidos = papeis_gerenciaveis_por_usuario(self.usuario_logado)
        if niveis_permitidos:
            self.fields["nivel_acesso"].choices = [
                escolha for escolha in self.fields["nivel_acesso"].choices if escolha[0] in niveis_permitidos
            ]

        if usuario_pode_gerir_multicampanha(self.usuario_logado):
            return

        campanha_id = getattr(self.usuario_logado, "campanha_id", None)
        if campanha_id:
            self.fields["campanha"].queryset = self.fields["campanha"].queryset.filter(pk=campanha_id)
            self.fields["campanha"].initial = campanha_id
            self.fields["campanha"].empty_label = None
        else:
            self.fields["campanha"].queryset = self.fields["campanha"].queryset.none()

    def clean_password1(self):
        senha = self.cleaned_data["password1"]
        usuario = Usuario(
            email=self.cleaned_data.get("email", ""),
            nome_completo=self.cleaned_data.get("nome_completo", ""),
        )
        validate_password(senha, usuario)
        return senha

    def clean_password2(self):
        senha1 = self.cleaned_data.get("password1")
        senha2 = self.cleaned_data.get("password2")
        if senha1 and senha2 and senha1 != senha2:
            raise forms.ValidationError("As senhas informadas nao conferem.")
        return senha2

    def clean(self):
        dados = super().clean()
        if self.usuario_logado is None:
            return dados

        campanha = dados.get("campanha")
        nivel_acesso = dados.get("nivel_acesso")
        niveis_permitidos = papeis_gerenciaveis_por_usuario(self.usuario_logado)

        if (
            not usuario_pode_gerir_multicampanha(self.usuario_logado)
            and not getattr(self.usuario_logado, "campanha_id", None)
        ):
            raise forms.ValidationError("Seu usuario precisa estar vinculado a uma campanha para cadastrar contas.")

        if campanha and not usuario_pode_gerir_multicampanha(self.usuario_logado):
            if campanha.pk != self.usuario_logado.campanha_id:
                self.add_error("campanha", "Nao e permitido cadastrar usuarios em outra campanha.")

        if nivel_acesso and niveis_permitidos and nivel_acesso not in niveis_permitidos:
            self.add_error("nivel_acesso", "Seu perfil pode criar apenas usuarios operacionais da propria campanha.")
        return dados

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.usuario_logado and not usuario_pode_gerir_multicampanha(self.usuario_logado):
            usuario.campanha = self.usuario_logado.campanha
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


class FormularioGestaoUsuario(FormularioBaseBootstrap):
    class Meta:
        model = Usuario
        fields = (
            "email",
            "nome_completo",
            "nome_exibicao",
            "telefone",
            "foto_perfil",
            "campanha",
            "nivel_acesso",
            "is_active",
            "tema_escuro",
        )

    def __init__(self, *args, usuario_logado=None, **kwargs):
        self.usuario_logado = usuario_logado
        super().__init__(*args, **kwargs)
        self.fields["campanha"].queryset = Campanha.objects.filter(excluido_em__isnull=True).order_by("nome_campanha")
        self._configurar_restricoes_gerenciais()

    def _configurar_restricoes_gerenciais(self):
        if self.usuario_logado is None:
            return

        niveis_permitidos = papeis_gerenciaveis_por_usuario(self.usuario_logado)
        if niveis_permitidos:
            self.fields["nivel_acesso"].choices = [
                escolha for escolha in self.fields["nivel_acesso"].choices if escolha[0] in niveis_permitidos
            ]

        if usuario_pode_gerir_multicampanha(self.usuario_logado):
            return

        campanha_id = getattr(self.usuario_logado, "campanha_id", None)
        if campanha_id:
            self.fields["campanha"].queryset = self.fields["campanha"].queryset.filter(pk=campanha_id)
            self.fields["campanha"].initial = campanha_id
            self.fields["campanha"].empty_label = None
        else:
            self.fields["campanha"].queryset = self.fields["campanha"].queryset.none()

    def clean(self):
        dados = super().clean()
        if self.usuario_logado is None:
            return dados

        campanha = dados.get("campanha")
        nivel_acesso = dados.get("nivel_acesso")
        niveis_permitidos = papeis_gerenciaveis_por_usuario(self.usuario_logado)

        if (
            not usuario_pode_gerir_multicampanha(self.usuario_logado)
            and not getattr(self.usuario_logado, "campanha_id", None)
        ):
            raise forms.ValidationError("Seu usuario precisa estar vinculado a uma campanha para gerenciar contas.")

        if campanha and not usuario_pode_gerir_multicampanha(self.usuario_logado):
            if campanha.pk != self.usuario_logado.campanha_id:
                self.add_error("campanha", "Nao e permitido vincular usuarios a outra campanha.")

        if nivel_acesso and niveis_permitidos and nivel_acesso not in niveis_permitidos:
            self.add_error("nivel_acesso", "Seu perfil pode gerenciar apenas usuarios operacionais da propria campanha.")
        return dados

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.usuario_logado and not usuario_pode_gerir_multicampanha(self.usuario_logado):
            usuario.campanha = self.usuario_logado.campanha
        if commit:
            usuario.save()
        return usuario


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
