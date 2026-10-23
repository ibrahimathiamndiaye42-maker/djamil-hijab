import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _m(n, cur):
    return f"{int(n):,}".replace(",", " ") + f" {cur}"


def build_invoice_pdf(inv, settings):
    sale, cur = inv.sale, settings.get("currency", "FCFA")
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    plum = colors.HexColor("#6b2d5c")
    y = H - 22 * mm
    c.setFillColor(plum); c.setFont("Helvetica-Bold", 22)
    c.drawString(20 * mm, y, settings.get("company_name", "DJAMIL HIJAB"))
    c.setFillColor(colors.black); c.setFont("Helvetica", 9)
    y -= 6 * mm
    c.drawString(20 * mm, y, "Tél : " + " / ".join(settings.get("phones", [])))
    if settings.get("address"):
        y -= 5 * mm; c.drawString(20 * mm, y, settings["address"])
    c.setFont("Helvetica-Bold", 16); c.setFillColor(plum)
    c.drawRightString(W - 20 * mm, H - 22 * mm, "FACTURE")
    c.setFont("Helvetica", 10); c.setFillColor(colors.black)
    c.drawRightString(W - 20 * mm, H - 28 * mm, f"N° {inv.number}")
    c.drawRightString(W - 20 * mm, H - 33 * mm, "Date : " + inv.issued_at.strftime("%d/%m/%Y %H:%M"))
    y -= 14 * mm
    c.setFont("Helvetica-Bold", 10); c.drawString(20 * mm, y, "Client :")
    c.setFont("Helvetica", 10)
    cust = sale.customer
    c.drawString(40 * mm, y, (cust.name + (f" — {cust.phone}" if cust.phone else "")) if cust else "Client de passage")
    y -= 5 * mm
    c.drawString(20 * mm, y, f"Vendu par : {sale.user.full_name}")
    y -= 10 * mm
    c.setFillColor(plum); c.rect(20 * mm, y - 2 * mm, W - 40 * mm, 7 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 9)
    c.drawString(22 * mm, y, "Désignation"); c.drawRightString(115 * mm, y, "Qté")
    c.drawRightString(150 * mm, y, "Prix unit."); c.drawRightString(W - 22 * mm, y, "Total")
    c.setFillColor(colors.black); c.setFont("Helvetica", 9)
    y -= 8 * mm
    for it in sale.items:
        if y < 50 * mm:
            c.showPage(); y = H - 25 * mm; c.setFont("Helvetica", 9)
        c.drawString(22 * mm, y, it.product_name[:60]); c.drawRightString(115 * mm, y, str(it.qty))
        c.drawRightString(150 * mm, y, _m(it.unit_price, cur)); c.drawRightString(W - 22 * mm, y, _m(it.line_total, cur))
        y -= 6 * mm
    c.line(20 * mm, y + 3 * mm, W - 20 * mm, y + 3 * mm)
    y -= 4 * mm
    rows = [("Sous-total", sale.subtotal), ("Remise", -sale.discount), ("TOTAL", sale.total),
            ("Payé", sale.paid), ("Reste à payer", sale.total - sale.paid)]
    for label, val in rows:
        c.setFont("Helvetica-Bold" if label in ("TOTAL", "Reste à payer") else "Helvetica", 10)
        c.drawRightString(150 * mm, y, label); c.drawRightString(W - 22 * mm, y, _m(val, cur)); y -= 6 * mm
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, y, "Paiement : " + (", ".join(f"{p.method} {_m(p.amount, cur)}" for p in sale.payments) or "—"))
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(W / 2, 18 * mm, settings.get("invoice_footer", ""))
    if inv.status == "ANNULEE":
        c.saveState(); c.setFillColor(colors.Color(0.8, 0, 0, alpha=0.25)); c.setFont("Helvetica-Bold", 90)
        c.translate(W / 2, H / 2); c.rotate(35); c.drawCentredString(0, 0, "ANNULÉE"); c.restoreState()
    c.save()
    return buf.getvalue()
