# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/scripts ./scripts
COPY frontend/src ./src
COPY frontend/public ./public
RUN npm run build

FROM nginx:1.27-alpine

ARG BUILD_ID=dev

RUN apk add --no-cache curl

COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=frontend-build /build/public /usr/share/nginx/html
RUN chmod -R a+rX /usr/share/nginx/html \
    && sed -i "s/__BUILD_ID__/${BUILD_ID}/g" /usr/share/nginx/html/app/index.html

ENV AUTH_UPSTREAM=http://auth:8001 \
    BETS_UPSTREAM=http://bets:8002 \
    REPORTS_UPSTREAM=http://reports:8003 \
    PAYMENTS_UPSTREAM=http://payments:8004 \
    NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx/conf.d

EXPOSE 8080
