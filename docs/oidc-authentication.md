# OpenID Connect sign-in

slskdN supports optional browser sign-in through an OpenID Connect provider.
Ordinary providers use Authorization Code with PKCE; Apple uses its documented
form-post flow without PKCE. Sign-in creates the normal slskdN JWT after
the provider identity passes admission. Provider tokens are not stored or sent
to browser JavaScript. The existing username/password login and API-key
authentication remain available.

Configure these values under `web.authentication.oidc` in `slskd.yml`, or use
the matching environment variables below:

```dotenv
SLSKD_OIDC_ISSUER_URL=https://id.example.com/realms/slskdn
SLSKD_OIDC_CLIENT_ID=slskdn
SLSKD_OIDC_CLIENT_SECRET=replace-with-client-secret
SLSKD_OIDC_REDIRECT_URI=https://music.example.com/signin-oidc
SLSKD_OIDC_ALLOWED_EMAILS=operator@example.com
SLSKD_OIDC_PROVIDER=keycloak
```

`provider`/`SLSKD_OIDC_PROVIDER` is a display hint only. The login page uses a
local provider icon and links to the selected provider's official setup guide.
Supported branded values are `google`, `microsoft-entra`, `okta`, `auth0`,
`keycloak`, `authentik`, `zitadel`, `amazon-cognito`, `gitlab`,
`fusionauth`, `onelogin`, `pingone`, and `jumpcloud`; unknown
values fall back to generic OpenID Connect presentation. Provider discovery
and issuer validation still use `issuer_url`.

Register the exact public HTTPS redirect URI with the provider. If `web.url_base`
is configured, include that path before `/signin-oidc`. The callback remains
HTTPS even when a private HTTP issuer is explicitly enabled.

The app requests `openid profile email`, validates the provider signature,
issuer, audience, lifetime, state, nonce, and PKCE verifier, and requires
`email_verified=true`. Exact email and domain lists are combined. With no
admission list, sign-in is denied by default. An address or domain on the
explicit admission list receives the app's Administrator role. If
`allow_any_verified_user` is enabled, other verified accounts receive
ReadWrite. OIDC group claims never grant the Administrator role.

| YAML field | Environment variable | Default |
| --- | --- | --- |
| `issuer_url` | `SLSKD_OIDC_ISSUER_URL` | unset |
| `client_id` | `SLSKD_OIDC_CLIENT_ID` | unset |
| `client_secret` | `SLSKD_OIDC_CLIENT_SECRET` | unset |
| `redirect_uri` | `SLSKD_OIDC_REDIRECT_URI` | unset |
| `provider` | `SLSKD_OIDC_PROVIDER` | `generic` |
| `allowed_emails` | `SLSKD_OIDC_ALLOWED_EMAILS` | empty; denies sign-in |
| `allowed_email_domains` | `SLSKD_OIDC_ALLOWED_EMAIL_DOMAINS` | empty |
| `scopes` | `SLSKD_OIDC_SCOPES` | `openid profile email` |
| `allow_any_verified_user` | `SLSKD_OIDC_ALLOW_ANY_VERIFIED_USER` | `false` |
| `allow_private_issuer` | `SLSKD_OIDC_ALLOW_PRIVATE_ISSUER` | `false` |

Provider backchannel requests reject redirects, use a 15-second timeout, cap
responses at 1 MiB, and reject private/reserved addresses unless
`allow_private_issuer` is enabled. The browser receives only slskdN's own
existing session token, held in the same tab-scoped storage as password login.
Logout revokes that JWT through the existing session endpoint.

This follows the [shared cross-project OIDC contract](https://github.com/snapetech-org/seerrng/blob/main/docs/maintainers/oidc-cross-project-template.md).

### Sign in with Apple

Set `issuer_url` to exactly `https://appleid.apple.com`, use the Apple Services
ID as `client_id`, and store the signed client-secret JWT in `client_secret`.
Register the exact HTTPS redirect URI above. slskdN requests only `openid email`,
uses Apple's required `response_mode=form_post`, and omits PKCE for this
provider. Apple may encode `email_verified` as a JSON boolean or string; only
`true` is accepted. Rotate the JWT before its six-month maximum expiry. See
Apple's [environment setup](https://developer.apple.com/documentation/signinwithapple/configuring-your-environment-for-sign-in-with-apple)
and [web authorization flow](https://developer.apple.com/documentation/signinwithapple/incorporating-sign-in-with-apple-into-other-platforms).
