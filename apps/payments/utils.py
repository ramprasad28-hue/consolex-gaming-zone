# apps/payments/utils.py
import os
from django.conf import settings

def send_whatsapp_booking_notification(booking, payment):
    """
    Sends WhatsApp notification to owner via Twilio.
    Designed to fail silently. Never raises exceptions.
    """
    try:
        # 1. Check if Twilio is installed
        from twilio.rest import Client
    except ImportError:
        print("Twilio not installed. Skipping WhatsApp notification.")
        return False

    try:
        # 2. Fetch credentials safely
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        from_whatsapp = os.environ.get('TWILIO_WHATSAPP_FROM')
        to_whatsapp = os.environ.get('OWNER_WHATSAPP_TO')

        if not all([account_sid, auth_token, from_whatsapp, to_whatsapp]):
            print("Twilio credentials missing. Skipping WhatsApp notification.")
            return False

        # 3. Construct Message
        message_body = (
            f"*New Booking Confirmed!*\n\n"
            f"🎮 *Game:* {booking.game_console.name if booking.game_console else 'Any Console'}\n"
            f"👤 *Customer:* {booking.user.first_name} {booking.user.last_name}\n"
            f"📧 *Email:* {booking.user.email}\n"
            f"📅 *Date:* {booking.booking_date.strftime('%d %b %Y')}\n"
            f"⏰ *Time:* {booking.start_time.strftime('%I:%M %p')} - {booking.end_time.strftime('%I:%M %p')}\n"
            f"👥 *Players:* {booking.number_of_players}\n\n"
            f"💰 *Total:* ₹{booking.total_cost}\n"
            f"✅ *Advance Paid:* ₹{payment.amount_rupees}\n"
            f"💵 *Balance Due:* ₹{booking.balance_amount}\n\n"
            f"🆔 *Booking ID:* #{booking.id}\n"
            f"🔗 *Razorpay ID:* {payment.razorpay_payment_id}"
        )

        # 4. Send Message
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=message_body,
            from_=from_whatsapp,
            to=to_whatsapp
        )
        print(f"WhatsApp notification sent successfully. SID: {message.sid}")
        return True

    except Exception as e:
        # NEVER let this interrupt the booking flow
        print(f"Failed to send WhatsApp notification: {str(e)}")
        return False