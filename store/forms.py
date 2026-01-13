from django import forms
from .models import Medicine

from django import forms
from .models import Medicine, Category, Supplier

class MedicineForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    expiry_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    class Meta:
        model = Medicine
        fields = '__all__'
        widgets = {
            'components': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Enter active ingredients and components'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Paracetamol Tablets'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., PharmaCorp Inc.'}),
            'power': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 500mg'}),
            'product_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., PC-12345'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., BATCH-001'}),
            'low_stock_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }