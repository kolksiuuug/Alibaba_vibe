import {
  Alert,
  Button,
  Card,
  Group,
  NumberInput,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { IconInfoCircle } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { fieldError, type Schemas } from "../../../api/client";
import { Api } from "../../../api/endpoints";
import { CompanyCard } from "../../../components/CompanyCard";
import { ErrorAlert } from "../../../components/common";
import { FORM_FIELDS } from "../../../shared/dictionaries";
import { formatMoney, formatMonths } from "../../../shared/format";

const REQUIRED = ["contact_name", "purpose_description"];

function toStrings(form: Record<string, unknown>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(form).map(([key, value]) => [key, value == null ? "" : String(value)]),
  );
}

/** Пустое поле -> null (очистить), числа — без пробелов. */
function toPayload(form: Record<string, string>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(form).map(([key, value]) => {
      const trimmed = value.trim();
      if (!trimmed) return [key, null];
      return [key, FORM_FIELDS[key]?.numeric ? Number(trimmed.replace(/\s/g, "")) : trimmed];
    }),
  );
}

export function DraftForm({ detail }: { detail: Schemas["ApplicationDetail"] }) {
  const application = detail.application;
  const queryClient = useQueryClient();
  const products = useQuery({ queryKey: ["products"], queryFn: Api.products, staleTime: 60_000 });
  const product = products.data?.find((item) => item.code === application.product.code);

  const [amount, setAmount] = useState<number>(application.amount);
  const [term, setTerm] = useState<number>(application.term_months);
  const [form, setForm] = useState<Record<string, string>>(() => toStrings(application.form_data));
  const [saved, setSaved] = useState(false);

  const update = () =>
    Api.updateApplication(application.id, {
      amount,
      term_months: term,
      form_data: toPayload(form),
    });
  const refresh = (data: Schemas["ApplicationDetail"]) => {
    queryClient.setQueryData(["application", application.id], data);
    void queryClient.invalidateQueries({ queryKey: ["applications"] });
  };

  const save = useMutation({
    mutationFn: update,
    onSuccess: (data) => {
      refresh(data);
      setSaved(true);
    },
  });
  const submit = useMutation({
    mutationFn: async () => {
      await update();
      return Api.submit(application.id);
    },
    onSuccess: refresh,
  });
  const cancel = useMutation({ mutationFn: () => Api.cancel(application.id), onSuccess: refresh });
  const error = save.error ?? submit.error ?? cancel.error;

  const setField = (code: string, value: string) => {
    setSaved(false);
    setForm((current) => ({ ...current, [code]: value }));
  };
  const missing = REQUIRED.filter((code) => !form[code]?.trim());
  const productFields = product?.required_fields ?? [];

  function input(code: string) {
    const meta = FORM_FIELDS[code] ?? { label: code };
    const props = {
      label: meta.label,
      description: meta.hint,
      value: form[code] ?? "",
      error: fieldError(error, "form_data", code),
      withAsterisk: REQUIRED.includes(code),
    };
    if (code === "purpose_description") {
      return (
        <Textarea
          key={code}
          {...props}
          autosize
          minRows={2}
          onChange={(event) => setField(code, event.currentTarget.value)}
        />
      );
    }
    if (meta.numeric) {
      return (
        <NumberInput
          key={code}
          {...props}
          thousandSeparator=" "
          allowDecimal={false}
          onChange={(value) => setField(code, String(value))}
        />
      );
    }
    return (
      <TextInput
        key={code}
        {...props}
        onChange={(event) => setField(code, event.currentTarget.value)}
      />
    );
  }

  return (
    <Stack>
      <CompanyCard company={application.company} />

      <Card withBorder padding="lg">
        <Title order={4} mb="sm">
          Условия
        </Title>
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <NumberInput
            label="Сумма, ₽"
            value={amount}
            onChange={(value) => {
              setSaved(false);
              setAmount(Number(value) || 0);
            }}
            thousandSeparator=" "
            allowDecimal={false}
            min={product?.min_amount}
            max={product?.max_amount}
            description={
              product &&
              `от ${formatMoney(product.min_amount)} до ${formatMoney(product.max_amount)}`
            }
            error={fieldError(error, "amount")}
          />
          <NumberInput
            label="Срок, месяцев"
            value={term}
            onChange={(value) => {
              setSaved(false);
              setTerm(Number(value) || 0);
            }}
            allowDecimal={false}
            min={product?.min_term_months}
            max={product?.max_term_months}
            description={
              product &&
              `от ${formatMonths(product.min_term_months)} до ${formatMonths(product.max_term_months)}`
            }
            error={fieldError(error, "term_months")}
          />
        </SimpleGrid>
      </Card>

      <Card withBorder padding="lg">
        <Title order={4} mb="sm">
          Анкета
        </Title>
        <Stack>
          {REQUIRED.map(input)}
          {productFields.length > 0 && (
            <>
              <Alert color="blue" icon={<IconInfoCircle size={18} />} mt="sm">
                Для продукта «{application.product.name}» банку понадобятся данные ниже. Их можно
                заполнить сейчас или позже — тогда банк пришлёт дозапрос.
              </Alert>
              {productFields.map((field) => input(field.code))}
            </>
          )}
        </Stack>
      </Card>

      <ErrorAlert error={error} />
      {missing.length > 0 && (
        <Text size="sm" c="dimmed">
          Чтобы отправить заявку, заполните:{" "}
          {missing.map((code) => FORM_FIELDS[code].label.toLowerCase()).join(", ")}.
        </Text>
      )}
      <Group>
        <Button
          onClick={() => submit.mutate()}
          loading={submit.isPending}
          disabled={missing.length > 0}
        >
          Отправить заявку
        </Button>
        <Button variant="default" onClick={() => save.mutate()} loading={save.isPending}>
          Сохранить черновик
        </Button>
        <Button
          variant="subtle"
          color="gray"
          onClick={() => cancel.mutate()}
          loading={cancel.isPending}
        >
          Отменить заявку
        </Button>
        {saved && (
          <Text size="sm" c="green">
            Черновик сохранён
          </Text>
        )}
      </Group>
    </Stack>
  );
}
