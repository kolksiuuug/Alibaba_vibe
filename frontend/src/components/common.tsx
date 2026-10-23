import { Alert, Center, Loader } from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { homePath, useAuth } from "../auth/AuthContext";

export function ErrorAlert({ error, title = "Не получилось" }: { error: unknown; title?: string }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : "Неизвестная ошибка";
  const retryHint = error instanceof ApiError && error.status >= 500 ? " Попробуйте ещё раз." : "";
  return (
    <Alert color="red" title={title} icon={<IconAlertCircle size={18} />}>
      {message}
      {retryHint}
    </Alert>
  );
}

export function PageLoader() {
  return (
    <Center py="xl">
      <Loader />
    </Center>
  );
}

/** Пускает на страницу только вошедшего пользователя нужной роли. */
export function RequireAuth({
  role,
  children,
}: {
  role?: "client" | "analyst";
  children: ReactNode;
}) {
  const { user, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) return <Navigate to={homePath(user)} replace />;
  return <>{children}</>;
}
