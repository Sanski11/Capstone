from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from flask import url_for
from extensions import mail  # or app.mail if you import directly

serializer = URLSafeTimedSerializer("your_secret_key")

def send_verification_email(email, token):
    link = url_for('verify_email', token=token, _external=True)
    
    msg = Message("Email Verification", recipients=[email])
    msg.body = f"Hi!\nClick the link to verify your email:\n{link}"
    
    try:
        mail.send(msg)
        print(f"✅ Email sent to {email}")
    except Exception as e:
        print(f"❌ Email send failed: {e}")

def verify_token(token, expiration=3600):
    try:
        return serializer.loads(token, salt="email-confirm", max_age=expiration)
    except Exception:
        return None
