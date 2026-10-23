/**
 * Словарь статусов заявки. Коды совпадают с backend (app/domain/statuses.py);
 * русские подписи и подсказки живут только здесь.
 */
export type StatusCode =
  | "draft"
  | "submitted"
  | "checking"
  | "info_requested"
  | "manual_review"
  | "offer"
  | "accepted"
  | "signed"
  | "issued"
  | "rejected"
  | "declined"
  | "cancelled";

export interface StatusInfo {
  label: string;
  color: string;
  /** Что сейчас происходит и что делать клиенту */
  client: string;
  /** Подсказка для аналитика */
  analyst: string;
}

export const STATUSES: Record<StatusCode, StatusInfo> = {
  draft: {
    label: "Черновик",
    color: "gray",
    client:
      "Заявка ещё не отправлена. Проверьте условия и заполните анкету, затем нажмите «Отправить заявку».",
    analyst: "Клиент ещё не отправил заявку.",
  },
  submitted: {
    label: "Подана",
    color: "blue",
    client: "Заявка получена. Через пару секунд начнётся автоматическая проверка.",
    analyst: "Заявка в очереди конвейера.",
  },
  checking: {
    label: "Проверка и скоринг",
    color: "blue",
    client:
      "Проверяем компанию в ЕГРЮЛ/ЕГРИП, налоги и кредитную историю. Обычно это меньше минуты — страница обновится сама.",
    analyst: "Идёт автоматическая проверка.",
  },
  info_requested: {
    label: "Нужна информация",
    color: "orange",
    client: "Банку не хватает данных. Ответьте на запрос ниже — заявка сразу вернётся на проверку.",
    analyst: "Ждём ответ клиента на дозапрос.",
  },
  manual_review: {
    label: "Ручное рассмотрение",
    color: "violet",
    client: "Заявку смотрит кредитный аналитик. Решение появится здесь и в уведомлениях.",
    analyst: "Нужно ваше решение: одобрить, изменить условия, запросить данные или отказать.",
  },
  offer: {
    label: "Предложение",
    color: "teal",
    client: "Банк готов выдать кредит. Посмотрите условия и примите решение.",
    analyst: "Клиент рассматривает предложение.",
  },
  accepted: {
    label: "Принято",
    color: "teal",
    client: "Вы приняли предложение. Осталось подписать договор кодом.",
    analyst: "Клиент принял предложение и подписывает договор.",
  },
  signed: {
    label: "Подписано",
    color: "green",
    client: "Договор подписан. Деньги поступят на расчётный счёт через несколько секунд.",
    analyst: "Договор подписан, идёт выдача.",
  },
  issued: {
    label: "Выдано",
    color: "green",
    client: "Кредит выдан: деньги на расчётном счёте.",
    analyst: "Кредит выдан.",
  },
  rejected: {
    label: "Отказ",
    color: "red",
    client: "Банк не может выдать кредит по этой заявке. Причины — ниже.",
    analyst: "По заявке отказ.",
  },
  declined: {
    label: "Отклонено клиентом",
    color: "gray",
    client: "Вы отказались от предложения. Можно подобрать другой кредит.",
    analyst: "Клиент отклонил предложение.",
  },
  cancelled: {
    label: "Отменена клиентом",
    color: "gray",
    client: "Заявка отменена. Новую можно подать в любой момент.",
    analyst: "Клиент отменил заявку.",
  },
};

/** Пока заявка в этих статусах, карточка опрашивает API раз в 2 секунды. */
export const POLLING_STATUSES: ReadonlySet<string> = new Set(["submitted", "checking", "signed"]);
export const POLL_INTERVAL_MS = 2000;

export function statusInfo(code: string): StatusInfo {
  return STATUSES[code as StatusCode] ?? { label: code, color: "gray", client: "", analyst: "" };
}
