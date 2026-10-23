import { Loader, Text, ThemeIcon, Timeline } from "@mantine/core";
import { IconCheck, IconClock, IconX } from "@tabler/icons-react";

import type { Schemas } from "../api/client";

const STATE_TEXT: Record<string, string> = {
  pending: "ожидает",
  running: "выполняется",
  done: "готово",
  failed: "не удалось",
};

function Bullet({ state }: { state: string }) {
  if (state === "done") {
    return (
      <ThemeIcon color="green" radius="xl" size={22}>
        <IconCheck size={14} />
      </ThemeIcon>
    );
  }
  if (state === "failed") {
    return (
      <ThemeIcon color="red" radius="xl" size={22}>
        <IconX size={14} />
      </ThemeIcon>
    );
  }
  if (state === "running") return <Loader size={18} />;
  return (
    <ThemeIcon color="gray" variant="light" radius="xl" size={22}>
      <IconClock size={14} />
    </ThemeIcon>
  );
}

/** Этапы автоматической проверки: валидация → ЕГРЮЛ → ФНС → БКИ → скоринг → решение. */
export function PipelineSteps({ steps }: { steps: Schemas["Step"][] }) {
  if (steps.length === 0) {
    return (
      <Text c="dimmed" size="sm">
        Проверка ещё не началась.
      </Text>
    );
  }
  const active = steps.findIndex((step) => step.state !== "done");
  return (
    <Timeline active={active === -1 ? steps.length : active - 1} bulletSize={22} lineWidth={2}>
      {steps.map((step) => (
        <Timeline.Item
          key={step.code}
          bullet={<Bullet state={step.state} />}
          title={step.title ?? step.code}
        >
          <Text size="sm" c={step.state === "failed" ? "red" : "dimmed"}>
            {step.message ?? STATE_TEXT[step.state] ?? step.state}
          </Text>
        </Timeline.Item>
      ))}
    </Timeline>
  );
}
