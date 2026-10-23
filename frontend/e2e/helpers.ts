import { expect, type Page } from "@playwright/test";

export const STATUS = (page: Page) => page.getByTestId("application-status");

/** Войти в демо-профиль по названию компании на карточке (или «Кредитный аналитик»). */
export async function loginAs(page: Page, cardText: string) {
  await page.goto("/login");
  const menu = page.getByRole("button", { name: "Выйти" });
  if (await menu.isVisible()) {
    await menu.click();
  }
  await page
    .locator(".mantine-Card-root", { hasText: cardText })
    .getByRole("button", { name: "Войти" })
    .click();
}

/** Подобрать продукт и создать черновик заявки. */
export async function startApplication(
  page: Page,
  {
    purpose,
    amount,
    term,
    product,
  }: { purpose?: string; amount: number; term: number; product: string },
) {
  await page.getByRole("link", { name: "Подобрать кредит" }).first().click();
  if (purpose) await page.getByText(purpose, { exact: true }).click();
  await page.getByLabel("Сумма, ₽").fill(String(amount));
  await page.getByLabel("Срок, месяцев").fill(String(term));
  await page.getByRole("button", { name: "Подобрать" }).click();
  await page
    .locator(".mantine-Card-root", { hasText: product })
    .getByRole("button", { name: "Оформить заявку" })
    .click();
  await expect(STATUS(page)).toHaveAttribute("data-status", "draft");
}

/** Заполнить обязательные поля анкеты и отправить заявку. */
export async function fillAndSubmit(page: Page) {
  await page.getByLabel("Контактное лицо по заявке").fill("Демо Контакт Синтетикович");
  await page.getByLabel("На что пойдут деньги").fill("Закупка сырья и материалов на сезон");
  await page.getByRole("button", { name: "Отправить заявку" }).click();
}

export async function expectStatus(page: Page, status: string) {
  await expect(STATUS(page)).toHaveAttribute("data-status", status);
}
