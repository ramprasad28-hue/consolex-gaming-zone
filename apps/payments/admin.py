from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'razorpay_order_id', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('razorpay_order_id', 'booking__user__email')
    readonly_fields = ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'created_at')
