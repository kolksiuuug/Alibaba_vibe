import {
  AppShell,
  Badge,
  Button,
  Container,
  Group,
  Menu,
  Text,
  ThemeIcon,
  UnstyledButton,
} from "@mantine/core";
import {
  IconBuildingBank,
  IconLogout,
  IconSwitchHorizontal,
  IconUserCircle,
} from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "react-router-dom";

import { Api } from "../api/endpoints";
import { homePath, useAuth } from "../auth/AuthContext";
import { NotificationBell } from "./NotificationBell";

export function Layout() {
  const { user, loginAs, logout } = useAuth();
  const navigate = useNavigate();
  const profiles = useQuery({
    queryKey: ["demo-profiles"],
    queryFn: Api.demoProfiles,
    staleTime: Infinity,
    enabled: Boolean(user),
  });

  async function switchTo(login: string) {
    const next = await loginAs(login);
    navigate(homePath(next));
  }

  function exit() {
    logout();
    navigate("/login");
  }

  return (
    <AppShell header={{ height: 64 }} padding="md">
      <AppShell.Header>
        <Container size="xl" h="100%">
          <Group h="100%" justify="space-between" wrap="nowrap">
            <Group gap="sm" wrap="nowrap">
              <UnstyledButton component={Link} to={homePath(user)}>
                <Group gap="xs" wrap="nowrap">
                  <ThemeIcon size="lg" radius="md">
                    <IconBuildingBank size={20} />
                  </ThemeIcon>
                  <Text fw={700}>Кредитный кабинет</Text>
                </Group>
              </UnstyledButton>
              <Badge variant="light" color="gray">
                Демо · данные синтетические
              </Badge>
              {user?.role === "client" && (
                <Group gap={4} ml="md" wrap="nowrap">
                  <Button component={Link} to="/" variant="subtle" color="dark">
                    Мои заявки
                  </Button>
                  <Button component={Link} to="/new" variant="subtle" color="dark">
                    Подобрать кредит
                  </Button>
                </Group>
              )}
              {user?.role === "analyst" && (
                <Button component={Link} to="/analyst" variant="subtle" color="dark" ml="md">
                  Очередь заявок
                </Button>
              )}
            </Group>

            {user && (
              <Group gap="xs" wrap="nowrap">
                {user.role === "client" && <NotificationBell />}
                <Menu position="bottom-end" width={360} shadow="md">
                  <Menu.Target>
                    <Button
                      variant="default"
                      leftSection={<IconUserCircle size={18} />}
                      rightSection={<IconSwitchHorizontal size={16} />}
                    >
                      <Text size="sm" truncate maw={260}>
                        {user.company?.name ?? user.display_name} ·{" "}
                        {user.role === "analyst" ? "аналитик" : "клиент"}
                      </Text>
                    </Button>
                  </Menu.Target>
                  <Menu.Dropdown>
                    <Menu.Label>Сменить демо-профиль</Menu.Label>
                    {profiles.data?.map((profile) => (
                      <Menu.Item
                        key={profile.login}
                        onClick={() => void switchTo(profile.login)}
                        disabled={profile.login === user.login}
                      >
                        <Text size="sm" fw={500}>
                          {profile.company_name ?? profile.display_name}
                          {profile.role === "analyst" && " (аналитик)"}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {profile.demo_hint}
                        </Text>
                      </Menu.Item>
                    ))}
                  </Menu.Dropdown>
                </Menu>
                <Button
                  variant="subtle"
                  color="gray"
                  leftSection={<IconLogout size={16} />}
                  onClick={exit}
                >
                  Выйти
                </Button>
              </Group>
            )}
          </Group>
        </Container>
      </AppShell.Header>
      <AppShell.Main>
        <Container size="xl" py="md">
          <Outlet />
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}
