"""
Synthetic PDF Generator for Workflow Engine Tests.

Generates deterministic test PDFs with known content for reliable testing.
"""

import io
import base64
from dataclasses import dataclass
from typing import Optional
from datetime import date
from decimal import Decimal


@dataclass
class InvoiceData:
    """Data structure for invoice content."""
    invoice_number: str
    invoice_date: date
    vendor_name: str
    vendor_address: str
    customer_name: str
    customer_address: str
    line_items: list[dict]
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total: Decimal
    currency: str = "USD"
    due_date: Optional[date] = None
    payment_terms: str = "Net 30"


@dataclass
class ReceiptData:
    """Data structure for receipt content."""
    receipt_number: str
    receipt_date: date
    store_name: str
    store_address: str
    items: list[dict]
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    payment_method: str


def create_simple_invoice_pdf(data: Optional[InvoiceData] = None) -> bytes:
    """
    Create a simple single-page invoice PDF.

    Args:
        data: Invoice data to use. If None, uses default test data.

    Returns:
        PDF file content as bytes.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
    except ImportError:
        # Return a minimal valid PDF if reportlab is not installed
        return _create_minimal_pdf("Simple Invoice - Test Document")

    if data is None:
        data = _get_default_invoice_data()

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1 * inch, height - 1 * inch, "INVOICE")

    # Invoice details
    c.setFont("Helvetica", 12)
    c.drawString(1 * inch, height - 1.5 * inch, f"Invoice #: {data.invoice_number}")
    c.drawString(1 * inch, height - 1.75 * inch, f"Date: {data.invoice_date.isoformat()}")
    if data.due_date:
        c.drawString(1 * inch, height - 2 * inch, f"Due Date: {data.due_date.isoformat()}")

    # Vendor info
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, height - 2.5 * inch, "From:")
    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, height - 2.75 * inch, data.vendor_name)
    c.drawString(1 * inch, height - 3 * inch, data.vendor_address)

    # Customer info
    c.setFont("Helvetica-Bold", 12)
    c.drawString(4 * inch, height - 2.5 * inch, "To:")
    c.setFont("Helvetica", 10)
    c.drawString(4 * inch, height - 2.75 * inch, data.customer_name)
    c.drawString(4 * inch, height - 3 * inch, data.customer_address)

    # Line items header
    y = height - 3.75 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1 * inch, y, "Description")
    c.drawString(4 * inch, y, "Qty")
    c.drawString(5 * inch, y, "Unit Price")
    c.drawString(6.5 * inch, y, "Amount")

    # Line items
    c.setFont("Helvetica", 10)
    y -= 0.25 * inch
    for item in data.line_items:
        c.drawString(1 * inch, y, item["description"])
        c.drawString(4 * inch, y, str(item["quantity"]))
        c.drawString(5 * inch, y, f"${item['unit_price']:.2f}")
        c.drawString(6.5 * inch, y, f"${item['amount']:.2f}")
        y -= 0.25 * inch

    # Totals
    y -= 0.5 * inch
    c.drawString(5 * inch, y, f"Subtotal: ${data.subtotal:.2f}")
    y -= 0.25 * inch
    c.drawString(5 * inch, y, f"Tax ({data.tax_rate}%): ${data.tax_amount:.2f}")
    y -= 0.25 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(5 * inch, y, f"Total: ${data.total:.2f} {data.currency}")

    c.save()
    return buffer.getvalue()


def create_multipage_invoice_pdf(pages: int = 5) -> bytes:
    """
    Create a multi-page invoice PDF with detailed line items.

    Args:
        pages: Number of pages to generate.

    Returns:
        PDF file content as bytes.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
    except ImportError:
        return _create_minimal_pdf(f"Multi-page Invoice - {pages} pages")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    for page_num in range(1, pages + 1):
        # Header
        c.setFont("Helvetica-Bold", 18)
        c.drawString(1 * inch, height - 1 * inch, f"INVOICE - Page {page_num} of {pages}")

        # Invoice info
        c.setFont("Helvetica", 12)
        c.drawString(1 * inch, height - 1.5 * inch, f"Invoice #: INV-2024-{1000 + page_num:04d}")
        c.drawString(1 * inch, height - 1.75 * inch, f"Date: 2024-01-{page_num:02d}")

        # Line items for this page
        y = height - 2.5 * inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1 * inch, y, "Item")
        c.drawString(4 * inch, y, "Description")
        c.drawString(6.5 * inch, y, "Amount")

        c.setFont("Helvetica", 10)
        for item_num in range(1, 21):
            y -= 0.3 * inch
            if y < 1 * inch:
                break
            item_id = (page_num - 1) * 20 + item_num
            c.drawString(1 * inch, y, f"ITEM-{item_id:04d}")
            c.drawString(4 * inch, y, f"Product description for item {item_id}")
            c.drawString(6.5 * inch, y, f"${item_id * 10:.2f}")

        # Page total
        c.setFont("Helvetica-Bold", 12)
        c.drawString(5 * inch, 0.5 * inch, f"Page {page_num} Subtotal: ${page_num * 2100:.2f}")

        if page_num < pages:
            c.showPage()

    c.save()
    return buffer.getvalue()


