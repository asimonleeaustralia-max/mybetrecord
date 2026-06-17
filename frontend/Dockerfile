# syntax=docker/dockerfile:1
FROM nginx:1.27-alpine

# nginx:alpine auto-renders templates in /etc/nginx/templates/*.template
# with envsubst at startup, substituting the *_UPSTREAM env vars.
COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template
COPY frontend/public /usr/share/nginx/html

# Defaults suit docker-compose; Azure overrides these with the internal FQDNs.
ENV AUTH_UPSTREAM=auth:8001 \
    BETS_UPSTREAM=bets:8002 \
    REPORTS_UPSTREAM=reports:8003 \
    PAYMENTS_UPSTREAM=payments:8004 \
    NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx/conf.d

EXPOSE 8080
