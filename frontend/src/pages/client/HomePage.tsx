import { Button, Card, Group, Stack, Table, Text, Title } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { Api } from "../../api/endpoints";
import { useAuth } from "../../auth/AuthContext";
import { StatusBadge } from "../../components/badges";
import { CompanyCard } from "../../components/CompanyCard";
import { ErrorAlert, PageLoader } from "../../components/common";
import { formatDateTime, formatMoney, formatMonths } from "../../shared/format";

export function HomePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const applications = useQuery({
    queryKey: ["applications"],
    queryFn: Api.applications,
    refetchInterval: 5000,
  });

  return (
    <Stack>
      <Group justify="space-between">
        <div>
          <Title order={2}>Заявки компании</Title>
          <Text c="dimmed">Статусы обновляются сами. Нажмите на заявку, чтобы открыть её.</Text>
        </div>
        <Button component={Link} to="/new" leftSection={<IconPlus size={18} />}>
          Подобрать кредит
        </Button>
      </Group>

      {user?.company && <CompanyCard company={user.company} />}
      <ErrorAlert error={applications.error} />

      {applications.isPending ? (
        <PageLoader />
      ) : applications.data?.length ? (
        <Card withBorder p={0}>
          <Table highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>№</Table.Th>
                <Table.Th>Продукт</Table.Th>
                <Table.Th ta="right">Сумма</Table.Th>
                <Table.Th>Срок</Table.Th>
                <Table.Th>Статус</Table.Th>
                <Table.Th>Изменён</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {applications.data.map((item) => (
                <Table.Tr
                  key={item.id}
                  onClick={() => navigate(`/applications/${item.id}`)}
                  style={{ cursor: "pointer" }}
                >
                  <Table.Td>{item.id}</Table.Td>
                  <Table.Td>{item.product.name}</Table.Td>
                  <Table.Td ta="right">{formatMoney(item.amount)}</Table.Td>
                  <Table.Td>{formatMonths(item.term_months)}</Table.Td>
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
          <Stack align="center" gap="xs">
            <Title order={4}>Заявок пока нет</Title>
            <Text c="dimmed" ta="center">
              Подберите кредит под цель, сумму и срок — это займёт пару минут. Данные компании уже
              есть у банка.
            </Text>
            <Button component={Link} to="/new" mt="sm">
              Подобрать кредит
            </Button>
          </Stack>
        </Card>
      )}
    </Stack>
  );
}