def create_receipt_pdf(data: Optional[ReceiptData] = None) -> bytes:
    """
    Create a receipt PDF (simulating a handwritten/scanned style).

    Args:
        data: Receipt data to use. If None, uses default test data.

    Returns:
        PDF file content as bytes.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
    except ImportError:
        return _create_minimal_pdf("Receipt - Test Document")

    if data is None:
        data = _get_default_receipt_data()

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Store header
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 1 * inch, data.store_name)
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 1.3 * inch, data.store_address)

    # Receipt info
    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, height - 2 * inch, f"Receipt #: {data.receipt_number}")
    c.drawString(1 * inch, height - 2.25 * inch, f"Date: {data.receipt_date.isoformat()}")

    # Dashed line
    c.setDash(3, 3)
    c.line(1 * inch, height - 2.5 * inch, width - 1 * inch, height - 2.5 * inch)
    c.setDash()

    # Items
    y = height - 3 * inch
    for item in data.items:
        c.drawString(1 * inch, y, item["name"])
        c.drawRightString(width - 1 * inch, y, f"${item['price']:.2f}")
        y -= 0.25 * inch

    # Totals
    c.setDash(3, 3)
    c.line(1 * inch, y - 0.1 * inch, width - 1 * inch, y - 0.1 * inch)
    c.setDash()

    y -= 0.4 * inch
    c.drawString(1 * inch, y, "Subtotal:")
    c.drawRightString(width - 1 * inch, y, f"${data.subtotal:.2f}")

    y -= 0.25 * inch
    c.drawString(1 * inch, y, "Tax:")
    c.drawRightString(width - 1 * inch, y, f"${data.tax:.2f}")

    y -= 0.25 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "TOTAL:")
    c.drawRightString(width - 1 * inch, y, f"${data.total:.2f}")

    y -= 0.5 * inch
    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, y, f"Payment: {data.payment_method}")

    c.save()
    return buffer.getvalue()


def create_low_confidence_pdf() -> bytes:
    """
    Create a PDF that should result in low extraction confidence.
    Contains messy, inconsistent, or ambiguous content.

    Returns:
        PDF file content as bytes.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
    except ImportError:
        return _create_minimal_pdf("Low Confidence Test Document")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Messy header
    c.setFont("Helvetica", 8)
    c.drawString(0.5 * inch, height - 0.5 * inch, "maybe invoice? or quote?")

    # Inconsistent formatting
    c.setFont("Helvetica-Oblique", 14)
    c.drawString(1 * inch, height - 1 * inch, "INVOICE/QUOTE/ESTIMATE")

    # Mixed up information
    c.setFont("Helvetica", 9)
    c.drawString(1 * inch, height - 1.5 * inch, "Number: ABC-???-123 or 456")
    c.drawString(1 * inch, height - 1.75 * inch, "Date: Jan/Feb 2024 (approx)")

    # Ambiguous amounts
    c.drawString(1 * inch, height - 2.5 * inch, "Item A ... $100 or $1000?")
    c.drawString(1 * inch, height - 2.75 * inch, "Item B ... ~$50-75")
    c.drawString(1 * inch, height - 3 * inch, "Item C ... TBD")

    # Crossed out and corrected values
    c.setFont("Helvetica", 12)
    c.drawString(1 * inch, height - 3.75 * inch, "Total: $150 $175 $200")
    c.line(1.5 * inch, height - 3.72 * inch, 2 * inch, height - 3.72 * inch)  # Strike through
    c.line(2.1 * inch, height - 3.72 * inch, 2.5 * inch, height - 3.72 * inch)  # Strike through

    # Handwritten notes simulation
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(5 * inch, height - 4 * inch, "check this ^")
    c.drawString(5 * inch, height - 4.25 * inch, "verify w/ John")

    c.save()
    return buffer.getvalue()


