from flask import url_for

from portality.lib import dates
from portality.events.consumer import EventConsumer
from portality import constants
from portality import models
from portality.bll import DOAJ, exceptions
from portality.lib.seamless import SeamlessException


class ApplicationPublisherCreatedNotify(EventConsumer):
    ID = "application:publisher:created:notify"

    @classmethod
    def consumes(cls, event):
        return event.id == constants.EVENT_APPLICATION_CREATED and event.context.get("application") is not None

    @classmethod
    def consume(cls, event):
        context = event.context
        app = context.get("application")
        if app is None:
            return
        try:
            application = models.Application(**app)
        except SeamlessException:
            raise exceptions.NoSuchObjectException("Could not create application object")
        if application is None:
            raise exceptions.NoSuchObjectException("Could not create application object")
        if not application.editor:
            return

        svc = DOAJ.notificationsService()

        notification = models.Notification()
        notification.who = application.owner
        notification.created_by = cls.ID
        notification.classification = constants.NOTIFICATION_CLASSIFICATION_CREATE
        notification.message = svc.message(cls.ID).format(title=application.bibjson().title,
                                                          journal_url=application.bibjson().journal_url,
                                                          application_date=dates.human_date(application.date_applied),
                                                          volunteers_url=url_for("doaj.volunteers"))

        svc.notify(notification)