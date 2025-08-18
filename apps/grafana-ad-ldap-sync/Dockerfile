# syntax=docker/dockerfile:1.4

FROM python:3.13-alpine
LABEL maintainers="dmclf <19852218+dmclf@users.noreply.github.com>"
LABEL description="unofficial docker image for ADldap2Grafana Sync"
ENV PYTHONUNBUFFERED=TRUE

RUN pip install requests ldap3 \
    && adduser -h /app/ -D -H appuser

COPY --chown=appuser --chmod=555 grafana-sync.py /app/

USER appuser

WORKDIR /app

ENTRYPOINT ["/app/grafana-sync.py"]
