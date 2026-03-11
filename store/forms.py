from django import forms
from .models import Medicine, Category, Supplier


class MedicineForm(forms.ModelForm):

    expiry_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

    class Meta:
        model = Medicine
        exclude = ['organization']   # 🔐 Never expose organization in form

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Paracetamol Tablets'
            }),
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., PharmaCorp Inc.'
            }),
            'power': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 500mg'
            }),
            'product_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., PC-12345'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'supplier': forms.Select(attrs={
                'class': 'form-select'
            }),
            'batch_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., BATCH-001'
            }),
            'low_stock_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'components': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Enter active ingredients and components'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        org = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)

        # 🔐 Default: show nothing
        self.fields['category'].queryset = Category.objects.none()
        self.fields['supplier'].queryset = Supplier.objects.none()

        # ✅ Show only current user's organization data
        if org:
            self.fields['category'].queryset = Category.objects.filter(
                organization=org
            )
            self.fields['supplier'].queryset = Supplier.objects.filter(
                organization=org
            )