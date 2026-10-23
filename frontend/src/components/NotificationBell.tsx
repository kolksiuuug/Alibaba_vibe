import {
  ActionIcon,
  Indicator,
  Popover,
  ScrollArea,
  Stack,
  Text,
  UnstyledButton,
} from "@mantine/core";
import { IconBell } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import type { Schemas } from "../api/client";
import { Api } from "../api/endpoints";
import { formatDateTime } from "../shared/format";

/** Центр уведомлений в продукте: email и SMS не используются. */
export function NotificationBell() {
  const [opened, setOpened] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const notifications = useQuery({
    queryKey: ["notifications"],
    queryFn: Api.notifications,
    refetchInterval: 5000,
  });
  const markRead = useMutation({
    mutationFn: Api.readNotification,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  function open(item: Schemas["Notification"]) {
    if (!item.is_read) markRead.mutate(item.id);
    setOpened(false);
    if (item.application_id) navigate(`/applications/${item.application_id}`);
  }

  const unread = notifications.data?.unread_count ?? 0;
  const items = notifications.data?.items ?? [];

  return (
    <Popover opened={opened} onChange={setOpened} position="bottom-end" width={380} shadow="md">
      <Popover.Target>
        <Indicator label={unread} size={18} disabled={unread === 0} offset={4}>
          <ActionIcon
            variant="default"
            size="lg"
            aria-label="Уведомления"
            onClick={() => setOpened((value) => !value)}
          >
            <IconBell size={20} />
          </ActionIcon>
        </Indicator>
      </Popover.Target>
      <Popover.Dropdown p={0}>
        <Text fw={600} p="sm" pb={4}>
          Уведомления
        </Text>
        <ScrollArea.Autosize mah={420}>
          {items.length === 0 ? (
            <Text c="dimmed" size="sm" p="sm">
              Пока нет уведомлений. Они появятся, когда изменится статус заявки.
            </Text>
          ) : (
            <Stack gap={0}>
              {items.map((item) => (
                <UnstyledButton
                  key={item.id}
                  onClick={() => open(item)}
                  p="sm"
                  style={{
                    borderTop: "1px solid var(--mantine-color-gray-2)",
                    background: item.is_read ? undefined : "var(--mantine-color-alfa-0)",
                  }}
                >
                  <Text size="sm" fw={item.is_read ? 400 : 600}>
                    {item.title}
                  </Text>
                  <Text size="sm" c="dimmed">
                    {item.body}
                  </Text>
                  <Text size="xs" c="dimmed" mt={2}>
                    {formatDateTime(item.created_at)}
                  </Text>
                </UnstyledButton>
              ))}
            </Stack>
          )}
        </ScrollArea.Autosize>
      </Popover.Dropdown>
    </Popover>
  );
}
