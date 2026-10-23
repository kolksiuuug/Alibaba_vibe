import {
  Alert,
  Anchor,
  Badge,
  Card,
  Grid,
  Group,
  List,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import type { Schemas } from "../../api/client";
import { Api } from "../../api/endpoints";
import { StatusBadge } from "../../components/badges";
import { CompanyCard } from "../../components/CompanyCard";
import { ErrorAlert, PageLoader } from "../../components/common";
import { EventsTimeline } from "../../components/EventsTimeline";
import { FactorTable } from "../../components/FactorList";
import { PipelineSteps } from "../../components/PipelineSteps";
import {
  CHECK_SOURCES,
  FORM_FIELDS,
  GRADE_COLORS,
  OUTCOME_LABELS,
  purposeLabel,
} from "../../shared/dictionaries";
import {
  formatDate,
  formatDateTime,
  formatMoney,
  formatMoneyExact,
  formatMonths,
  formatRate,
} from "../../shared/format";
import { POLL_INTERVAL_MS, POLLING_STATUSES, statusInfo } from "../../shared/statuses";
import { DecisionPanel } from "./DecisionPanel";

const CHECK_FIELDS: Record<string, string> = {
  status: "Статус",
  registered_at: "Дата регистрации",
  okved: "ОКВЭД",
  tax_debt: "Налоговая задолженность",
  late_payments_12m: "Опозданий с налогами за 12 мес.",
  tax_regime: "Режим налогообложения",
  employees: "Сотрудников",
  active_loans: "Действующих кредитов",
  monthly_payments: "Платежи по кредитам в месяц",
  current_overdue_days: "Текущая просрочка, дн.",
  max_overdue_days_24m: "Макс. просрочка за 24 мес., дн.",
  overdue_count_24m: "Число просрочек за 24 мес.",
};
const COMPANY_STATUSES: Record<string, string> = {
  active: "действует",
  liquidating: "ликвидация",
  liquidated: "ликвидирована",
  bankrupt: "банкротство",
};
const MONEY_FIELDS = new Set(["tax_debt", "monthly_payments"]);

function formatCheckValue(key: string, value: unknown): string {
  if (key === "status") return COMPANY_STATUSES[String(value)] ?? String(value);
  if (key === "registered_at") return formatDate(String(value));
  if (MONEY_FIELDS.has(key)) return formatMoney(Number(value));
  return String(value);
}

function ChecksPanel({ checks }: { checks: Schemas["Check"][] }) {
  if (checks.length === 0) {
    return (
      <Text size="sm" c="dimmed">
        Проверки ещё не выполнялись.
      </Text>
    );
  }
  return (
    <SimpleGrid cols={{ base: 1, md: 3 }}>
      {checks.map((check) => (
        <Card key={check.source} withBorder>
          <Group justify="space-between" mb="xs">
            <Text fw={600} size="sm">
              {CHECK_SOURCES[check.source] ?? check.source}
            </Text>
            <Badge color={check.status === "ok" ? "green" : "red"} variant="light">
              {check.status === "ok" ? "получено" : "нет ответа"}
            </Badge>
          </Group>
          {check.error && (
            <Text size="xs" c="red">
              {check.error}
            </Text>
          )}
          <Stack gap={2}>
            {Object.entries(check.response ?? {})
              .filter(([key]) => key in CHECK_FIELDS)
              .map(([key, value]) => (
                <Group key={key} justify="space-between" gap="xs" wrap="nowrap">
                  <Text size="xs" c="dimmed">
                    {CHECK_FIELDS[key]}
                  </Text>
                  <Text size="xs" fw={500} ta="right">
                    {formatCheckValue(key, value)}
                  </Text>
                </Group>
              ))}
          </Stack>
        </Card>
      ))}
    </SimpleGrid>
  );
}

function DecisionsTable({ decisions }: { decisions: Schemas["Decision"][] }) {
  return (
    <Table verticalSpacing={4} fz="sm">
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Когда</Table.Th>
          <Table.Th>Кто</Table.Th>
          <Table.Th>Итог</Table.Th>
          <Table.Th>Условия</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {decisions.map((decision) => (
          <Table.Tr key={decision.id}>
            <Table.Td>{formatDateTime(decision.created_at)}</Table.Td>
            <Table.Td>{decision.decided_by === "engine" ? "Движок" : "Аналитик"}</Table.Td>
            <Table.Td>
              {OUTCOME_LABELS[decision.outcome] ?? decision.outcome}
              {decision.is_counter && " (контр.)"}
            </Table.Td>
            <Table.Td>
              {decision.amount
                ? `${formatMoney(decision.amount)}, ${formatMonths(decision.term_months ?? 0)}, ${formatRate(decision.rate)}`
                : "—"}
            </Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}

export function CardPage() {
  const id = Number(useParams().id);
  const query = useQuery({
    queryKey: ["analyst-card", id],
    queryFn: () => Api.analystCard(id),
    refetchInterval: (q) =>
      POLLING_STATUSES.has(q.state.data?.application.status ?? "") ? POLL_INTERVAL_MS : false,
  });

  if (query.isPending) return <PageLoader />;
  if (query.isError) return <ErrorAlert error={query.error} title="Карточка не открылась" />;

  const card = query.data;
  const application = card.application;
  const scoring = card.scoring;
  const engineDecisions = card.decisions.filter((d) => d.decided_by === "engine");
  const recommendation = [...engineDecisions].reverse().find((d) => d.amount);
  const lastEngine = engineDecisions[engineDecisions.length - 1];
  const formEntries = Object.entries(application.form_data).filter(
    ([, value]) => value != null && value !== "",
  );

  return (
    <Stack>
      <Group justify="space-between" align="flex-start">
        <div>
          <Text size="sm" c="dimmed">
            <Anchor component={Link} to="/analyst">
              Очередь заявок
            </Anchor>{" "}
            / Заявка №{application.id}
          </Text>
          <Title order={2}>{application.company.name}</Title>
          <Text c="dimmed">
            {application.product.name}: {formatMoney(application.amount)} на{" "}
            {formatMonths(application.term_months)} · {purposeLabel(application.purpose)}
          </Text>
        </div>
        <StatusBadge status={application.status} size="lg" testId="application-status" />
      </Group>
      <Alert color={statusInfo(application.status).color}>
        {statusInfo(application.status).analyst}
      </Alert>

      <Grid>
        <Grid.Col span={{ base: 12, lg: 8 }}>
          <Stack>
            <Card withBorder padding="lg">
              <Group justify="space-between" mb="sm">
                <Title order={4}>Скоринг</Title>
                {scoring?.grade && (
                  <Group gap="xs">
                    <Text fw={700} size="xl">
                      {scoring.score} баллов
                    </Text>
                    <Badge size="xl" color={GRADE_COLORS[scoring.grade] ?? "gray"}>
                      {scoring.grade}
                    </Badge>
                  </Group>
                )}
              </Group>
              {scoring?.stop_factors.length ? (
                <Alert color="red" title="Сработали стоп-факторы" mb="sm">
                  <List size="sm">
                    {scoring.stop_factors.map((stop) => (
                      <List.Item key={stop.code}>{stop.text}</List.Item>
                    ))}
                  </List>
                </Alert>
              ) : null}
              {scoring?.factors.length ? (
                <FactorTable factors={scoring.factors} />
              ) : (
                !scoring?.stop_factors.length && (
                  <Text size="sm" c="dimmed">
                    Скоринг ещё не рассчитан.
                  </Text>
                )
              )}
            </Card>

            <Card withBorder padding="lg">
              <Title order={4} mb="sm">
                Проверки во внешних системах
              </Title>
              <ChecksPanel checks={card.checks} />
            </Card>

            <CompanyCard company={application.company} note="Синтетические данные" />

            <Card withBorder padding="lg">
              <Title order={4} mb="sm">
                Обороты по расчётному счёту
              </Title>
              <SimpleGrid cols={{ base: 3, md: 6 }} spacing="xs">
                {application.company.monthly_turnover.map((month) => (
                  <div key={month.month}>
                    <Text size="xs" c="dimmed">
                      {month.month}
                    </Text>
                    <Text size="sm">{formatMoney(month.amount)}</Text>
                  </div>
                ))}
              </SimpleGrid>
            </Card>

            <Card withBorder padding="lg">
              <Title order={4} mb="sm">
                Анкета клиента
              </Title>
              {formEntries.length ? (
                <Stack gap={4}>
                  {formEntries.map(([key, value]) => (
                    <Group key={key} gap="xs" align="flex-start" wrap="nowrap">
                      <Text size="sm" c="dimmed" w={260}>
                        {FORM_FIELDS[key]?.label ?? key}
                      </Text>
                      <Text size="sm">{String(value)}</Text>
                    </Group>
                  ))}
                </Stack>
              ) : (
                <Text size="sm" c="dimmed">
                  Анкета пустая.
                </Text>
              )}
            </Card>
          </Stack>
        </Grid.Col>

        <Grid.Col span={{ base: 12, lg: 4 }}>
          <Stack>
            {application.status === "manual_review" && (
              <DecisionPanel
                key={application.status_changed_at}
                card={card}
                recommendation={recommendation}
              />
            )}
            <Card withBorder padding="lg">
              <Title order={4} mb="sm">
                Рекомендация движка
              </Title>
              {lastEngine ? (
                <Stack gap="xs">
                  <Text size="sm">
                    Итог: <b>{OUTCOME_LABELS[lastEngine.outcome] ?? lastEngine.outcome}</b>
                  </Text>
                  {recommendation && (
                    <Text size="sm">
                      Условия: {formatMoney(recommendation.amount)} на{" "}
                      {formatMonths(recommendation.term_months ?? 0)}, ставка{" "}
                      {formatRate(recommendation.rate)}, платёж{" "}
                      {formatMoneyExact(recommendation.monthly_payment)}
                    </Text>
                  )}
                  <List size="sm">
                    {lastEngine.reasons.map((reason) => (
                      <List.Item key={reason.code}>{reason.text}</List.Item>
                    ))}
                  </List>
                </Stack>
              ) : (
                <Text size="sm" c="dimmed">
                  Движок ещё не принимал решение по этой заявке.
                </Text>
              )}
            </Card>
            {application.pipeline_steps.length > 0 && (
              <Card withBorder padding="lg">
                <Title order={4} mb="sm">
                  Этапы конвейера
                </Title>
                <PipelineSteps steps={application.pipeline_steps} />
              </Card>
            )}
            {card.decisions.length > 0 && (
              <Card withBorder padding="lg">
                <Title order={4} mb="sm">
                  Решения
                </Title>
                <DecisionsTable decisions={card.decisions} />
              </Card>
            )}
            {card.info_requests.length > 0 && (
              <Card withBorder padding="lg">
                <Title order={4} mb="sm">
                  Дозапросы
                </Title>
                <Stack gap="sm">
                  {card.info_requests.map((request) => (
                    <div key={request.id}>
                      <Text size="sm">{request.message}</Text>
                      <Text size="xs" c="dimmed">
                        {request.requested_by === "engine" ? "Движок" : "Аналитик"},{" "}
                        {formatDateTime(request.created_at)} ·{" "}
                        {request.responded_at
                          ? `ответ ${formatDateTime(request.responded_at)}`
                          : "ждём ответ"}
                      </Text>
                    </div>
                  ))}
                </Stack>
              </Card>
            )}
            <Card withBorder padding="lg">
              <Title order={4} mb="sm">
                Журнал переходов
              </Title>
              <EventsTimeline events={card.events} showCodes />
            </Card>
          </Stack>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
