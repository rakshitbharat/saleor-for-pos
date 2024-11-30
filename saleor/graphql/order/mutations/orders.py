import graphene
from django.core.exceptions import ValidationError
from decimal import Decimal
from graphql import ResolveInfo

from ....permission.enums import OrderPermissions
from ....order import models as order_models
from ....order import OrderStatus
from ...core.mutations import BaseMutation
from ...core.types import OrderError
from ...core.enums import OrderErrorCode
from ..enums import OrderDiscountType
from ..types import Order
from ...core.utils import from_global_id_or_error
from ....plugins.manager import get_plugins_manager
from ....order.events import order_discount_added_event
from ....order.models import Order as OrderModel
from ....order.enums import DiscountType

class OrderDiscountAndTaxInput(graphene.InputObjectType):
    discount_amount = graphene.Float(description="Fixed discount amount to apply.")
    tax_amount = graphene.Float(description="Fixed tax amount to apply.")

class OrderDiscountAndTaxUpdate(BaseMutation):
    class Arguments:
        order = graphene.ID(required=True, description="ID of the order to update.")
        input = OrderDiscountAndTaxInput(
            required=True,
            description="Fields required to update order discount and tax."
        )

    order_discount_and_tax = graphene.Field(Order, description="Order with updated discount and tax.")

    class Meta:
        description = "Updates order discount and tax amounts."
        permissions = (OrderPermissions.MANAGE_ORDERS,)
        error_type_class = OrderError
        error_type_field = "order_errors"

    @classmethod
    def get_instance(cls, info: ResolveInfo, **data):
        order_id = data.get("order")
        print("DEBUG: Received order_id:", order_id)  # Debug log
        
        try:
            # Decode the global ID to get the database ID
            _, db_id = from_global_id_or_error(order_id, Order)
            print("DEBUG: Decoded db_id:", db_id)  # Debug log
            
            # Get the order instance using the database ID
            order = order_models.Order.objects.get(pk=db_id)
            print("DEBUG: Retrieved order:", order)  # Debug log
            
            if not order:
                raise ValidationError({
                    "order": ValidationError(
                        "Order not found.",
                        code=OrderErrorCode.NOT_FOUND
                    )
                })
            
            return order
            
        except Exception as e:
            print("DEBUG: Error in get_instance:", str(e))  # Debug error
            print("DEBUG: Error type:", type(e))  # Check error type
            raise

    @classmethod
    def perform_mutation(cls, _root, info: ResolveInfo, /, **data):
        instance = cls.get_instance(info, **data)
        input_data = data.get("input", {})
        
        if instance.status not in [OrderStatus.DRAFT, OrderStatus.UNCONFIRMED]:
            raise ValidationError({
                "order": ValidationError(
                    "Only draft and unconfirmed orders can be modified.",
                    code=OrderErrorCode.NOT_EDITABLE
                )
            })

        cls.check_channel_permissions(info, [instance.channel_id])

        discount_amount = input_data.get("discount_amount")
        tax_amount = input_data.get("tax_amount")

        if discount_amount is not None:
            if discount_amount < 0:
                raise ValidationError({
                    "discount_amount": ValidationError(
                        "Discount amount cannot be negative.",
                        code=OrderErrorCode.INVALID
                    )
                })
            if discount_amount > instance.total.gross.amount:
                raise ValidationError({
                    "discount_amount": ValidationError(
                        "Discount amount cannot be greater than order total.",
                        code=OrderErrorCode.INVALID
                    )
                })
            discount = instance.discounts.create(
                amount_value=Decimal(str(discount_amount)),
                type=OrderDiscountType.MANUAL.value,
                reason="POS Discount"
            )
            order_discount_added_event(
                order=instance,
                user=info.context.user,
                app=info.context.app,
                order_discount=discount,
            )

        if tax_amount is not None:
            if tax_amount < 0:
                raise ValidationError({
                    "tax_amount": ValidationError(
                        "Tax amount cannot be negative.",
                        code=OrderErrorCode.INVALID
                    )
                })
            instance.shipping_tax_rate = Decimal(str(tax_amount))
            instance.shipping_tax_class_id = None

        instance.save()

        # Get the plugin manager and trigger recalculation
        manager = get_plugins_manager(allow_replica=False)
        instance.should_refresh_prices = True
        instance.save(update_fields=["should_refresh_prices"])

        return OrderDiscountAndTaxUpdate(order_discount_and_tax=instance) 