# ─────────────────────────────────────────────
# File: apps/payments/utils.py
# Twilio WhatsApp notification helper
# ─────────────────────────────────────────────

from django.conf import settings


def send_whatsapp_booking_notification(booking, payment):
    """
    Sends a WhatsApp message to the owner when a booking is paid.
    Requires TWILIO_* settings to be configured.
    Fails silently so a Twilio error never breaks a booking.
    """
    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        advance_amount = payment.amount_rupees
        total_amount   = booking.total_cost

        message_body = (
            f"🎮 *New CONSOLEX Booking!*\n\n"
            f"👤 Customer : {booking.user.get_full_name() or booking.user.email}\n"
            f"📞 Phone    : {getattr(booking.user, 'phone_number', 'N/A')}\n"
            f"📅 Date     : {booking.booking_date.strftime('%d %b %Y')}\n"
            f"⏰ Time     : {booking.start_time.strftime('%I:%M %p')} — "
            f"{booking.end_time.strftime('%I:%M %p')}\n"
            f"🎯 Game     : {booking.game_console.name if booking.game_console else 'N/A'}\n"
            f"👥 Players  : {booking.number_of_players}\n"
            f"💰 Total    : ₹{total_amount}\n"
            f"✅ Advance  : ₹{advance_amount} (Paid)\n"
            f"💵 Balance  : ₹{total_amount - advance_amount} (Due at venue)\n\n"
            f"Booking ID  : #{booking.id}"
        )

        client.messages.create(
            body=message_body,
            from_=settings.TWILIO_WHATSAPP_FROM,
            to=settings.OWNER_WHATSAPP_TO,
        )

    except ImportError:
        # twilio package not installed yet — safe to ignore during development
        print("[CONSOLEX] Twilio not installed. Install with: pip install twilio")
    except Exception as e:
        # Never crash a booking because of a notification failure
        print(f"[CONSOLEX] WhatsApp notification failed: {e}")