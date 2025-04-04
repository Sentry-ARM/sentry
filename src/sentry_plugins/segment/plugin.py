from sentry import http
from sentry.integrations.base import FeatureDescription, IntegrationFeatures
from sentry.plugins.bases.data_forwarding import DataForwardingPlugin
from sentry_plugins.base import CorePluginMixin
from sentry_plugins.utils import get_secret_field_config

DESCRIPTION = """
Send Sentry events to Segment.

This integration allows you to collect all your client-side data for Sentry to send to Segment.

Segment is a customer data platform (CDP) that helps you collect, clean, and control your customer data.
"""


class SegmentPlugin(CorePluginMixin, DataForwardingPlugin):
    title = "Segment"
    slug = "segment"
    description = DESCRIPTION
    conf_key = "segment"
    required_field = "write_key"

    endpoint = "https://api.segment.io/v1/track"
    feature_descriptions = [
        FeatureDescription(
            """
            Forward Sentry errors and events to Segment.
            """,
            IntegrationFeatures.DATA_FORWARDING,
        )
    ]

    def get_config(self, project, user=None, initial=None, add_additional_fields: bool = False):
        return [
            get_secret_field_config(
                name="write_key",
                label="Write Key",
                secret=self.get_option("write_key", project),
                help_text="Your Segment write key",
            )
        ]

    def get_rate_limit(self):
        return (200, 1)

    # https://segment.com/docs/spec/track/
    def get_event_payload(self, event):
        context = {"library": {"name": "sentry", "version": self.version}}

        props = {
            "eventId": event.event_id,
            "transaction": event.get_tag("transaction") or "",
            "release": event.get_tag("sentry:release") or "",
            "level": event.get_tag("level") or "",
            "environment": event.get_tag("environment") or "",
        }

        if "user" in event.interfaces:
            user = event.interfaces["user"]
            if user.ip_address:
                context["ip"] = user.ip_address
            user_id = user.id
        else:
            user_id = None

        if "request" in event.interfaces:
            http = event.interfaces["request"]
            headers = http.headers
            if not isinstance(headers, dict):
                headers = dict(headers or ())

            context.update(
                {
                    "userAgent": headers.get("User-Agent", ""),
                    "page": {
                        "url": http.url,
                        "method": http.method,
                        "search": http.query_string or "",
                        "referrer": headers.get("Referer", ""),
                    },
                }
            )

        if "exception" in event.interfaces:
            exc = event.interfaces["exception"].values[0]
            props.update({"exceptionType": exc.type})

        return {
            "context": context,
            "userId": user_id,
            "event": "Error Captured",
            "properties": props,
            "integration": {"name": "sentry", "version": self.version},
            "timestamp": event.datetime.isoformat() + "Z",
        }

    def forward_event(self, event, payload, **kwargs):
        # TODO(dcramer): we currently only support authenticated events, as the
        # value of anonymous errors/crashes/etc is much less meaningful in the
        # context of Segment

        # we currently only support errors
        if event.get_event_type() != "error":
            return

        # we avoid instantiating interfaces here as they're only going to be
        # used if there's a User present
        user_interface = event.data.get("user")
        if not user_interface:
            return

        user_id = user_interface.get("id")

        if not user_id:
            return

        write_key = self.get_option("write_key", event.project)
        if not write_key:
            return

        with http.build_session() as session:
            session.post(self.endpoint, json=payload, auth=(write_key, ""))
