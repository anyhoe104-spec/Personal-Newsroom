from .api_stub import collect_api_stub
from .google_alert import collect_google_alert
from .rss import collect_rss


COLLECTORS = {
    "rss": collect_rss,
    "google_alert": collect_google_alert,
    "api_stub": collect_api_stub,
}
