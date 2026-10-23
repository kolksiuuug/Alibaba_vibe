import type { components } from "./schema";

/** Типы ответов API — только сгенерированные из docs/openapi.yaml (npm run gen:api). */
export type Schemas = components["schemas"];

const TOKEN_KEY = "credit-cabinet.token";

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string): void {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      // приватный режим браузера: сессия живёт до перезагрузки страницы
    }
  },
  clear(): void {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      // нечего очищать
    }
  },
};

/** Ошибка API в формате problem+json. */
export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly errors?: Record<string, unknown>;

  constructor(status: number, problem: Schemas["Problem"]) {
    super(problem.detail || problem.title || `Ошибка ${status}`);
    this.status = status;
    this.code = problem.code;
    this.errors = problem.errors as Record<string, unknown> | undefined;
  }
}

let onUnauthorized: () => void = () => {};

export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

export async function api<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, {
      title: "Нет связи с сервером",
      detail: "Проверьте, что стенд запущен (docker compose up).",
    });
  }

  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401) onUnauthorized();
    throw new ApiError(response.status, (data ?? {}) as Schemas["Problem"]);
  }
  return data as T;
}

/** Ошибка валидации поля: errors.amount или errors.form_data.contact_name. */
export function fieldError(error: unknown, ...path: string[]): string | undefined {
  if (!(error instanceof ApiError) || !error.errors) return undefined;
  let node: unknown = error.errors;
  for (const key of path) {
    if (node && typeof node === "object" && key in node) {
      node = (node as Record<string, unknown>)[key];
    } else {
      return undefined;
    }
  }
  return Array.isArray(node) ? String(node[0]) : undefined;
}
