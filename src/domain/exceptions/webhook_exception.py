from src.core.exceptions import NotFoundException


class WebhookSubscriptionNotFoundException(NotFoundException):
    """Webhook-подписка не найдена."""

    def __init__(self, subscription_id: int):
        super().__init__(resource="WebhookSubscription", identifier=subscription_id)
