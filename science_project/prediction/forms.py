from django import forms


class UploadData(forms.Form):
    file = forms.FileField(
        label='Upload Dataset (CSV)',
        help_text='Harap upload dataset dengan format yang benar',
    )
