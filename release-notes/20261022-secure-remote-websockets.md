---
category: security
audience: operators
area: web-transport
action: Configure TLS for remote WebSocket clients before upgrading
breaking: true
---
Remote WebSocket connections now require TLS; cleartext connections remain available only on loopback. Configure HTTPS/WSS for remote browser and API clients before upgrading.
