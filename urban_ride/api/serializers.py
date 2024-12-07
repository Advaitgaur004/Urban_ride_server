from rest_framework import serializers
from django.utils import timezone
from .models import Auto, Slot, User, SlotParticipant, AutoQueue
from django.contrib.auth.hashers import make_password

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'password', 'user_type', 
                 'created_at', 'college', 'address', 'image', 'image_url')
        read_only_fields = ('id', 'created_at', 'image_url')

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data.get('password'))
        return super().create(validated_data)

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None

class AutoSerializer(serializers.ModelSerializer):
    driver_details = UserSerializer(source='driver', read_only=True)
    driver_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Auto
        fields = ('id', 'driver', 'driver_id', 'driver_details', 'license_plate', 'status')
        read_only_fields = ('id', 'driver', 'driver_details', 'status')

    def validate_driver_id(self, value):
        try:
            driver = User.objects.get(id=value)
            if driver.user_type != 'DRIVER':
                raise serializers.ValidationError("User must be a driver")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Driver not found")

class AutoSlotSerializer(serializers.ModelSerializer):
    driver_details = UserSerializer(source='driver', read_only=True)
    driver_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Auto
        fields = ('id', 'driver', 'driver_id', 'driver_details', 'license_plate')
        read_only_fields = ('id', 'driver', 'driver_details')



class SlotSerializer(serializers.ModelSerializer):
    auto_details = AutoSlotSerializer(source='auto', read_only=True)
    participants_count = serializers.IntegerField(source='current_capacity', read_only=True)
    creator_details = UserSerializer(source='creator', read_only=True)
    participants = serializers.SerializerMethodField()
    
    class Meta:
        model = Slot
        fields = ('id', 'max_capacity', 'current_capacity', 'auto', 'auto_details',
                 'fare', 'status', 'ride_time', 'created_at', 'start_loc', 
                 'dest_loc', 'participants_count', 'creator', 'creator_details',
                 'participants')
        read_only_fields = ('id', 'current_capacity', 'created_at', 'participants')

    def get_participants(self, obj):
        participants = SlotParticipant.objects.filter(slot=obj)
        return SlotParticipantSerializer(participants, many=True).data

    def validate_ride_time(self, value):
        from django.utils import timezone
        if value < timezone.now():
            raise serializers.ValidationError("Ride time cannot be in the past")
        return value

    def validate(self, data):
        if 'status' in data and self.instance:
            current_status = self.instance.status
            new_status = data['status']

            valid_transitions = {
                'PENDING_DRIVER': ['OPEN', 'CANCELLED'],
                'OPEN': ['BOOKED', 'CANCELLED'],
                'BOOKED': ['CANCELLED'],
                'CANCELLED': []
            }
            
            if new_status not in valid_transitions.get(current_status, []):
                raise serializers.ValidationError(
                    f"Invalid status transition from {current_status} to {new_status}"
                )
        return data


class SlotParticipantSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    slot_details = serializers.SerializerMethodField()
    
    class Meta:
        model = SlotParticipant
        fields = ('id', 'slot', 'slot_details', 'user', 'user_details', 'status',
                 'convenience_fee', 'paid', 'joined_at')
        read_only_fields = ('id', 'joined_at', 'slot', 'user', 'status')

    def get_slot_details(self, obj):
        return {
            'id': obj.slot.id,
            'fare': obj.slot.fare,
            'ride_time': obj.slot.ride_time,
            'start_loc': obj.slot.start_loc,
            'dest_loc': obj.slot.dest_loc,
            'status': obj.slot.status,
            'creator': UserSerializer(obj.slot.creator).data,
            'auto': AutoSlotSerializer(obj.slot.auto).data
        }

    def validate(self, data):
        if self.context.get('slot'):
            slot = self.context['slot']
            if slot.status != 'OPEN':
                raise serializers.ValidationError("can only join open slots")
            if slot.current_capacity >= slot.max_capacity:
                raise serializers.ValidationError("slot is already full")
        return data

class AutoQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoQueue
        fields = ('id', 'auto', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate(self, data):
        if data.get('auto').status != 'AVAILABLE':
            raise serializers.ValidationError("can only queue available autos")
        return data
