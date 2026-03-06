"""
Event Bus connector — publishes domain events to external systems.

Used to notify other microservices about lifecycle changes:
- rfq.created, rfq.status_changed, rfq.deadline_changed
- stage.advanced, stage.blocked, stage.completed
- reminder.created, reminder.sent
- file.uploaded, file.deleted

Methods:
- publish(event_type, payload)  — POST event to EVENT_BUS_URL
"""
