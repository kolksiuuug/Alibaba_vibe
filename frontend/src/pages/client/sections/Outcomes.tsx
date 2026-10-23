import {
  Alert,
  Button,
  Card,
  Group,
  List,
  Loader,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconCircleCheck, IconCircleX } from "@tabler/icons-react";
import { Link } from "react-router-dom";

import type { Schemas } from "../../../api/client";
import { SimulationBadge } from "../../../components/badges";
import { ClientFactors } from "../../../components/FactorList";
import { PipelineSteps } from "../../../components/PipelineSteps";
import { formatDateTime, formatMoney } from "../../../shared/format";
import { OfferSummary } from "./OfferPanel";

type Detail = Schemas["ApplicationDetail"];

export function CheckingPanel({ detail }: { detail: Detail }) {
  return (
    <Card withBorder padding="lg">
      <Stack>
        <Group gap="sm">
          <Loader size="sm" />
          <Title order={4}>Идёт автоматическая проверка</Title>
        </Group>
        <Text size="sm" c="dimmed">
          Не закрывайте страницу — статус обновляется каждые 2 секунды.
        </Text>
        <PipelineSteps steps={detail.application.pipeline_steps} />
      </Stack>
    </Card>
  );
}

export function ManualReviewPanel({ detail }: { detail: Detail }) {
  return (
    <Card withBorder padding="lg">
      <Stack>
        <Title order={4}>Заявку рассматривает кредитный аналитик</Title>
        <Text size="sm">
          Автоматическая проверка не дала однозначного ответа, поэтому решение примет специалист.
          Ничего делать не нужно — ответ появится здесь и в уведомлениях.
        </Text>
        {detail.reasons.length > 0 && (
          <List size="sm">
            {detail.reasons.map((reason) => (
              <List.Item key={reason.code}>{reason.text}</List.Item>
            ))}
          </List>
        )}
        <ClientFactors factors={detail.factors} />
      </Stack>
    </Card>
  );
}

export function SignedPanel() {
  return (
    <Card withBorder padding="lg">
      <Group justify="space-between">
        <Group gap="sm">
          <Loader size="sm" />
          <Title order={4}>Договор подписан, выдаём деньги</Title>
        </Group>
        <SimulationBadge />
      </Group>
      <Text size="sm" mt="sm">
        Деньги поступят на расчётный счёт компании через несколько секунд.
      </Text>
    </Card>
  );
}

export function IssuedPanel({ detail }: { detail: Detail }) {
  return (
    <Stack>
      <Card withBorder padding="lg">
        <Stack>
          <Group justify="space-between">
            <Group gap="sm">
              <IconCircleCheck size={28} color="var(--mantine-color-green-6)" />
              <Title order={3}>Кредит выдан</Title>
            </Group>
            <SimulationBadge />
          </Group>
          {detail.disbursement && (
            <SimpleGrid cols={{ base: 1, sm: 3 }}>
              <div>
                <Text size="xs" c="dimmed">
                  Зачислено на счёт
                </Text>
                <Text fw={700} size="lg">
                  {formatMoney(detail.disbursement.amount)}
                </Text>
              </div>
              <div>
                <Text size="xs" c="dimmed">
                  Номер операции в АБС
                </Text>
                <Text>{detail.disbursement.abs_reference}</Text>
              </div>
              <div>
                <Text size="xs" c="dimmed">
                  Когда
                </Text>
                <Text>{formatDateTime(detail.disbursement.created_at)}</Text>
              </div>
            </SimpleGrid>
          )}
          {detail.signature && (
            <Text size="sm" c="dimmed">
              Договор подписан {formatDateTime(detail.signature.signed_at)}, подпись{" "}
              {detail.signature.signature_reference}.
            </Text>
          )}
        </Stack>
      </Card>
      {detail.offer && (
        <Card withBorder padding="lg">
          <Title order={5} mb="sm">
            Условия кредита
          </Title>
          <OfferSummary offer={detail.offer} factors={detail.factors} />
        </Card>
      )}
    </Stack>
  );
}

export function RejectedPanel({ detail }: { detail: Detail }) {
  return (
    <Card withBorder padding="lg">
      <Stack>
        <Group gap="sm">
          <IconCircleX size={28} color="var(--mantine-color-red-6)" />
          <Title order={3}>Банк не может выдать кредит</Title>
        </Group>
        {detail.reasons.length > 0 && (
          <Alert color="red" title="Причины">
            <List size="sm">
              {detail.reasons.map((reason) => (
                <List.Item key={reason.code}>{reason.text}</List.Item>
              ))}
            </List>
          </Alert>
        )}
        {detail.decision_comment && (
          <Alert color="violet" title="Комментарий кредитного аналитика">
            {detail.decision_comment}
          </Alert>
        )}
        {detail.factors.length > 0 && (
          <>
            <Title order={5}>Что повлияло на оценку</Title>
            <ClientFactors factors={detail.factors} />
          </>
        )}
        <Group>
          <Button component={Link} to="/new" variant="light">
            Подобрать другой кредит
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}

export function ClosedPanel({ text }: { text: string }) {
  return (
    <Card withBorder padding="lg">
      <Stack>
        <Text>{text}</Text>
        <Group>
          <Button component={Link} to="/new" variant="light">
            Подобрать кредит
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}
