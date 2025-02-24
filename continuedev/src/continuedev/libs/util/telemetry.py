import os
import socket
from typing import Any

from dotenv import load_dotenv

from ..constants.main import CONTINUE_SERVER_VERSION_FILE
from .commonregex import clean_pii_from_any
from .paths import getServerFolderPath

load_dotenv()
in_codespaces = os.getenv("CODESPACES") == "true"
POSTHOG_API_KEY = "phc_JS6XFROuNbhJtVCEdTSYk6gl5ArRrTNMpCcguAXlSPs"


def is_connected():
    try:
        # connect to the host -- tells us if the host is actually reachable
        socket.create_connection(("www.google.com", 80))
        return True
    except OSError:
        pass
    return False


class PostHogLogger:
    unique_id: str = "NO_UNIQUE_ID"
    allow_anonymous_telemetry: bool = False
    posthog = None

    def __init__(self, api_key: str):
        self.api_key = api_key

    def setup(self, unique_id: str, allow_anonymous_telemetry: bool):
        self.unique_id = unique_id or "NO_UNIQUE_ID"
        self.allow_anonymous_telemetry = allow_anonymous_telemetry or False

        # Capture initial event
        self.capture_event("session_start", {"os": os.name})

    def capture_event(self, event_name: str, event_properties: Any):
        """Safely capture event. Telemetry should never be the reason Continue doesn't work"""
        try:
            self._capture_event(event_name, event_properties)
        except Exception as e:
            print(f"Failed to capture event: {e}")
            pass

    _found_disconnected: bool = False

    def _capture_event(self, event_name: str, event_properties: Any):
        # logger.debug(
        #     f"Logging to PostHog: {event_name} ({self.unique_id}, {self.allow_anonymous_telemetry}): {event_properties}")
        telemetry_path = os.path.expanduser("~/.continue/telemetry.log")

        # Make sure the telemetry file exists
        if not os.path.exists(telemetry_path):
            os.makedirs(os.path.dirname(telemetry_path), exist_ok=True)
            open(telemetry_path, "w").close()

        with open(telemetry_path, "a") as f:
            str_to_write = f"{event_name}: {event_properties}\n{self.unique_id}\n{self.allow_anonymous_telemetry}\n\n"
            f.write(str_to_write)

        if not self.allow_anonymous_telemetry:
            return

        # Clean PII from event properties
        event_properties = clean_pii_from_any(event_properties)

        # Add additional properties that are on every event
        if in_codespaces:
            event_properties["codespaces"] = True

        server_version_file = os.path.join(
            getServerFolderPath(), CONTINUE_SERVER_VERSION_FILE
        )
        if os.path.exists(server_version_file):
            with open(server_version_file, "r") as f:
                event_properties["server_version"] = f.read()

        # Add operating system
        event_properties["os"] = os.name

        # Send event to PostHog
        if self.posthog is None:
            from posthog import Posthog

            # The personal API key is necessary only if you want to use local evaluation of feature flags.
            self.posthog = Posthog(self.api_key, host="https://app.posthog.com")

        if is_connected():
            self.posthog.capture(self.unique_id, event_name, event_properties)
        else:
            if not self._found_disconnected:
                self._found_disconnected = True
                raise ConnectionError("No internet connection")


posthog_logger = PostHogLogger(api_key=POSTHOG_API_KEY)
