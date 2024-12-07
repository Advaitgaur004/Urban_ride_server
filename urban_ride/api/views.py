from rest_framework import status, viewsets, generics, serializers, mixins
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.contrib.auth import get_user_model

from .models import Auto, Slot, User, AutoQueue, SlotParticipant
from .serializers import (
    AutoSerializer, 
    SlotSerializer, 
    AutoQueueSerializer, 
    UserSerializer,
    SlotParticipantSerializer
)
#TODO : Please add creator detail in slot and participant's detail too.

class UserViewSet(mixins.ListModelMixin,mixins.CreateModelMixin,mixins.UpdateModelMixin,mixins.DestroyModelMixin,mixins.RetrieveModelMixin,viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = []
    permission_classes = []
    parser_classes = (MultiPartParser, FormParser)

class AutoViewSet(viewsets.ModelViewSet):
    queryset = Auto.objects.all()
    serializer_class = AutoSerializer
    authentication_classes = []
    permission_classes = []

class AutoCreateView(generics.CreateAPIView):
    serializer_class = AutoSerializer
    permission_classes = []
    
    def perform_create(self, serializer):
        driver = User.objects.get(id=self.request.data.get('driver_id'))

        #TODO: Only that driver which is attached with the slot should accept this (not any driver)(for simplicity any driver can accept for now)
        if driver.user_type != 'DRIVER':
            return Response(
                {"error": "User must be a driver"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            auto = serializer.save(
                driver=driver,
                license_plate=self.request.data.get('license_plate'),
                status='AVAILABLE'
            )
            AutoQueue.objects.create(auto=auto)
            
        return Response(serializer.data)

class AutoQueueViewSet(viewsets.ModelViewSet):
    queryset = AutoQueue.objects.all()
    serializer_class = AutoQueueSerializer
    authentication_classes = []
    permission_classes = []

class SlotCreateView(generics.CreateAPIView):
    serializer_class = SlotSerializer
    authentication_classes = []
    permission_classes = []
    
    def create(self, request, *args, **kwargs):
        try:
            auto_queue = AutoQueue.objects.latest('created_at')
            auto = auto_queue.auto
            
            # Validate creator_id
            creator_id = request.data.get('creator_id')
            if not creator_id:
                return Response(
                    {"error": "Creator ID is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                creator = User.objects.get(id=creator_id)
            except User.DoesNotExist:
                return Response(
                    {"error": "Invalid creator ID"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer_data = {
                'auto': auto.id,
                'creator': creator.id,
                'max_capacity': request.data.get('max_capacity', 4),
                'current_capacity': request.data.get('current_capacity', 1),
                'fare': request.data.get('fare', 100),
                'ride_time': request.data.get('ride_time'),
                'start_loc': request.data.get('start_loc', 'IITJ'),
                'dest_loc': request.data.get('dest_loc', 'Paota')
            }
            
            serializer = self.get_serializer(data=serializer_data)
            
            try:
                serializer.is_valid(raise_exception=True)
                
                with transaction.atomic():
                    slot = serializer.save(
                        status='PENDING_DRIVER',
                    )
                    
                    auto.status = 'QUEUED'
                    auto.save()
                    auto_queue.delete()
                    
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
            except serializers.ValidationError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        except AutoQueue.DoesNotExist:
            return Response(
                {"error": "No autos in queue"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Unexpected error: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AutoDriverAcceptView(generics.UpdateAPIView):
    queryset = Slot.objects.all()
    serializer_class = SlotSerializer
    authentication_classes = []
    permission_classes = []

    def update(self, request, *args, **kwargs):
        slot = self.get_object()
        if slot.status != 'PENDING_DRIVER':
            return Response(
                {"error": "Only pending slots can be accepted"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            serializer = self.get_serializer(slot, data={'status': 'OPEN'}, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            slot.auto.status = 'BOOKED'
            slot.auto.save()
        
        return Response(serializer.data)

class SlotParticipantCreateView(generics.CreateAPIView):

    #TODO: User xyz can create and join the same slot multiple times fix this
    #TODO: User xyz can join the same slot multiple times fix this

    serializer_class = SlotParticipantSerializer
    queryset = SlotParticipant.objects.all()
    authentication_classes = []
    permission_classes = []

    def create(self, request, *args, **kwargs):
        try:
            slot = Slot.objects.get(pk=self.kwargs['pk'])
            if slot.status != 'OPEN':
                return Response(
                    {"error": "Slot is not open"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if slot.current_capacity >= slot.max_capacity:
                return Response(
                    {"error": "Slot is already full"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user_id = request.data.get('user_id')
            try:
                user = User.objects.get(id=user_id)
                if user.user_type != 'CUSTOMER':
                    return Response(
                        {"error": "User must be a customer"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if SlotParticipant.objects.filter(slot=slot, user=user).exists():
                    return Response(
                        {"error": "You have already joined this slot"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if slot.creator.id == user.id:
                    return Response(
                        {"error": "Slot creator cannot join as a participant"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                user_slots = SlotParticipant.objects.filter(
                    user=user,
                    slot__ride_time=slot.ride_time,
                    slot__status__in=['OPEN', 'PENDING_DRIVER']
                )
                if user_slots.exists():
                    return Response(
                        {"error": "You already have a slot booked for this time"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = self.get_serializer(
                data={'convenience_fee': request.data.get('convenience_fee')},
                context={'slot': slot}
            )
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                participant = serializer.save(
                    slot=slot,
                    user=user,
                    status='JOINED'
                )
                
                slot.current_capacity += 1
                slot.save()
                
            return Response(self.get_serializer(participant).data, status=status.HTTP_201_CREATED)
            
        except Slot.DoesNotExist:
            return Response(
                {"error": "Slot not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SlotViewSet(viewsets.ModelViewSet):
    queryset = Slot.objects.all()
    serializer_class = SlotSerializer
    authentication_classes = []
    permission_classes = []

class PaymentViewSet(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = []

    @action(detail=False, methods=['post'])
    def convenience_fee(self, request):
        total_fee = 50

        return Response({
            'total_fee': total_fee
        })
