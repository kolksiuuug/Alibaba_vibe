import { useQuery } from "@tanstack/react-query";

async function isApiAlive(): Promise<boolean> {
  const response = await fetch("/api/health");
  return response.ok;
}

export function App() {
  const health = useQuery({ queryKey: ["health"], queryFn: isApiAlive });

  let apiState = "проверяем…";
  if (health.isError || health.data === false) apiState = "недоступно";
  else if (health.data) apiState = "работает";

  return (
    <main
      style={{
        fontFamily: "system-ui, sans-serif",
        maxWidth: 720,
        margin: "48px auto",
        padding: "0 16px",
      }}
    >
      <h1>Умный кредитный кабинет предпринимателя</h1>
      <p>Прототип для хакатона. Все данные синтетические.</p>
      <p>Состояние API: {apiState}</p>
      <p>
        <a href="/api/docs">Документация API (Swagger)</a>
      </p>
    </main>
  );
}
