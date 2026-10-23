import { Text, Timeline } from "@mantine/core";

import type { Schemas } from "../api/client";
import { ACTOR_LABELS, REASON_LABELS } from "../shared/dictionaries";
import { formatDateTime } from "../shared/format";
import { statusInfo } from "../shared/statuses";

/** Журнал переходов статуса: кто, когда и почему. Коды без подписи видит только аналитик. */
export function EventsTimeline({
  events,
  showCodes = false,
}: {
  events: Schemas["Event"][];
  showCodes?: boolean;
}) {
  const reasonText = (code?: string | null) =>
    code ? (REASON_LABELS[code] ?? (showCodes ? code : null)) : null;
  return (
    <Timeline active={events.length - 1} bulletSize={14} lineWidth={2}>
      {events.map((event) => (
        <Timeline.Item
          key={event.id}
          title={
            event.from_status
              ? `${statusInfo(event.from_status).label} → ${statusInfo(event.to_status).label}`
              : `Создан черновик`
          }
        >
          <Text size="xs" c="dimmed">
            {formatDateTime(event.at)} · {ACTOR_LABELS[event.actor] ?? event.actor}
            {reasonText(event.reason) ? ` · ${reasonText(event.reason)}` : ""}
          </Text>
          {event.comment && <Text size="sm">«{event.comment}»</Text>}
        </Timeline.Item>
      ))}
    </Timeline>
  );
}
