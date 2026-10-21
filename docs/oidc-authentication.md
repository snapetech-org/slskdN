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
`fusionauth`, `onelogin`, `pingone`, `jumpcloud`, and `apple-sign-in`; unknown
values fall back to generic OpenID Connect presentation. Provider discovery
and issuer validation still use `issuer_url`.

The shared [provider catalog](https://github.com/snapetech-org/seerrng/blob/main/docs/maintainers/oidc-provider-catalog.md)
has official setup links, example issuers, and provider-specific claim notes.
The [cross-project OIDC contract](https://github.com/snapetech-org/seerrng/blob/main/docs/maintainers/oidc-cross-project-template.md)
explains the common protocol rules and the intentional app-specific session and
role differences.

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

## Sign in with Apple

Set `issuer_url` to exactly `https://appleid.apple.com`, use the Apple Services
ID as `client_id`, and store the signed client-secret JWT in `client_secret`.
Register the exact HTTPS redirect URI above. slskdN requests only `openid email`,
uses Apple's required `response_mode=form_post`, and omits PKCE for this
provider. Apple may encode `email_verified` as a JSON boolean or string; only
`true` is accepted. Rotate the JWT before its six-month maximum expiry. See
Apple's [environment setup](https://developer.apple.com/documentation/signinwithapple/configuring-your-environment-for-sign-in-with-apple)
and [web authorization flow](https://developer.apple.com/documentation/signinwithapple/incorporating-sign-in-with-apple-into-other-platforms).

## Enable, verify, and recover

Configure all four core values together. The redirect URI is
`https://<public-host>/<web.url_base>/signin-oidc` when a URL base is set, or
`https://<public-host>/signin-oidc` at the root. Keep the provider secret in a
server-side secret source or protected `slskd.yml`, never in the browser bundle
or a checked-in configuration example. Apply the new configuration and start a
fresh sign-in.

Exact-email or domain admissions grant the app's Administrator permission.
When `allow_any_verified_user` is explicitly enabled, other verified users
receive ReadWrite. This distinction is local to slskdN: OIDC group claims do
not promote a user, and provider branding does not change either role. Keep
local password/API-key access available while validating the provider.

Test one exact allow-list account, one verified unadmitted account, and the
allow-any role only in a controlled environment. Confirm logout invalidates the
app JWT, then confirm local recovery still works. To disable OIDC, clear the
complete provider configuration or choose another authentication method using
the normal slskdN configuration procedure.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Provider reports an invalid callback | Match the exact external HTTPS URI, including `web.url_base`, to `SLSKD_OIDC_REDIRECT_URI` and the provider registration. |
| Issuer discovery or token exchange fails | Check exact tenant/realm issuer, DNS, CA trust, and outbound access. Private addresses or HTTP require the explicit `allow_private_issuer` opt-in. |
| Access is denied after a successful provider login | Verify `email`, `email_verified`, exact/domain admission values, and that the user's provider email matches the allowed value. Empty lists deny by default. |
| Callback state/nonce validation fails | Start a new login in the same browser and public hostname; check proxy scheme/host forwarding, cookie handling, and recent service restarts. |
| A user has a different role than expected | Exact email/domain allow-list matches receive Administrator; allow-any matches receive ReadWrite. Groups do not grant Administrator. |
| Apple callback fails | Confirm Apple's Services ID and exact issuer, `/signin-oidc` URL, `form_post` support, SameSite=None/Secure cookies, and valid JWT secret. |

For support, include the slskdN version, provider ID, redacted issuer host,
callback path, error code, and timestamp. Do not attach codes, tokens, secrets,
or raw claim payloads.
