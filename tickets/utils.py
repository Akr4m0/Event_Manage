# tickets/utils.py
from django.template.loader import get_template
from django.conf import settings
import qrcode
from io import BytesIO
import uuid
from datetime import datetime
import base64
import importlib.util

def generate_qr_code(data):
    """Generate a QR code from the given data"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    return img

def is_weasyprint_available():
    """Check if WeasyPrint is available"""
    return importlib.util.find_spec("weasyprint") is not None

def generate_ticket_pdf(ticket):
    """Generate a PDF ticket"""
    # Generate QR code as base64 data URL
    qr_img = generate_qr_code(str(ticket.ticket_code))
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer)
    qr_buffer.seek(0)
    qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode('utf-8')
    
    # Prepare context for the template
    context = {
        'ticket': ticket,
        'event': ticket.ticket_type.event,
        'qr_code': f"data:image/png;base64,{qr_base64}",
        'generated_at': datetime.now(),
    }
    
    # Check if WeasyPrint is available
    if is_weasyprint_available():
        # Import WeasyPrint only if it's available
        from weasyprint import HTML, CSS
        
        # Render the HTML template
        template = get_template('tickets/pdf/ticket_template.html')
        html_string = template.render(context)
        
        # Generate PDF
        pdf_file = BytesIO()
        try:
            HTML(string=html_string).write_pdf(
                pdf_file,
                stylesheets=[CSS(string='@page { size: A4; margin: 1cm }')]
            )
            
            pdf_file.seek(0)
            return pdf_file
        except Exception as e:
            # If PDF generation fails, return text message
            buffer = BytesIO()
            error_message = f"PDF generation failed: {str(e)}\n\n"
            buffer.write(error_message.encode('utf-8'))
            buffer.seek(0)
            return buffer
    else:
        # Return a mock PDF with an error message
        buffer = BytesIO()
        ticket_info = (
            f"PDF generation requires WeasyPrint. Please install it with: pip install weasyprint\n\n"
            f"Ticket Information:\n"
            f"Event: {ticket.ticket_type.event.title}\n"
            f"Ticket Type: {ticket.ticket_type.name}\n"
            f"Ticket Code: {ticket.ticket_code}\n"
            f"Holder: {ticket.user.username}\n"
            f"Date: {ticket.ticket_type.event.start_date.strftime('%Y-%m-%d %H:%M')}\n"
        )
        buffer.write(ticket_info.encode('utf-8'))
        buffer.seek(0)
        return buffer

def validate_ticket_purchase(ticket_type, quantity):
    """Validate if tickets can be purchased"""
    if ticket_type.quantity_available == 0:
        # Unlimited tickets
        return True, "Tickets available"
    
    # Check if enough tickets are available
    sold_tickets = ticket_type.tickets.count()
    remaining = ticket_type.quantity_available - sold_tickets
    
    if quantity > remaining:
        return False, f"Only {remaining} tickets available"
    
    return True, "Tickets available"

def create_ticket(ticket_type, user):
    """Create a new ticket instance"""
    ticket = ticket_type.tickets.create(
        user=user,
        status='pending',
        ticket_code=uuid.uuid4()
    )
    return ticket