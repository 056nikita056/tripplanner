from django import forms

from .models import Activity, PackingItem, Trip, TripPackingItem


def _apply_bootstrap(form: forms.Form) -> None:
    for field in form.fields.values():
        widget = field.widget
        cls = widget.attrs.get('class', '')
        if isinstance(widget, forms.CheckboxInput):
            bootstrap = 'form-check-input'
        elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
            bootstrap = 'form-select'
        else:
            bootstrap = 'form-control'
        widget.attrs['class'] = (cls + ' ' + bootstrap).strip()


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['title', 'destination', 'start_date', 'end_date', 'budget', 'is_public']
        labels = {
            'title': 'Название поездки',
            'destination': 'Направление',
            'start_date': 'Дата начала',
            'end_date': 'Дата окончания',
            'budget': 'Бюджет',
            'is_public': 'Публичная поездка',
        }
        help_texts = {
            'is_public': 'Если выключить, поездку увидите только вы.',
        }
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap(self)

        dest_qs = self.fields['destination'].queryset
        if not dest_qs.exists():
            self.fields['destination'].required = False
            self.fields['destination'].disabled = True
            self.fields['destination'].help_text = (
                'Направлений пока нет. Добавьте направление в админке, '
                'затем создайте поездку.'
            )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        budget = cleaned.get('budget')
        if self.fields['destination'].disabled:
            raise forms.ValidationError(
                'Нельзя создать поездку: сначала добавьте хотя бы одно направление.'
            )
        if start and end and end < start:
            raise forms.ValidationError('Дата окончания должна быть после даты начала.')
        if budget is not None and budget < 0:
            raise forms.ValidationError('Бюджет не может быть отрицательным.')
        return cleaned


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['title', 'date', 'cost', 'notes', 'tags']
        labels = {
            'title': 'Название активности',
            'date': 'Дата',
            'cost': 'Стоимость',
            'notes': 'Заметки',
            'tags': 'Теги',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.trip = kwargs.pop('trip', None)
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        if self.owner:
            self.fields['tags'].queryset = self.fields['tags'].queryset.filter(owner=self.owner)
        _apply_bootstrap(self)

    def clean(self):
        cleaned = super().clean()
        date = cleaned.get('date')
        cost = cleaned.get('cost')
        if cost is not None and cost < 0:
            raise forms.ValidationError('Стоимость не может быть отрицательной.')
        if self.trip and date:
            if date < self.trip.start_date or date > self.trip.end_date:
                raise forms.ValidationError('Дата активности должна попадать в диапазон поездки.')
        return cleaned


class PackingItemForm(forms.ModelForm):
    class Meta:
        model = PackingItem
        fields = ['name', 'category']
        labels = {
            'name': 'Название',
            'category': 'Категория',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap(self)

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise forms.ValidationError('Название обязательно.')
        return name


class TripPackingItemForm(forms.ModelForm):
    class Meta:
        model = TripPackingItem
        fields = ['item', 'quantity', 'is_packed', 'note']
        labels = {
            'item': 'Вещь',
            'quantity': 'Количество',
            'is_packed': 'Упаковано',
            'note': 'Комментарий',
        }

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        if self.owner:
            self.fields['item'].queryset = self.fields['item'].queryset.filter(owner=self.owner)
        _apply_bootstrap(self)

    def clean_quantity(self):
        q = self.cleaned_data.get('quantity')
        if q is None or q < 1:
            raise forms.ValidationError('Количество должно быть не меньше 1.')
        return q
