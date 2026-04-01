import requests
import schedule
import time
import smtplib
import os
from bs4 import BeautifulSoup
from twilio.rest import Client
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ─── CONFIG FROM ENVIRONMENT VARIABLES ───────────────
CHECK_URL = "https://shop.royalchallengers.com/ticket"
CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "5"))

SALE_KEYWORDS = ["buy now", "book now", "add to cart", "buy tickets", "book tickets", "purchase"]
UNAVAILABLE_KEYWORDS = ["sold out", "coming soon", "not available", "ticket sales open soon"]

# Gmail
GMAIL_SENDER     = os.environ["GMAIL_SENDER"]
GMAIL_PASSWORD   = os.environ["GMAIL_PASSWORD"]
GMAIL_RECEIVER   = os.environ["GMAIL_RECEIVER"]

# Twilio WhatsApp
TWILIO_SID       = os.environ["TWILIO_SID"]
TWILIO_TOKEN     = os.environ["TWILIO_TOKEN"]
TWILIO_FROM      = os.environ["TWILIO_FROM"]   # e.g. whatsapp:+14155238886
TWILIO_TO        = os.environ["TWILIO_TO"]     # e.g. whatsapp:+919876543210

# ─── ALERT FUNCTIONS ─────────────────────────────────

def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"]    = GMAIL_SENDER
        msg["To"]      = GMAIL_RECEIVER
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER, GMAIL_PASSWORD)
            server.send_message(msg)
        print("  ✅ Email sent!")
    except Exception as e:
        print(f"  ❌ Email failed: {e}")

def send_whatsapp(message):
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(body=message, from_=TWILIO_FROM, to=TWILIO_TO)
        print("  ✅ WhatsApp sent!")
    except Exception as e:
        print(f"  ❌ WhatsApp failed: {e}")

def alert(title, short_msg, html_body):
    print(f"  🚨 {title}")
    send_whatsapp(short_msg)
    send_email(title, html_body)

# ─── MAIN CHECK ──────────────────────────────────────

ticket_was_available = False  # track state to avoid repeat alerts

def check_tickets():
    global ticket_was_available
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] Checking RCB ticket availability...")

    try:
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        resp = requests.get(CHECK_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        page_text = soup.get_text().lower()

        found_sale        = any(kw in page_text for kw in SALE_KEYWORDS)
        found_unavailable = any(kw in page_text for kw in UNAVAILABLE_KEYWORDS)
        tickets_available = found_sale and not found_unavailable

        if tickets_available and not ticket_was_available:
            # First time detecting availability → ALERT
            alert(
                title="🏏 RCB Tickets Are On Sale NOW!",
                short_msg=(
                    f"🚨 RCB TICKETS ARE LIVE! 🏏\n"
                    f"Book now before they sell out!\n👉 {CHECK_URL}"
                ),
                html_body=f"""
                    <h2>🏏 RCB Tickets Are Available!</h2>
                    <p>Ticket sales have just opened on the RCB website.</p>
                    <p><a href="{CHECK_URL}" style="font-size:18px;color:red;">
                        👉 Click here to book now
                    </a></p>
                    <p><small>Detected at: {now}</small></p>
                """
            )
            ticket_was_available = True

        elif not tickets_available and ticket_was_available:
            # Were available, now sold out
            print("  ℹ️  Tickets appear to be sold out or unavailable again.")
            ticket_was_available = False

        else:
            print("  ❌ Tickets not yet available. Will check again.")

    except Exception as e:
        print(f"  ⚠️  Error: {e}")

# ─── SCHEDULER ───────────────────────────────────────
print(f"🏏 RCB Monitor started — checking every {CHECK_INTERVAL_MINUTES} minutes.")
check_tickets()
schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_tickets)

while True:
    schedule.run_pending()
    time.sleep(30)
