from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator
from cloudinary_storage.storage import MediaCloudinaryStorage
from cloudinary.models import CloudinaryField

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        return self.create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    USER_TYPES = (
        ('CUSTOMER', 'Customer'),
        ('DRIVER', 'Driver'),
        ('ADMIN', 'Admin'),
    )
    username = models.CharField(max_length=30, unique=True)
    password = models.CharField(max_length=128)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    user_type = models.CharField(max_length=10, choices=USER_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    college = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    image = CloudinaryField('image', folder='profile_images', blank=True, null=True)

    REQUIRED_FIELDS = ['email', 'phone', 'user_type']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'users'

class Auto(models.Model):
    STATUS_CHOICES = (
        ('AVAILABLE', 'Available'),
        ('BOOKED', 'Booked'),
        ('QUEUED', 'Queued'),
    )
    
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='autos')
    license_plate = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='AVAILABLE')

    class Meta:
        db_table = 'autos'

class Slot(models.Model):
    STATUS_CHOICES = (
        ('PENDING_DRIVER', 'Pending Driver'),
        ('OPEN', 'Open'),
        ('BOOKED', 'Booked'),
        ('CANCELLED', 'Cancelled'),
        ('FINALIZED', 'Finalized'),
    )
    
    LOCATIONS = (
        ('IITJ', 'IIT Jodhpur'),
        ('NIFTJ', 'NIFT Jodhpur'),
        ('Paota', 'Paota'),
        ('Ratanada', 'Ratanada'),
        ('Sardarpura', 'Sardarpura'),
    )

    auto = models.ForeignKey(Auto, on_delete=models.CASCADE, related_name='slots')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_slots',default=None, null=True)
    max_capacity = models.IntegerField(validators=[MinValueValidator(1)])
    current_capacity = models.IntegerField(default=1)
    fare = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING_DRIVER')
    ride_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    start_loc = models.CharField(max_length=10, choices=LOCATIONS, default='IITJ')
    dest_loc = models.CharField(max_length=10, choices=LOCATIONS, default='Paota')

    class Meta:
        db_table = 'slots'

class SlotParticipant(models.Model):
    STATUS_CHOICES = (
        ('JOINED', 'Joined'),
        ('REMOVED', 'Removed'),
        ('CANCELLED', 'Cancelled'),
    )
    
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='slot_participants')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    convenience_fee = models.DecimalField(max_digits=10, decimal_places=2)
    paid = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'slot_participants'

class AutoQueue(models.Model):
    auto = models.ForeignKey(Auto, on_delete=models.CASCADE, related_name='auto_queue', default=None, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        db_table = 'auto_queue'
