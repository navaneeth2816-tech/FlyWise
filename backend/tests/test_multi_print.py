import subprocess
import os
import re
import sys

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
HTML_PATH = os.path.abspath(r"backend\tests\test_multi_passenger_ticket.html")
PDF_PATH = os.path.abspath(r"backend\tests\printed_multi_ticket.pdf")
css_path = os.path.abspath(r"frontend\css\style.css").replace('\\', '/')

html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>FlyWise Multi-Passenger Print Test</title>
  <link rel="stylesheet" href="file:///{css_path}">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    #ticket-modal {{ display: flex; }}
  </style>
</head>
<body>
  <nav class="navbar">Nav</nav>
  <main class="container"><div style="height: 1500px;">Long background</div></main>
  <footer>Footer</footer>

  <div id="ticket-modal" class="modal-overlay">
    <div class="modal-content" style="max-width: 840px;">
      <div id="ticket-modal-body">
        <div id="flywise-digital-ticket" class="airline-ticket-wrapper">
          <div class="ticket-header-row">
            <div class="ticket-logo-block">
              <div class="ticket-brand-title">
                <i class="fa-solid fa-plane-up"></i>
                <span>FlyWise</span>
              </div>
              <div class="ticket-doc-type">Electronic Ticket & Travel Itinerary Receipt</div>
            </div>
            <div class="ticket-pnr-block">
              <div class="ticket-pnr-tag">BOOKING REFERENCE (PNR)</div>
              <div class="ticket-pnr-code">FW-BOM99A</div>
              <div class="ticket-meta-tags">
                <span class="ticket-status-pill">CONFIRMED</span>
                <span>20 Oct 2026, 14:35 IST</span>
              </div>
            </div>
          </div>

          <div class="ticket-simulated-banner">
            <span class="ticket-simulated-badge">SIMULATED / TEST PAYMENT — SUCCESSFUL</span>
            <span>Ref: <code>SIM-PAY-CARD-BOM99A</code></span>
          </div>

          <div class="ticket-flight-card">
            <div class="ticket-flight-info-row">
              <div><span class="ticket-airline-name">IndiGo</span> <span class="ticket-flight-number">6E-201</span></div>
              <div>Class: <strong>ECONOMY</strong> • Duration: <strong>2h 15m</strong></div>
            </div>
            <div class="ticket-route-grid">
              <div class="ticket-route-node left">
                <div class="ticket-iata">DEL</div>
                <div class="ticket-city">Delhi</div>
                <div class="ticket-airport">Indira Gandhi International Airport</div>
                <div class="ticket-datetime">06:00</div>
                <div class="ticket-subdate">Sun, 25 Oct 2026</div>
              </div>
              <div class="ticket-route-center">
                <span class="ticket-flight-mode">NON-STOP</span>
                <div class="ticket-flight-line"><span class="dot"></span><span class="line"></span><i class="fa-solid fa-plane plane-icon"></i><span class="line"></span><span class="dot"></span></div>
                <span class="ticket-duration-label">2h 15m</span>
              </div>
              <div class="ticket-route-node right">
                <div class="ticket-iata">BOM</div>
                <div class="ticket-city">Mumbai</div>
                <div class="ticket-airport">Chhatrapati Shivaji Maharaj Int'l Airport</div>
                <div class="ticket-datetime">08:15</div>
                <div class="ticket-subdate">Sun, 25 Oct 2026</div>
              </div>
            </div>
          </div>

          <div class="ticket-section-title">PASSENGER & SEAT INFORMATION</div>
          <table class="ticket-passengers-table">
            <thead>
              <tr><th>PASSENGER NAME</th><th>TYPE</th><th>SEAT</th><th>E-TICKET NUMBER</th><th>SERVICES & ADD-ONS</th></tr>
            </thead>
            <tbody>
              <tr><td><strong>Navaneeth Naidu</strong></td><td>Adult</td><td><span class="ticket-seat-pill">2A (Window)</span></td><td><code>TK-6E-9021481</code></td><td>Hot Gourmet Meal • Travel Insurance</td></tr>
              <tr><td><strong>Kavya Naidu</strong></td><td>Adult</td><td><span class="ticket-seat-pill">2B (Middle)</span></td><td><code>TK-6E-9021482</code></td><td>Standard Baggage (15kg Check-in, 7kg Cabin)</td></tr>
            </tbody>
          </table>

          <div class="ticket-section-title">FARE SUMMARY & PAYMENT BREAKDOWN</div>
          <div class="ticket-fare-box">
            <div class="ticket-fare-left">
              <div class="ticket-fare-line"><span>Base Airfare:</span> <span>₹11,600</span></div>
              <div class="ticket-fare-line"><span>Seat Selection Fee:</span> <span>₹250</span></div>
              <div class="ticket-fare-line"><span>Taxes & Airline Fees:</span> <span>₹1,892</span></div>
              <div class="ticket-fare-line"><span>Journey Add-ons:</span> <span>₹549</span></div>
            </div>
            <div class="ticket-fare-right">
              <div>TOTAL AMOUNT PAID</div>
              <div class="ticket-fare-grand-total">₹14,291</div>
              <div style="font-size: 0.66rem; color: #059669; font-weight: 700;">Paid via Card (Simulated)</div>
            </div>
          </div>

          <div class="ticket-guidelines-box">
            <div><strong>• Photo Identification:</strong> Valid government photo ID (Aadhaar, Passport, Voter ID) required at airport entrance.</div>
            <div><strong>• Airport Reporting:</strong> Web check-in opens 48 hours prior. Reporting counter closes 60 mins before departure; gate closes 25 mins prior.</div>
            <div><strong>• Baggage Policy:</strong> Standard hand baggage allowance 7 kg (1 piece); check-in baggage 15 kg per passenger.</div>
          </div>

          <div class="ticket-footer-row">
            <div class="ticket-footer-text">
              <strong>FlyWise Intelligent Travel & Journey Management System</strong><br>
              Electronically generated travel document verified against live MySQL records. No real financial transaction was conducted.
            </div>
            <div class="ticket-footer-qr">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 25 25" width="54" height="54"><rect width="25" height="25" fill="#ffffff" /><rect x="0" y="0" width="7" height="1" fill="#000" /></svg>
              <div class="ticket-qr-caption">PNR: FW-BOM99A</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html_content)

if os.path.exists(PDF_PATH):
    os.remove(PDF_PATH)

cmd = [
    EDGE_PATH,
    "--headless=new",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={PDF_PATH}",
    HTML_PATH
]

result = subprocess.run(cmd, capture_output=True, text=True)
with open(PDF_PATH, 'rb') as f:
    pdf_bytes = f.read()

pages = re.findall(rb'/Type\s*/Page\b', pdf_bytes)
print(f"MULTI-PASSENGER PRINTED PDF PAGE COUNT: {len(pages)} PAGE(S)")
assert len(pages) == 1, f"Expected 1 page, got {len(pages)}"
print("MULTI-PASSENGER TEST PASSED: Exactly 1 A4 Page!")
