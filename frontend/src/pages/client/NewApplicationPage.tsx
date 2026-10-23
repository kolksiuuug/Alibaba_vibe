import {
  Badge,
  Button,
  Card,
  Group,
  List,
  NumberInput,
  Radio,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import type { Schemas } from "../../api/client";
import { Api } from "../../api/endpoints";
import { ErrorAlert } from "../../components/common";
import { PURPOSES, type PurposeCode } from "../../shared/dictionaries";
import { formatMoney, formatMonths, formatRate } from "../../shared/format";

export function NewApplicationPage() {
  const navigate = useNavigate();
  const [purpose, setPurpose] = useState<PurposeCode>("working_capital");
  const [amount, setAmount] = useState<number>(3_000_000);
  const [term, setTerm] = useState<number>(24);

  const recommend = useMutation({
    mutationFn: () => Api.recommend({ purpose, amount, term_months: term }),
  });
  const create = useMutation({
    mutationFn: (item: Schemas["Recommendation"]) =>
      Api.createApplication({
        product_code: item.product.code,
        amount: item.amount,
        term_months: item.term_months,
        purpose,
        form_data: {},
      }),
    onSuccess: (detail) => navigate(`/applications/${detail.application.id}`),
  });

  return (
    <Stack>
      <div>
        <Title order={2}>Подбор кредита</Title>
        <Text c="dimmed">
          Расскажите, на что нужны деньги, — покажем до трёх подходящих продуктов с примерным
          платежом.
        </Text>
      </div>

      <Card withBorder padding="lg">
        <Stack>
          <Radio.Group
            label="Цель кредита"
            value={purpose}
            onChange={(value) => setPurpose(value as PurposeCode)}
          >
            <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} mt="xs">
              {PURPOSES.map((item) => (
                <Radio.Card key={item.value} value={item.value} p="md" radius="md">
                  <Group wrap="nowrap" align="flex-start">
                    <Radio.Indicator />
                    <Text size="sm">{item.label}</Text>
                  </Group>
                </Radio.Card>
              ))}
            </SimpleGrid>
          </Radio.Group>
          <Group grow align="flex-start">
            <NumberInput
              label="Сумма, ₽"
              value={amount}
              onChange={(value) => setAmount(Number(value) || 0)}
              min={100_000}
              step={100_000}
              thousandSeparator=" "
              allowDecimal={false}
            />
            <NumberInput
              label="Срок, месяцев"
              value={term}
              onChange={(value) => setTerm(Number(value) || 0)}
              min={1}
              max={120}
              allowDecimal={false}
            />
          </Group>
          <Group>
            <Button onClick={() => recommend.mutate()} loading={recommend.isPending}>
              Подобрать
            </Button>
          </Group>
        </Stack>
      </Card>

      <ErrorAlert error={recommend.error || create.error} />

      {recommend.data && (
        <Stack>
          <Text size="sm" c="dimmed">
            Ставка предварительная — «от». Точные условия банк предложит после проверки заявки.
          </Text>
          <SimpleGrid cols={{ base: 1, md: 3 }}>
            {recommend.data.map((item) => (
              <Card key={item.product.code} withBorder padding="lg">
                <Stack gap="xs" h="100%" justify="space-between">
                  <div>
                    <Group justify="space-between" align="flex-start" wrap="nowrap">
                      <Title order={4}>{item.product.name}</Title>
                      {item.fits ? (
                        <Badge color="green" variant="light">
                          подходит
                        </Badge>
                      ) : (
                        <Badge color="yellow" variant="light">
                          условия скорректированы
                        </Badge>
                      )}
                    </Group>
                    <Text size="sm" c="dimmed" mt={4}>
                      {item.product.description}
                    </Text>
                    <SimpleGrid cols={2} mt="md" spacing="xs">
                      <div>
                        <Text size="xs" c="dimmed">
                          Ставка
                        </Text>
                        <Text fw={700}>от {formatRate(item.rate)}</Text>
                      </div>
                      <div>
                        <Text size="xs" c="dimmed">
                          Платёж в месяц
                        </Text>
                        <Text fw={700}>≈ {formatMoney(item.monthly_payment)}</Text>
                      </div>
                      <div>
                        <Text size="xs" c="dimmed">
                          Сумма
                        </Text>
                        <Text>{formatMoney(item.amount)}</Text>
                      </div>
                      <div>
                        <Text size="xs" c="dimmed">
                          Срок
                        </Text>
                        <Text>{formatMonths(item.term_months)}</Text>
                      </div>
                    </SimpleGrid>
                    {item.notes.length > 0 && (
                      <List size="sm" mt="sm" spacing={4}>
                        {item.notes.map((note) => (
                          <List.Item key={note}>{note}</List.Item>
                        ))}
                      </List>
                    )}
                  </div>
                  <Button
                    onClick={() => create.mutate(item)}
                    loading={
                      create.isPending && create.variables?.product.code === item.product.code
                    }
                    fullWidth
                  >
                    Оформить заявку
                  </Button>
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
        </Stack>
      )}
    </Stack>
  );
}
