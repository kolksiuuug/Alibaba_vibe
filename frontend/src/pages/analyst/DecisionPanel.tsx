import {
  Alert,
  Button,
  Card,
  MultiSelect,
  NumberInput,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { fieldError, type Schemas } from "../../api/client";
import { Api } from "../../api/endpoints";
import { ErrorAlert } from "../../components/common";
import {
  DECISION_ACTIONS,
  REQUESTABLE_FIELDS,
  type DecisionAction,
} from "../../shared/dictionaries";
import { formatMoney, formatMonths, formatRate } from "../../shared/format";

const ACTION_COLORS: Record<DecisionAction, string> = {
  approve: "green",
  change_terms: "teal",
  request_info: "orange",
  reject: "red",
};

/** Решение по ручному рассмотрению; комментарий обязателен для любого действия. */
export function DecisionPanel({
  card,
  recommendation,
}: {
  card: Schemas["AnalystCard"];
  recommendation: Schemas["Decision"] | undefined;
}) {
  const application = card.application;
  const queryClient = useQueryClient();
  const [action, setAction] = useState<DecisionAction>("approve");
  const [amount, setAmount] = useState<number>(recommendation?.amount ?? application.amount);
  const [term, setTerm] = useState<number>(recommendation?.term_months ?? application.term_months);
  const [fields, setFields] = useState<string[]>([]);
  const [comment, setComment] = useState("");

  const decide = useMutation({
    mutationFn: () =>
      Api.analystDecision(application.id, {
        action,
        comment: comment.trim() || null,
        ...(action === "change_terms" ? { amount, term_months: term } : {}),
        ...(action === "request_info" ? { fields } : {}),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["analyst-card", application.id], data);
      void queryClient.invalidateQueries({ queryKey: ["analyst-queue"] });
    },
  });

  const hint: Record<DecisionAction, string> = {
    approve: recommendation?.amount
      ? `Клиент получит предложение по рекомендации движка: ${formatMoney(recommendation.amount)} на ${formatMonths(recommendation.term_months ?? 0)}, ставка ${formatRate(recommendation.rate)}.`
      : "Клиент получит предложение на запрошенных условиях.",
    change_terms:
      "Укажите сумму и срок, которые готовы предложить. Ставка — по рекомендации движка.",
    request_info: "Комментарий станет текстом дозапроса для клиента. Можно отметить поля анкеты.",
    reject: "Клиент увидит отказ и ваш комментарий.",
  };

  return (
    <Card withBorder padding="lg">
      <Stack>
        <Title order={4}>Решение по заявке</Title>
        <SegmentedControl
          value={action}
          onChange={(value) => setAction(value as DecisionAction)}
          data={DECISION_ACTIONS.map((item) => ({ value: item.value, label: item.label }))}
          fullWidth
          orientation="vertical"
        />
        <Text size="sm" c="dimmed">
          {hint[action]}
        </Text>
        {action === "change_terms" && (
          <SimpleGrid cols={2}>
            <NumberInput
              label="Сумма, ₽"
              value={amount}
              onChange={(value) => setAmount(Number(value) || 0)}
              thousandSeparator=" "
              allowDecimal={false}
              error={fieldError(decide.error, "amount")}
            />
            <NumberInput
              label="Срок, месяцев"
              value={term}
              onChange={(value) => setTerm(Number(value) || 0)}
              allowDecimal={false}
              error={fieldError(decide.error, "term_months")}
            />
          </SimpleGrid>
        )}
        {action === "request_info" && (
          <MultiSelect
            label="Какие поля анкеты заполнить клиенту"
            placeholder="Можно не выбирать — тогда клиент ответит текстом"
            data={REQUESTABLE_FIELDS}
            value={fields}
            onChange={setFields}
            clearable
          />
        )}
        <Textarea
          label="Комментарий"
          description="Обязателен для любого решения и попадает в журнал"
          withAsterisk
          autosize
          minRows={3}
          value={comment}
          onChange={(event) => setComment(event.currentTarget.value)}
        />
        {decide.error ? <ErrorAlert error={decide.error} /> : null}
        {decide.isSuccess && (
          <Alert color="green">Решение сохранено, клиент получил уведомление.</Alert>
        )}
        <Button
          color={ACTION_COLORS[action]}
          onClick={() => decide.mutate()}
          loading={decide.isPending}
          disabled={!comment.trim()}
        >
          {DECISION_ACTIONS.find((item) => item.value === action)?.label}
        </Button>
      </Stack>
    </Card>
  );
}
