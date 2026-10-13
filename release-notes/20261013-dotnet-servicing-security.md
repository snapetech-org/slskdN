---
category: security
audience: users, operators
area: security
action: Upgrade to release .351 to receive the patched .NET runtime and SignalR packages.
breaking: false
---
Patched .NET dependencies and bundled runtimes now use the 10.0.13 servicing release, which fixes a high-severity SignalR denial-of-service vulnerability. Hosted builds and dependency checks now use the patched .NET SDK and inspect every first-party .NET project.
