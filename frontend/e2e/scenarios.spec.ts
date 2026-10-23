import { expect, test } from "@playwright/test";

import { expectStatus, fillAndSubmit, loginAs, startApplication } from "./helpers";

// Пять демо-сценариев (CLAUDE.md, раздел 9) через интерфейс против http://localhost:8080.

test("1. Одобрение: предложение, подпись кодом, выдача", async ({ page }) => {
  await loginAs(page, "ООО «Тёплый колос»");
  await startApplication(page, { amount: 3_000_000, term: 24, product: "Оборотный кредит «Ритм»" });
  await fillAndSubmit(page);

  await expectStatus(page, "offer");
  await expect(page.getByText("Одобрено на ваших условиях")).toBeVisible();
  await page.getByRole("button", { name: "Принять предложение" }).click();

  await expectStatus(page, "accepted");
  await expect(page.getByText("Симуляция").first()).toBeVisible();
  await page.getByRole("button", { name: "Получить код" }).click();
  const code = (await page.getByTestId("sign-code").innerText()).trim();
  await page.locator(".mantine-PinInput-input").first().click();
  await page.keyboard.type(code);
  await page.getByRole("button", { name: "Подписать договор" }).click();

  await expectStatus(page, "issued");
  await expect(page.getByRole("heading", { name: "Кредит выдан" })).toBeVisible();

  await page.getByRole("button", { name: "Уведомления" }).click();
  await expect(page.getByText("Кредит выдан").last()).toBeVisible();
});

test("2. Контрпредложение: сумма больше лимита, клиент отклоняет", async ({ page }) => {
  await loginAs(page, "ООО «Дальний рейс»");
  await startApplication(page, {
    amount: 12_000_000,
    term: 24,
    product: "Оборотный кредит «Ритм»",
  });
  await fillAndSubmit(page);

  await expectStatus(page, "offer");
  await expect(page.getByText("Банк предлагает другие условия")).toBeVisible();
  await page.getByRole("button", { name: "Отклонить" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Отклонить" }).click();

  await expectStatus(page, "declined");
});

test("3. Дозапрос: данные о залоге, затем предложение", async ({ page }) => {
  await loginAs(page, "ИП Лаврова Мира Олеговна");
  await startApplication(page, {
    purpose: "Купить оборудование или технику",
    amount: 2_500_000,
    term: 36,
    product: "Инвестиционный кредит «Станок»",
  });
  await fillAndSubmit(page);

  await expectStatus(page, "info_requested");
  await page.getByLabel("Описание залога").fill("Токарный станок с ЧПУ, 2024 года выпуска");
  await page.getByLabel("Оценочная стоимость залога, ₽").fill("3200000");
  await page.getByLabel("Поставщик оборудования").fill("ООО «Станкоцентр»");
  await page.getByRole("button", { name: "Отправить ответ" }).click();

  await expectStatus(page, "offer");
});

test("4. Ручное рассмотрение: аналитик меняет условия", async ({ page }) => {
  await loginAs(page, "ООО «Зелёная веранда»");
  await startApplication(page, {
    amount: 1_500_000,
    term: 18,
    product: "Экспресс-кредит «Быстрый старт»",
  });
  await fillAndSubmit(page);
  await expectStatus(page, "manual_review");
  const applicationUrl = page.url();

  await loginAs(page, "Кредитный аналитик");
  await page
    .getByRole("row", { name: /Зелёная веранда/ })
    .first()
    .click();
  await expectStatus(page, "manual_review");
  await expect(page.getByText("Стабильность оборотов")).toBeVisible();
  await page.getByText("Изменить условия", { exact: true }).click();
  await page.getByLabel("Сумма, ₽").fill("1200000");
  await page.getByLabel("Комментарий").fill("Обороты неровные: снижаем сумму до 1,2 млн");
  await page.getByRole("button", { name: "Изменить условия" }).click();
  await expectStatus(page, "offer");

  await loginAs(page, "ООО «Зелёная веранда»");
  await page.goto(applicationUrl);
  await expectStatus(page, "offer");
  await expect(page.getByText("Комментарий кредитного аналитика")).toBeVisible();
});

test("5. Отказ: просрочка 90+ дней", async ({ page }) => {
  await loginAs(page, "ООО «Кромка-Строй»");
  await startApplication(page, { amount: 2_000_000, term: 12, product: "Оборотный кредит «Ритм»" });
  await fillAndSubmit(page);

  await expectStatus(page, "rejected");
  await expect(page.getByText(/В кредитной истории есть текущая просрочка/)).toBeVisible();
});
