import { Alert, Button, Card, Code, Group, PinInput, Stack, Text, Title } from "@mantine/core";
import { IconSignature } from "@tabler/icons-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { Schemas } from "../../../api/client";
import { Api } from "../../../api/endpoints";
import { SimulationBadge } from "../../../components/badges";
import { ErrorAlert } from "../../../components/common";
import { formatDateTime } from "../../../shared/format";
import { OfferSummary } from "./OfferPanel";

/** Подписание договора кодом, который показывается и вводится здесь же (симуляция ЭП). */
export function SignPanel({ detail }: { detail: Schemas["ApplicationDetail"] }) {
  const application = detail.application;
  const queryClient = useQueryClient();
  const [code, setCode] = useState("");
  const requestCode = useMutation({ mutationFn: () => Api.requestSignCode(application.id) });
  const confirm = useMutation({
    mutationFn: () => Api.confirmSign(application.id, code),
    onSuccess: (data) => queryClient.setQueryData(["application", application.id], data),
  });

  return (
    <Stack>
      <Card withBorder padding="lg">
        <Stack>
          <Group justify="space-between">
            <Group gap="xs">
              <IconSignature size={22} />
              <Title order={4}>Подписание договора</Title>
            </Group>
            <SimulationBadge />
          </Group>
          <Text size="sm">
            Договор подписывается одноразовым кодом. В прототипе код показывается прямо на этой
            странице — SMS и звонки не используются.
          </Text>
          {requestCode.data ? (
            <Alert color="yellow" title="Ваш код подписи">
              <Group gap="sm">
                <Code fz="xl" fw={700} data-testid="sign-code">
                  {requestCode.data.code}
                </Code>
                <Text size="xs" c="dimmed">
                  действует до {formatDateTime(requestCode.data.expires_at)}
                </Text>
              </Group>
            </Alert>
          ) : null}
          <Group align="flex-end">
            <Button
              variant={requestCode.data ? "default" : "filled"}
              onClick={() => requestCode.mutate()}
              loading={requestCode.isPending}
            >
              {requestCode.data ? "Получить новый код" : "Получить код"}
            </Button>
          </Group>
          {requestCode.data && (
            <Stack gap="xs">
              <Text size="sm" fw={500}>
                Введите код
              </Text>
              <PinInput length={6} type="number" value={code} onChange={setCode} oneTimeCode />
              <Group>
                <Button
                  onClick={() => confirm.mutate()}
                  loading={confirm.isPending}
                  disabled={code.length !== 6}
                >
                  Подписать договор
                </Button>
              </Group>
            </Stack>
          )}
          <ErrorAlert error={requestCode.error || confirm.error} />
        </Stack>
      </Card>
      {detail.offer && (
        <Card withBorder padding="lg">
          <Title order={5} mb="sm">
            Условия договора
          </Title>
          <OfferSummary offer={detail.offer} factors={[]} />
        </Card>
      )}
    </Stack>
  );
}
