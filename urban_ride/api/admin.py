from django.contrib import admin
from .models import User, Slot, SlotParticipant, Auto, AutoQueue


class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'phone', 'user_type',)
    search_fields = ('username', 'email', 'phone')

class SlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at')
    search_fields = ('id', 'start_time', 'end_time')

class SlotParticipantAdmin(admin.ModelAdmin):
    list_display = ('id', 'slot', 'user', 'status', 'convenience_fee', 'paid', 'joined_at')
    search_fields = ('id', 'slot', 'user', 'status')

class AutoAdmin(admin.ModelAdmin):
    list_display = ('id', 'driver', 'license_plate', 'status')
    search_fields = ('id', 'driver', 'license_plate', 'status')


admin.site.register(User, UserAdmin)
admin.site.register(Slot, SlotAdmin)
admin.site.register(SlotParticipant, SlotParticipantAdmin)
admin.site.register(Auto, AutoAdmin)
admin.site.register(AutoQueue)
