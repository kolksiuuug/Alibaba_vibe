import { Group, Progress, Stack, Table, Text, ThemeIcon } from "@mantine/core";
import { IconAlertTriangle, IconCircleCheck, IconInfoCircle } from "@tabler/icons-react";

import type { Schemas } from "../api/client";
import { FACTOR_LABELS } from "../shared/dictionaries";

function ImpactIcon({ impact }: { impact: string }) {
  if (impact === "positive") {
    return (
      <ThemeIcon color="green" variant="light" radius="xl">
        <IconCircleCheck size={18} />
      </ThemeIcon>
    );
  }
  if (impact === "negative") {
    return (
      <ThemeIcon color="orange" variant="light" radius="xl">
        <IconAlertTriangle size={18} />
      </ThemeIcon>
    );
  }
  return (
    <ThemeIcon color="gray" variant="light" radius="xl">
      <IconInfoCircle size={18} />
    </ThemeIcon>
  );
}

/** 3–5 главных факторов решения простыми словами — для клиента. */
export function ClientFactors({ factors }: { factors: Schemas["Factor"][] }) {
  if (factors.length === 0) return null;
  return (
    <Stack gap="sm">
      {factors.map((factor) => (
        <Group key={factor.code} align="flex-start" wrap="nowrap" gap="sm">
          <ImpactIcon impact={factor.impact} />
          <div>
            <Text size="sm" fw={600}>
              {FACTOR_LABELS[factor.code] ?? factor.code}
            </Text>
            <Text size="sm">{factor.explanation_ru}</Text>
          </div>
        </Group>
      ))}
    </Stack>
  );
}

/** Все факторы скоринга с баллами — для аналитика. */
export function FactorTable({ factors }: { factors: Schemas["Factor"][] }) {
  return (
    <Table striped verticalSpacing="xs">
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Фактор</Table.Th>
          <Table.Th w={160}>Баллы</Table.Th>
          <Table.Th>Объяснение</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {factors.map((factor) => {
          const share = Math.max(0, factor.points) / factor.max_points;
          return (
            <Table.Tr key={factor.code}>
              <Table.Td>
                <Group gap="xs" wrap="nowrap">
                  <ImpactIcon impact={factor.impact} />
                  <Text size="sm">{FACTOR_LABELS[factor.code] ?? factor.code}</Text>
                </Group>
              </Table.Td>
              <Table.Td>
                <Text size="sm" fw={600} c={factor.points < 0 ? "red" : undefined}>
                  {factor.points} из {factor.max_points}
                </Text>
                <Progress
                  value={share * 100}
                  size="sm"
                  color={share >= 0.75 ? "green" : share < 0.4 ? "orange" : "blue"}
                />
              </Table.Td>
              <Table.Td>
                <Text size="sm">{factor.explanation_ru}</Text>
              </Table.Td>
            </Table.Tr>
          );
        })}
      </Table.Tbody>
    </Table>
  );
}
