from django import forms


class FormularioBootstrapMixin(forms.ModelForm):
    classes_personalizadas = {
        forms.CheckboxInput: "form-check-input",
        forms.SelectMultiple: "form-select",
        forms.Select: "form-select",
        forms.ClearableFileInput: "form-control",
        forms.FileInput: "form-control",
        forms.DateInput: "form-control",
        forms.DateTimeInput: "form-control",
        forms.TimeInput: "form-control",
        forms.EmailInput: "form-control",
        forms.NumberInput: "form-control",
        forms.Textarea: "form-control",
        forms.TextInput: "form-control",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            widget = campo.widget
            classe = self._obter_classe_widget(widget)
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {classe}".strip()
            if isinstance(widget, forms.CheckboxInput):
                continue
            widget.attrs.setdefault("placeholder", campo.label)
            if isinstance(widget, forms.DateInput):
                widget.attrs.setdefault("type", "date")
            if isinstance(widget, forms.DateTimeInput):
                widget.attrs.setdefault("type", "datetime-local")

    def _obter_classe_widget(self, widget) -> str:
        for tipo, classe in self.classes_personalizadas.items():
            if isinstance(widget, tipo):
                return classe
        return "form-control"


def normalizar_tags(valor: str | list[str] | None) -> list[str]:
    if isinstance(valor, list):
        return [item.strip() for item in valor if str(item).strip()]
    if not valor:
        return []
    return [item.strip() for item in str(valor).split(",") if item.strip()]
