import { Alert, Button, Card, NumberInput, Stack, TextInput, Textarea, Title } from "@mantine/core";
import { IconMessageQuestion } from "@tabler/icons-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { fieldError, type Schemas } from "../../../api/client";
import { Api } from "../../../api/endpoints";
import { ErrorAlert } from "../../../components/common";
import { FORM_FIELDS } from "../../../shared/dictionaries";

/** Ответ на дозапрос банка: заполненные поля сразу отправляют заявку на повторную проверку. */
export function InfoRequestForm({ detail }: { detail: Schemas["ApplicationDetail"] }) {
  const application = detail.application;
  const request = detail.info_request;
  const queryClient = useQueryClient();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [comment, setComment] = useState("");

  const respond = useMutation({
    mutationFn: () =>
      Api.infoResponse(application.id, {
        answers: Object.fromEntries(
          Object.entries(answers).map(([code, value]) => [
            code,
            FORM_FIELDS[code]?.numeric ? Number(value.replace(/\s/g, "")) : value.trim(),
          ]),
        ),
        comment: comment.trim() || null,
      }),
    onSuccess: (data) => queryClient.setQueryData(["application", application.id], data),
  });

  if (!request) return null;
  const fields = request.fields;
  const filled = fields.every((field) => answers[field.code]?.trim());
  const ready = fields.length > 0 ? filled : comment.trim().length > 0;

  return (
    <Card withBorder padding="lg">
      <Stack>
        <Title order={4}>Запрос банка</Title>
        <Alert color="orange" icon={<IconMessageQuestion size={18} />}>
          {request.message}
        </Alert>
        {fields.map((field) => {
          const meta = FORM_FIELDS[field.code];
          const common = {
            key: field.code,
            label: meta?.label ?? field.label,
            description: meta?.hint,
            withAsterisk: true,
            error: fieldError(respond.error, "answers", field.code),
          };
          return meta?.numeric ? (
            <NumberInput
              {...common}
              thousandSeparator=" "
              allowDecimal={false}
              value={answers[field.code] ?? ""}
              onChange={(value) =>
                setAnswers((current) => ({ ...current, [field.code]: String(value) }))
              }
            />
          ) : (
            <TextInput
              {...common}
              value={answers[field.code] ?? ""}
              onChange={(event) => {
                const value = event.currentTarget.value;
                setAnswers((current) => ({ ...current, [field.code]: value }));
              }}
            />
          );
        })}
        <Textarea
          label={fields.length > 0 ? "Комментарий для банка (необязательно)" : "Ваш ответ"}
          withAsterisk={fields.length === 0}
          autosize
          minRows={2}
          value={comment}
          onChange={(event) => setComment(event.currentTarget.value)}
          error={fieldError(respond.error, "comment")}
        />
        <ErrorAlert error={respond.error} />
        <Button onClick={() => respond.mutate()} loading={respond.isPending} disabled={!ready}>
          Отправить ответ
        </Button>
      </Stack>
    </Card>
  );
}
