import { Badge, Tooltip } from "@mantine/core";

import { statusInfo } from "../shared/statuses";

export function StatusBadge({
  status,
  size = "md",
  testId,
}: {
  status: string;
  size?: "sm" | "md" | "lg";
  testId?: string;
}) {
  const info = statusInfo(status);
  return (
    <Badge color={info.color} size={size} variant="light" data-testid={testId} data-status={status}>
      {info.label}
    </Badge>
  );
}

/** Плашка у смоделированных шагов: подпись и выдача (CLAUDE.md, раздел 12). */
export function SimulationBadge() {
  return (
    <Tooltip label="В прототипе этот шаг смоделирован: реальные системы банка не вызываются">
      <Badge color="yellow" variant="filled">
        Симуляция
      </Badge>
    </Tooltip>
  );
}