def _get_default_invoice_data() -> InvoiceData:
    """Get default invoice data for testing."""
    return InvoiceData(
        invoice_number="INV-2024-0001",
        invoice_date=date(2024, 1, 15),
        vendor_name="Test Vendor Inc.",
        vendor_address="123 Vendor Street, Test City, TC 12345",
        customer_name="Test Customer LLC",
        customer_address="456 Customer Ave, Sample Town, ST 67890",
        line_items=[
            {"description": "Product A", "quantity": 2, "unit_price": Decimal("50.00"), "amount": Decimal("100.00")},
            {"description": "Service B", "quantity": 1, "unit_price": Decimal("150.00"), "amount": Decimal("150.00")},
            {"description": "Product C", "quantity": 3, "unit_price": Decimal("25.00"), "amount": Decimal("75.00")},
        ],
        subtotal=Decimal("325.00"),
        tax_rate=Decimal("10"),
        tax_amount=Decimal("32.50"),
        total=Decimal("357.50"),
        currency="USD",
        due_date=date(2024, 2, 14),
        payment_terms="Net 30"
    )


def _get_default_receipt_data() -> ReceiptData:
    """Get default receipt data for testing."""
    return ReceiptData(
        receipt_number="RCP-20240115-001",
        receipt_date=date(2024, 1, 15),
        store_name="Test Store",
        store_address="789 Store Blvd, Commerce City, CC 11111",
        items=[
            {"name": "Coffee", "price": Decimal("4.50")},
            {"name": "Sandwich", "price": Decimal("8.99")},
            {"name": "Cookie", "price": Decimal("2.50")},
        ],
        subtotal=Decimal("15.99"),
        tax=Decimal("1.28"),
        total=Decimal("17.27"),
        payment_method="Credit Card"
    )


def _create_minimal_pdf(title: str) -> bytes:
    """
    Create a minimal valid PDF without external dependencies.
    This is a fallback when reportlab is not installed.
    """
    # Minimal PDF structure
    content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 100 >>
stream
BT
/F1 24 Tf
100 700 Td
({title}) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
0000000418 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
496
%%EOF"""
    return content.encode('latin-1')


def save_test_pdf(filename: str, content: bytes, output_dir: str = "tests/fixtures/documents") -> str:
    """
    Save a generated PDF to the fixtures directory.

    Args:
        filename: Name of the file to save.
        content: PDF content as bytes.
        output_dir: Directory to save to.

    Returns:
        Full path to the saved file.
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(content)
    return filepath


def get_expected_invoice_extraction() -> dict:
    """
    Get the expected extraction result for the default invoice.
    Used for validation in tests.
    """
    return {
        "invoice_number": "INV-2024-0001",
        "invoice_date": "2024-01-15",
        "vendor": {
            "name": "Test Vendor Inc.",
            "address": "123 Vendor Street, Test City, TC 12345"
        },
        "customer": {
            "name": "Test Customer LLC",
            "address": "456 Customer Ave, Sample Town, ST 67890"
        },
        "line_items": [
            {"description": "Product A", "quantity": 2, "unit_price": 50.00, "amount": 100.00},
            {"description": "Service B", "quantity": 1, "unit_price": 150.00, "amount": 150.00},
            {"description": "Product C", "quantity": 3, "unit_price": 25.00, "amount": 75.00}
        ],
        "subtotal": 325.00,
        "tax_rate": 10,
        "tax_amount": 32.50,
        "total": 357.50,
        "currency": "USD",
        "due_date": "2024-02-14",
        "payment_terms": "Net 30"
    }


def get_expected_receipt_extraction() -> dict:
    """
    Get the expected extraction result for the default receipt.
    Used for validation in tests.
    """
    return {
        "receipt_number": "RCP-20240115-001",
        "receipt_date": "2024-01-15",
        "store": {
            "name": "Test Store",
            "address": "789 Store Blvd, Commerce City, CC 11111"
        },
        "items": [
            {"name": "Coffee", "price": 4.50},
            {"name": "Sandwich", "price": 8.99},
            {"name": "Cookie", "price": 2.50}
        ],
        "subtotal": 15.99,
        "tax": 1.28,
        "total": 17.27,
        "payment_method": "Credit Card"
    }
