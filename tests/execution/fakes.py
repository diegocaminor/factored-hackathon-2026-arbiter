from app.execution.adapters import SimulatedHandoffQueue, SimulatedOfferSender


class SpyOfferSender(SimulatedOfferSender):
    def __init__(self):
        self.sent = []

    def send(self, customer_id, product, channel):
        self.sent.append((customer_id, product, channel))
        return super().send(customer_id, product, channel)


class SpyHandoffQueue(SimulatedHandoffQueue):
    def __init__(self):
        self.created = []

    def create(self, customer_id, reason):
        self.created.append((customer_id, reason))
        return super().create(customer_id, reason)
