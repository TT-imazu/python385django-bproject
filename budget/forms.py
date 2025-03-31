from django import forms

class BudgetGenerationForm(forms.Form):
    year_month = forms.CharField(
        label="年月 (YYYYMM)", 
        max_length=6, 
        min_length=6, 
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "202503"})
    )


class CSVUploadForm(forms.Form):
    file = forms.FileField()