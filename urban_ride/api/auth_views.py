import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.core.cache import cache
from .models import User
from .serializers import UserSerializer

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp):
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = settings.EMAIL_HOST_USER
        sender_password = settings.EMAIL_HOST_PASSWORD

        print(sender_email, sender_password)

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = email
        message["Subject"] = "Urban Ride - Login OTP"

        body = f"""
        Hello!

        Your OTP for Urban Ride login is: {otp}

        This OTP will expire in 5 minutes.
        Please do not share this OTP with anyone.

        Best regards,
        Urban Ride Team
        """
        message.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@api_view(['POST'])
@permission_classes([AllowAny])
def request_otp(request):
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    otp = generate_otp()
    cache.set(f'login_otp_{email}', otp, timeout=300)

    if send_otp_email(email, otp):
        return Response({'message': 'OTP sent successfully'}, status=status.HTTP_200_OK)
    return Response({'error': 'Failed to send OTP'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    email = request.data.get('email')
    otp = request.data.get('otp')

    if not email or not otp:
        return Response({'error': 'Email and OTP are required'}, status=status.HTTP_400_BAD_REQUEST)

    stored_otp = cache.get(f'login_otp_{email}')
    if not stored_otp:
        return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

    if otp != stored_otp:
        return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
        serializer = UserSerializer(user)
        cache.delete(f'login_otp_{email}')
        return Response({
            'message': 'Login successful',
            'user': serializer.data
        }, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
