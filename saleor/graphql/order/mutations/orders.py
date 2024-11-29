import graphene
from django.core.exceptions import ValidationError
from decimal import Decimal

from ....permission.enums import OrderPermissions
from ....order import models as order_models
from ....order import OrderStatus, events
from ...core.mutations import BaseMutation
from ...core.types import OrderError
from ...core.enums import OrderErrorCode
from ..types import Order

class OrderDiscountAndTaxUpdate(BaseMutation):
    class Arguments:
        order = graphene.ID(required=True, description="ID of the order to update.")
        discount_amount = graphene.Float(
            description="Fixed discount amount to apply."
        )
        tax_amount = graphene.Float(
            description="Fixed tax amount to apply."
        )

    class Meta:
        description = "Updates order discount and tax amounts."
        permissions = (OrderPermissions.MANAGE_ORDERS,)
        error_type_class = OrderError
        error_type_field = "order_errors"

    order = graphene.Field(Order, description="Order with updated discount and tax.")

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        order_id = data.get("order")
        
        order = cls.get_node_or_error(
            info, order_id, field="order", only_type=order_models.Order
        )

        if order.status not in [OrderStatus.DRAFT, OrderStatus.UNCONFIRMED]:
            raise ValidationError({
                "order": ValidationError(
                    "Only draft and unconfirmed orders can be modified.",
                    code=OrderErrorCode.NOT_EDITABLE
                )
            })

        cls.check_channel_permissions(info, [order.channel_id])

        discount_amount = data.get("discount_amount")
        tax_amount = data.get("tax_amount")

        if discount_amount is not None:
            if discount_amount < 0:
                raise ValidationError({
                    "discount_amount": ValidationError(
                        "Discount amount cannot be negative.",
                        code=OrderErrorCode.INVALID
                    )
                })
            if discount_amount > order.total_gross_amount:
                raise ValidationError({
                    "discount_amount": ValidationError(
                        "Discount amount cannot be greater than order total.",
                        code=OrderErrorCode.INVALID
                    )
                })
            order.total_discount_amount = Decimal(str(discount_amount))

        if tax_amount is not None:
            if tax_amount < 0:
                raise ValidationError({
                    "tax_amount": ValidationError(
                        "Tax amount cannot be negative.",
                        code=OrderErrorCode.INVALID
                    )
                })
            order.total_tax_amount = Decimal(str(tax_amount))

        order.total_net_amount = (
            order.total_gross_amount 
            - (order.total_discount_amount or Decimal("0"))
            - (order.total_tax_amount or Decimal("0"))
        )

        order.save(update_fields=[
            "total_discount_amount",
            "total_tax_amount", 
            "total_net_amount",
            "updated_at"
        ])

        # Create order event
        events.order_updated_event(
            order=order,
            user=info.context.user,
            app=info.context.app,
        )

        return OrderDiscountAndTaxUpdate(order=order) 