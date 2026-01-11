from django import forms

from .models import Activity, PackingItem, Trip, TripPackingItem


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['title', 'destination', 'start_date', 'end_date', 'budget', 'is_public']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        budget = cleaned.get('budget')
        if start and end and end < start:
            raise forms.ValidationError('Дата окончания должна быть после даты начала.')
        if budget is not None and budget < 0:
            raise forms.ValidationError('Бюджет не может быть отрицательным.')
        return cleaned


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['title', 'date', 'cost', 'notes', 'tags']
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

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise forms.ValidationError('Название обязательно.')
        return name


class TripPackingItemForm(forms.ModelForm):
    class Meta:
        model = TripPackingItem
        fields = ['item', 'quantity', 'is_packed', 'note']

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        if self.owner:
            self.fields['item'].queryset = self.fields['item'].queryset.filter(owner=self.owner)

    def clean_quantity(self):
        q = self.cleaned_data.get('quantity')
        if q is None or q < 1:
            raise forms.ValidationError('Количество должно быть не меньше 1.')
        return q
