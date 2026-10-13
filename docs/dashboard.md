# Dashboard

The Dashboard is the default page after sign-in. It summarizes successful
downloads and uploads completed during the last seven days, then links directly
to each transfer list.

The byte totals use the amount actually transferred. Failed, cancelled, and
other unsuccessful transfers do not contribute to the file counts or byte
totals. Use the queue pages to inspect in-progress work and older transfer
history.

The page refreshes when opened. Use **Refresh transfer overview** to request a
new summary without leaving the page.

## API

The Dashboard reads `GET /api/v0/telemetry/reports/transfers/summary`. The
endpoint defaults to the seven days ending at the request time and groups
completed transfer summaries by direction and final state. API clients that
need another time range can supply `start` and `end` query values.

See the [API reference](api-documentation.md) for the complete route list and
the [Transfer Operations guide](transfer-operations.md) for queue and history
behavior.
