from __future__ import annotations

from language_nav.contracts import FailureMonitorState, MonitorLevel


class NoOpFailureMonitor:
    """Explicit development-only monitor; never represented as Research 2 evidence."""

    def state(self) -> FailureMonitorState:
        return FailureMonitorState("failure-monitor/v1", MonitorLevel.NOMINAL, 0.0, ("monitor_unavailable",), 0)


class Research2MonitorAdapter:
    def __init__(self, message_provider) -> None:
        self._message_provider = message_provider

    def state(self) -> FailureMonitorState:
        message = self._message_provider()
        return FailureMonitorState(
            schema_version="failure-monitor/v1",
            level=MonitorLevel(str(message.level)),
            failure_probability=float(message.failure_probability),
            reason_codes=tuple(message.reason_codes),
            observed_at_ns=int(message.observed_at_ns),
        )

