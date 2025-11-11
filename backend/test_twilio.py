import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_number = os.getenv("TWILIO_PHONE_NUMBER")
to_number = os.getenv("TWILIO_RECEIVER_NUMBER")

client = Client(account_sid, auth_token)

message = client.messages.create(
    body="🚧 Test SMS from PotholeWatch – Twilio connected successfully!",
    from_=from_number,
    to=to_number
)

print("✅ Message sent successfully! SID:", message.sid)
