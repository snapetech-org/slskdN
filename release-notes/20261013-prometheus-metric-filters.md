---
category: changed
audience: users, operators
area: telemetry
action: none
breaking: false
---
Metrics text and JSON endpoints accept repeatable include and exclude patterns for metric-family names. Pattern counts and lengths are capped and matching has a timeout; requests without filters keep their current output.
