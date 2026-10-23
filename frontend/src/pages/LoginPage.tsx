import { Alert, Badge, Button, Card, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { IconInfoCircle } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { Api } from "../api/endpoints";
import { homePath, useAuth } from "../auth/AuthContext";
import { ErrorAlert, PageLoader } from "../components/common";
import { ROLE_LABELS } from "../shared/dictionaries";

export function LoginPage() {
  const { user, loginAs } = useAuth();
  const navigate = useNavigate();
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const profiles = useQuery({ queryKey: ["demo-profiles"], queryFn: Api.demoProfiles });

  if (user) return <Navigate to={homePath(user)} replace />;

  async function enter(login: string) {
    setPending(login);
    setError(null);
    try {
      const next = await loginAs(login);
      navigate(homePath(next));
    } catch (err) {
      setError(err);
    } finally {
      setPending(null);
    }
  }

  return (
    <Stack maw={1100} mx="auto">
      <div>
        <Title order={2}>Вход в демо-профиль</Title>
        <Text c="dimmed">
          Регистрация не нужна: предприниматель уже клиент банка, и его данные известны. Выберите
          компанию — у каждой свой сценарий проверки. Чтобы рассмотреть заявки, войдите как
          аналитик. Профиль можно сменить в любой момент в шапке.
        </Text>
      </div>
      <Alert color="gray" icon={<IconInfoCircle size={18} />}>
        Все компании, люди и ИНН вымышлены. Бюро кредитных историй, ЕГРЮЛ, ФНС, электронная подпись
        и выдача денег работают как моки.
      </Alert>
      <ErrorAlert error={error || profiles.error} />
      {profiles.isPending ? (
        <PageLoader />
      ) : (
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}>
          {profiles.data?.map((profile) => (
            <Card key={profile.login} withBorder padding="lg">
              <Stack gap="xs" h="100%" justify="space-between">
                <div>
                  <Badge
                    variant="light"
                    color={profile.role === "analyst" ? "violet" : "alfa"}
                    mb="xs"
                  >
                    {ROLE_LABELS[profile.role]}
                  </Badge>
                  <Text fw={700}>{profile.company_name ?? profile.display_name}</Text>
                  <Text size="sm" c="dimmed">
                    {profile.company_name ? profile.display_name : "Сотрудник банка"}
                  </Text>
                  <Text size="sm" mt="xs">
                    {profile.demo_hint}
                  </Text>
                </div>
                <Button
                  onClick={() => void enter(profile.login)}
                  loading={pending === profile.login}
                  variant={profile.role === "analyst" ? "light" : "filled"}
                  fullWidth
                >
                  Войти
                </Button>
              </Stack>
            </Card>
          ))}
        </SimpleGrid>
      )}
    </Stack>
  );
}
