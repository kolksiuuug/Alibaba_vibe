import {
  Badge,
  Card,
  Group,
  ScrollArea,
  SegmentedControl,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Api } from "../../api/endpoints";
import { StatusBadge } from "../../components/badges";
import { ErrorAlert, PageLoader } from "../../components/common";
import { GRADE_COLORS } from "../../shared/dictionaries";
import { formatDateTime, formatMoney, formatMonths } from "../../shared/format";

const FILTERS = [
  { value: "manual_review", label: "Ручное рассмотрение" },
  { value: "all", label: "Все" },
  { value: "checking", label: "На проверке" },
  { value: "info_requested", label: "Дозапрос" },
  { value: "offer", label: "Предложение" },
  { value: "issued", label: "Выдано" },
  { value: "rejected", label: "Отказ" },
];

export function QueuePage() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState("manual_review");
  const status = filter === "all" ? undefined : filter;
  const queue = useQuery({
    queryKey: ["analyst-queue", filter],
    queryFn: () => Api.analystQueue(status),
    refetchInterval: 5000,
  });

  return (
    <Stack>
      <div>
        <Title order={2}>Очередь заявок</Title>
        <Text c="dimmed">
          В «Ручном рассмотрении» — заявки, по которым нужно ваше решение. Черновики не
          показываются.
        </Text>
      </div>
      <ScrollArea type="never">
        <SegmentedControl value={filter} onChange={setFilter} data={FILTERS} />
      </ScrollArea>
      <ErrorAlert error={queue.error} />
      {queue.isPending ? (
        <PageLoader />
      ) : queue.data?.length ? (
        <Card withBorder p={0}>
          <Table highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>№</Table.Th>
                <Table.Th>Компания</Table.Th>
                <Table.Th>Продукт</Table.Th>
                <Table.Th ta="right">Сумма</Table.Th>
                <Table.Th>Срок</Table.Th>
                <Table.Th>Оценка</Table.Th>
                <Table.Th>Статус</Table.Th>
                <Table.Th>Изменена</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {queue.data.map((item) => (
                <Table.Tr
                  key={item.id}
                  onClick={() => navigate(`/analyst/applications/${item.id}`)}
                  style={{ cursor: "pointer" }}
                >
                  <Table.Td>{item.id}</Table.Td>
                  <Table.Td>
                    <Text size="sm">{item.company_name}</Text>
                    <Text size="xs" c="dimmed">
                      ИНН {item.company_inn}
                    </Text>
                  </Table.Td>
                  <Table.Td>{item.product_name}</Table.Td>
                  <Table.Td ta="right">{formatMoney(item.amount)}</Table.Td>
                  <Table.Td>{formatMonths(item.term_months)}</Table.Td>
                  <Table.Td>
                    {item.grade ? (
                      <Group gap={6} wrap="nowrap">
                        <Badge color={GRADE_COLORS[item.grade] ?? "gray"}>{item.grade}</Badge>
                        <Text size="xs" c="dimmed">
                          {item.score} б.
                        </Text>
                      </Group>
                    ) : (
                      <Text size="xs" c="dimmed">
                        —
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <StatusBadge status={item.status} />
                  </Table.Td>
                  <Table.Td>{formatDateTime(item.status_changed_at)}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      ) : (
        <Card withBorder padding="xl">
          <Text c="dimmed" ta="center">
            Заявок в этом статусе нет. Войдите как «Зелёная веранда» (demo-manual) и отправьте
            заявку — она появится в ручном рассмотрении.
          </Text>
        </Card>
      )}
    </Stack>
  );
}
