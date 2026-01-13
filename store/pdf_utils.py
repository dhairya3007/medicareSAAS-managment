from io import BytesIO
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib import colors
from datetime import datetime

def generate_simple_invoice(order):
    """Generate a simple PDF invoice using reportlab"""
    buffer = BytesIO()
    
    # Create the PDF object
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center
    )
    
    # Title
    elements.append(Paragraph("MEDICARE PHARMACY", title_style))
    elements.append(Paragraph("INVOICE", title_style))
    
    # Order details
    order_info = [
        [f"Order #: {order.id}", f"Date: {order.order_date.strftime('%Y-%m-%d %H:%M')}"],
        [f"Customer: {order.user.username}", f"Total: ₹{order.final_amount}"],
    ]
    
    order_table = Table(order_info, colWidths=[3*inch, 3*inch])
    order_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(order_table)
    elements.append(Paragraph("<br/>", styles["Normal"]))
    
    # Items table
    items_data = [['Medicine', 'Quantity', 'Price', 'Total']]
    for item in order.items.all():
        items_data.append([
            item.medicine.name,
            str(item.quantity),
            f"₹{item.price}",
            f"₹{float(item.price) * item.quantity}"
        ])
    
    items_table = Table(items_data, colWidths=[3*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(items_table)
    
    # Summary
    elements.append(Paragraph("<br/>", styles["Normal"]))
    summary_data = [
        ["Subtotal:", f"₹{order.total_amount}"],
        ["Discount:", f"{order.discount_percentage}%"],
        ["Total Amount:", f"₹{order.final_amount}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[4*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
    ]))
    elements.append(summary_table)
    
    # Footer
    elements.append(Paragraph("<br/><br/>", styles["Normal"]))
    elements.append(Paragraph("Thank you for your purchase!", styles["Normal"]))
    elements.append(Paragraph("MediCare Pharmacy - Your Health, Our Priority", styles["Normal"]))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF value from buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from .models import Order

def download_invoice(request, order_id):
    """View to download PDF invoice"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Generate PDF using your existing function
    pdf = generate_simple_invoice(order)
    
    # Create HTTP response with PDF
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order_id}.pdf"'
    
    return response