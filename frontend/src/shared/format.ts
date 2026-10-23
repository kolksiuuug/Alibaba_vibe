const rubles = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });
const kopecks = new Intl.NumberFormat("ru-RU", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const dateFormat = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
  year: "numeric",
});
const dateTimeFormat = new Intl.DateTimeFormat("ru-RU", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

export function formatMoney(value?: number | null): string {
  return value == null ? "—" : `${rubles.format(value)} ₽`;
}

export function formatMoneyExact(value?: number | null): string {
  return value == null ? "—" : `${kopecks.format(value)} ₽`;
}

export function formatRate(value?: number | null): string {
  return value == null ? "—" : `${value.toLocaleString("ru-RU", { maximumFractionDigits: 2 })}%`;
}

export function formatDate(value?: string | null): string {
  return value ? dateFormat.format(new Date(value)) : "—";
}

export function formatDateTime(value?: string | null): string {
  return value ? dateTimeFormat.format(new Date(value)) : "—";
}

export function formatMonths(value: number): string {
  return `${value} мес.`;
}

export function averageTurnover(months: { amount: number }[]): number {
  return months.length ? months.reduce((sum, m) => sum + m.amount, 0) / months.length : 0;
}
