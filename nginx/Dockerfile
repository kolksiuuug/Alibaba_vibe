# Сборка SPA и Swagger UI ассетов -> статический nginx с прокси /api в app
FROM node:22.23.4-alpine3.24 AS build

WORKDIR /frontend
# swagger-ui-dist тянет телеметрию @scarf/scarf: отключаем, сборка не ходит во внешние сервисы
ENV SCARF_ANALYTICS=false
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build \
    && mkdir -p dist/swagger-ui \
    && cp node_modules/swagger-ui-dist/swagger-ui.css \
          node_modules/swagger-ui-dist/swagger-ui-bundle.js \
          node_modules/swagger-ui-dist/swagger-ui-standalone-preset.js \
          dist/swagger-ui/

FROM nginx:1.26.3-alpine3.20

COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /frontend/dist /usr/share/nginx/html

EXPOSE 80
