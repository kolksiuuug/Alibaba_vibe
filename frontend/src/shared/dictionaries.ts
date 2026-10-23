/** Подписи кодов из API для интерфейса. Коды совпадают с backend. */

export const PURPOSES = [
  { value: "working_capital", label: "Пополнить оборотные средства" },
  { value: "equipment", label: "Купить оборудование или технику" },
  { value: "cash_gap", label: "Закрыть кассовый разрыв" },
  { value: "expansion", label: "Развить бизнес" },
] as const;

export type PurposeCode = (typeof PURPOSES)[number]["value"];

export function purposeLabel(code: string): string {
  return PURPOSES.find((p) => p.value === code)?.label ?? code;
}

export const ROLE_LABELS: Record<string, string> = {
  client: "Предприниматель",
  analyst: "Кредитный аналитик",
};

export const ACTOR_LABELS: Record<string, string> = {
  client: "Клиент",
  analyst: "Аналитик",
  system: "Система",
};

export const CHECK_SOURCES: Record<string, string> = {
  egrul: "ЕГРЮЛ / ЕГРИП",
  fns: "ФНС «Прозрачный бизнес»",
  bki: "Бюро кредитных историй",
};

export const FACTOR_LABELS: Record<string, string> = {
  business_age: "Возраст бизнеса",
  avg_turnover: "Среднемесячный оборот",
  turnover_stability: "Стабильность оборотов",
  debt_load: "Долговая нагрузка",
  credit_history: "Кредитная история",
  tax_discipline: "Налоговая дисциплина",
  amount_to_turnover: "Сумма к годовому обороту",
  security: "Залог и поручительство",
  industry_risk: "Отраслевой риск",
};

/** Поля анкеты: подписи и подсказки для формы. */
export const FORM_FIELDS: Record<string, { label: string; hint?: string; numeric?: boolean }> = {
  contact_name: { label: "Контактное лицо по заявке", hint: "Кто ответит на вопросы банка" },
  purpose_description: {
    label: "На что пойдут деньги",
    hint: "Пара предложений простыми словами",
  },
  collateral_description: {
    label: "Описание залога",
    hint: "Что это, марка, год выпуска",
  },
  collateral_value: { label: "Оценочная стоимость залога, ₽", numeric: true },
  equipment_supplier: { label: "Поставщик оборудования" },
  guarantor_full_name: { label: "ФИО поручителя" },
  guarantor_inn: { label: "ИНН поручителя" },
};

/** Поля, которые аналитик может запросить у клиента. */
export const REQUESTABLE_FIELDS = [
  "collateral_description",
  "collateral_value",
  "equipment_supplier",
  "guarantor_full_name",
  "guarantor_inn",
].map((code) => ({ value: code, label: FORM_FIELDS[code].label }));

export const DECISION_ACTIONS = [
  { value: "approve", label: "Одобрить" },
  { value: "change_terms", label: "Изменить условия" },
  { value: "request_info", label: "Запросить информацию" },
  { value: "reject", label: "Отказать" },
] as const;

export type DecisionAction = (typeof DECISION_ACTIONS)[number]["value"];

export const OUTCOME_LABELS: Record<string, string> = {
  offer: "Предложение",
  manual_review: "На ручное рассмотрение",
  info_requested: "Дозапрос",
  rejected: "Отказ",
};

/** Причины переходов из журнала (AuditEvent.reason) простыми словами. */
export const REASON_LABELS: Record<string, string> = {
  approved: "одобрено автоматически",
  amount_above_limit: "сумма больше лимита",
  term_extended: "увеличен срок",
  reduced_amount: "уменьшена сумма",
  missing_fields: "не хватает данных",
  borderline_score: "пограничная оценка",
  low_score: "низкая оценка риска",
  limit_below_minimum: "лимит меньше минимума продукта",
  debt_load_exceeded: "высокая долговая нагрузка",
  company_inactive: "компания не действует",
  current_overdue: "текущая просрочка",
  tax_debt: "налоговая задолженность",
  business_too_young: "бизнесу меньше 6 месяцев",
  info_provided: "ответ на дозапрос",
  pipeline_failed: "проверка не завершилась",
  bki_unavailable: "БКИ не ответило",
  egrul_unavailable: "ЕГРЮЛ не ответил",
  fns_unavailable: "ФНС не ответила",
  validation_failed: "ошибка в анкете",
  invalid_source_data: "некорректные данные проверок",
  approve: "решение аналитика",
  change_terms: "аналитик изменил условия",
  request_info: "дозапрос аналитика",
  reject: "отказ аналитика",
};

export const GRADE_COLORS: Record<string, string> = {
  A: "green",
  B: "teal",
  C: "yellow",
  D: "orange",
  E: "red",
};
