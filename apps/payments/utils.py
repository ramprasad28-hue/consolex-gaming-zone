# ─────────────────────────────────────────────
# File: apps/payments/utils.py
# ─────────────────────────────────────────────

from django.conf import settings


def send_whatsapp_booking_notification(booking, payment):
    """
    Sends WhatsApp notification to owner on successful booking.
    NEVER raises — all exceptions are caught so booking flow is safe.
    """
    try:
        from twilio.rest import Client

        sid   = getattr(settings, 'TWILIO_ACCOUNT_SID',  '')
        token = getattr(settings, 'TWILIO_AUTH_TOKEN',   '')
        from_ = getattr(settings, 'TWILIO_WHATSAPP_FROM', '')
        to_   = getattr(settings, 'OWNER_WHATSAPP_TO',   '')

        # Skip silently if credentials are not configured
        if not all([sid, token, from_, to_]):
            print('[CONSOLEX] WhatsApp skipped — Twilio credentials not set.')
            return

        mode   = ' 🧪 DEMO' if payment.is_demo else ''
        client = Client(sid, token)

        body = (
            f"🎮 *New CONSOLEX Booking!*{mode}\n\n"
            f"👤 Customer : {booking.user.get_full_name() or booking.user.email}\n"
            f"📞 Phone    : {getattr(booking.user, 'phone_number', 'N/A')}\n"
            f"📅 Date     : {booking.booking_date.strftime('%d %b %Y')}\n"
            f"⏰ Time     : {booking.start_time.strftime('%I:%M %p')} — "
            f"{booking.end_time.strftime('%I:%M %p')}\n"
            f"🎯 Game     : {booking.game_console.name if booking.game_console else 'N/A'}\n"
            f"👥 Players  : {booking.number_of_players}\n"
            f"💰 Total    : ₹{booking.total_cost}\n"
            f"✅ Advance  : ₹{payment.amount_rupees} (Paid)\n"
            f"💵 Balance  : ₹{booking.balance_amount} (Due at venue)\n\n"
            f"Booking ID  : #{booking.id}"
        )

        client.messages.create(body=body, from_=from_, to=to_)
        print(f'[CONSOLEX] WhatsApp notification sent for Booking #{booking.id}')

    except ImportError:
        print('[CONSOLEX] Twilio not installed — pip install twilio')
    except Exception as e:
        print(f'[CONSOLEX] WhatsApp notification failed: {e}')