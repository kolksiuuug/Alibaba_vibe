import {
  Accordion,
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconArrowsExchange } from "@tabler/icons-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { Schemas } from "../../../api/client";
import { Api } from "../../../api/endpoints";
import { ErrorAlert } from "../../../components/common";
import { ClientFactors } from "../../../components/FactorList";
import { ScheduleTable } from "../../../components/ScheduleTable";
import { formatMoney, formatMoneyExact, formatMonths, formatRate } from "../../../shared/format";

function Stat({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text fw={strong ? 700 : 500} size={strong ? "lg" : "md"}>
        {value}
      </Text>
    </div>
  );
}

/** Условия предложения, график, объяснение решения. */
export function OfferSummary({
  offer,
  factors,
}: {
  offer: Schemas["Offer"];
  factors: Schemas["Factor"][];
}) {
  return (
    <Stack>
      {offer.is_counter && (
        <Alert
          color="yellow"
          icon={<IconArrowsExchange size={18} />}
          title="Банк предлагает другие условия"
        >
          Вы просили {formatMoney(offer.requested_amount)} на{" "}
          {formatMonths(offer.requested_term_months)}{" "}
          {offer.reasons.map((reason) => reason.text).join(" ")}
        </Alert>
      )}
      {offer.decided_by === "analyst" && offer.comment && (
        <Alert color="violet" title="Комментарий кредитного аналитика">
          {offer.comment}
        </Alert>
      )}
      <SimpleGrid cols={{ base: 2, md: 3 }}>
        <Stat label="Сумма кредита" value={formatMoney(offer.amount)} strong />
        <Stat label="Ежемесячный платёж" value={formatMoneyExact(offer.monthly_payment)} strong />
        <Stat label="Ставка" value={formatRate(offer.rate)} strong />
        <Stat label="Срок" value={formatMonths(offer.term_months)} />
        <Stat label="Переплата" value={formatMoneyExact(offer.overpayment)} />
        <Stat label="Всего к выплате" value={formatMoneyExact(offer.total_payment)} />
      </SimpleGrid>
      <Accordion variant="contained">
        {factors.length > 0 && (
          <Accordion.Item value="factors">
            <Accordion.Control>Почему такое решение</Accordion.Control>
            <Accordion.Panel>
              <ClientFactors factors={factors} />
            </Accordion.Panel>
          </Accordion.Item>
        )}
        <Accordion.Item value="schedule">
          <Accordion.Control>График платежей ({offer.schedule.length} мес.)</Accordion.Control>
          <Accordion.Panel>
            <ScheduleTable rows={offer.schedule} />
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>
    </Stack>
  );
}

export function OfferPanel({ detail }: { detail: Schemas["ApplicationDetail"] }) {
  const application = detail.application;
  const queryClient = useQueryClient();
  const [confirmDecline, setConfirmDecline] = useState(false);
  const onSuccess = (data: Schemas["ApplicationDetail"]) =>
    queryClient.setQueryData(["application", application.id], data);
  const accept = useMutation({ mutationFn: () => Api.acceptOffer(application.id), onSuccess });
  const decline = useMutation({
    mutationFn: () => Api.declineOffer(application.id),
    onSuccess: (data) => (setConfirmDecline(false), onSuccess(data)),
  });

  if (!detail.offer) return null;
  return (
    <Card withBorder padding="lg">
      <Stack>
        <Group justify="space-between">
          <Title order={4}>Предложение банка</Title>
          {detail.offer.is_counter ? (
            <Badge color="yellow">Контрпредложение</Badge>
          ) : (
            <Badge color="green">Одобрено на ваших условиях</Badge>
          )}
        </Group>
        <OfferSummary offer={detail.offer} factors={detail.factors} />
        <ErrorAlert error={accept.error || decline.error} />
        <Group>
          <Button onClick={() => accept.mutate()} loading={accept.isPending}>
            Принять предложение
          </Button>
          <Button variant="outline" color="gray" onClick={() => setConfirmDecline(true)}>
            Отклонить
          </Button>
        </Group>
      </Stack>
      <Modal
        opened={confirmDecline}
        onClose={() => setConfirmDecline(false)}
        title="Отклонить предложение?"
      >
        <Text size="sm">Заявка закроется. Позже можно будет подать новую.</Text>
        <Group mt="md" justify="flex-end">
          <Button variant="default" onClick={() => setConfirmDecline(false)}>
            Вернуться
          </Button>
          <Button color="red" onClick={() => decline.mutate()} loading={decline.isPending}>
            Отклонить
          </Button>
        </Group>
      </Modal>
    </Card>
  );
}
