import { Card, Group, SimpleGrid, Text, Title } from "@mantine/core";

import type { Schemas } from "../api/client";
import { averageTurnover, formatDate, formatMoney } from "../shared/format";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text size="sm">{value}</Text>
    </div>
  );
}

/** Данные компании, которые банк уже знает: клиенту их вводить не нужно. */
export function CompanyCard({
  company,
  note = "Эти данные банк уже знает — вводить их не нужно.",
}: {
  company: Schemas["Company"];
  note?: string;
}) {
  return (
    <Card withBorder>
      <Group justify="space-between" mb="xs">
        <Title order={4}>{company.name}</Title>
        <Text size="xs" c="dimmed">
          {note}
        </Text>
      </Group>
      <SimpleGrid cols={{ base: 2, md: 4 }} spacing="sm">
        <Field label="ИНН" value={company.inn} />
        <Field label={company.kind === "ip" ? "ОГРНИП" : "ОГРН"} value={company.ogrn} />
        <Field label="Дата регистрации" value={formatDate(company.registered_at)} />
        <Field label="Регион" value={company.region} />
        <Field label="ОКВЭД" value={`${company.okved} — ${company.okved_name}`} />
        <Field label="Руководитель" value={company.director_name} />
        <Field
          label="Средний оборот по счёту в месяц"
          value={formatMoney(averageTurnover(company.monthly_turnover))}
        />
      </SimpleGrid>
    </Card>
  );
}
