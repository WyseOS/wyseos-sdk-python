# X Execution Mode SDK Design

- Date: 2026-05-11
- Status: Draft for review
- Scope: Align the Python SDK with the agent-side `XWyseBrowser` execution-mode and X API authorization flow. This design does not change Go backend APIs.

## Background

The agent now reads `extra.execution_mode` in `XWyseBrowser` and supports three values:

1. `auto`
2. `api_only`
3. `extension_only`

The SDK already forwards `extra` during session start, but it has no explicit examples or handling for API-only X execution. It also does not understand the new `x_api_authorize` interaction emitted by the agent when X API credentials are missing, expired, or missing scopes.

The SDK can run in a local terminal, on a remote server, or as a tool invoked by another agent such as Codex or OpenClaw. It cannot safely infer whether a local browser is available.

## Go Backend OAuth Findings

The Go backend has two distinct X OAuth paths.

The generic login path is:

```text
GET /auth/url?type=login&platform=twitter
```

This path logs a Mate user in and may issue a JWT or API key. It is not the right flow for agent X API execution.

The connector binding path is:

```text
POST /connectors/v1/x/accounts/authorize
```

This is the correct SDK path for `x_api_authorize`.

The connector authorize endpoint:

1. Requires an authenticated Mate user.
2. Accepts `redirect_url` and optional `target_credential_id`.
3. Creates an OAuth state with `type=bind`, `platform=twitter`, and `scene=connector_x_bind`.
4. Stores the state in Redis for five minutes.
5. Returns `auth_url`.

The callback is registered through:

```go
oauth.RegisterSceneCallback(connectors.SceneConnectorXBind, connectors.HandleXConnectorCallback)
```

The connector callback:

1. Exchanges the Twitter OAuth code for tokens.
2. Fetches `/2/users/me`.
3. Writes or refreshes `mate_connector_credentials`.
4. Redirects to the original `redirect_url` with `success=true` or an error code.

If `target_credential_id` is present, the backend validates ownership before issuing the URL and later requires the authorized Twitter account to match the existing credential's `external_user_id`. This makes it the correct path for token refresh and missing-scope reauthorization.

## Design Goals

1. Preserve the SDK's simple `extra` passthrough model.
2. Make API-only X sessions discoverable in examples without adding a large public abstraction.
3. Handle `x_api_authorize` by using the existing connector OAuth flow.
4. Default to remote-safe URL output. Do not open a browser unless the process was explicitly marked as browser-capable.
5. Keep the implementation small and local to SDK runtime helpers and `TaskRunner`.

## Non-Goals

1. No Go backend API changes.
2. No new public runner option.
3. No polling loop to detect OAuth callback completion.
4. No automatic retry of the interrupted agent task after OAuth.
5. No new unit test files.

## Execution Mode

The SDK should keep `CreateSessionRequest.extra` as `Dict[str, Any]`. It should not add a nested execution-mode model.

Examples should show the direct protocol field:

```python
extra = {
    "execution_mode": "api_only",
    "marketing_product": {"product_id": product_id},
}
```

Allowed values are documented in examples:

1. `auto`: agent decides between extension and X API.
2. `api_only`: agent uses X API where supported; reply remains unsupported.
3. `extension_only`: agent requires the browser extension.

The agent remains the authority for validation and fallback. SDK should not duplicate the agent's execution-mode decision matrix.

## Browser Availability

Add a small SDK-internal browser availability helper.

Default state:

```python
could_use_browser = False
```

The SDK may expose a minimal setter for callers that explicitly know a local browser is usable:

```python
set_browser_available(True)
```

This is not a runner option and should not appear in the main CLI path. It is an opt-in escape hatch for local integrations.

All user-facing URL interactions should go through one helper:

1. If `could_use_browser` is false, print the URL and a short instruction.
2. If `could_use_browser` is true, try to open the URL.
3. If opening fails, log the error and print the URL.

This helper should replace the current direct `webbrowser.open()` behavior for `x_confirm` as well as the new `x_api_authorize` path.

## x_api_authorize Input Handling

`TaskRunner._handle_input_message()` should recognize `x_api_authorize` before normal plan or text input handling.

Detection should be tolerant because the payload may arrive through metadata or message content:

1. `message.message.type == "x_api_authorize"`
2. `message.message.metadata.data_type == "x_api_authorize"`
3. `message.message.data.type == "x_api_authorize"`
4. JSON-decoded text content has `type == "x_api_authorize"`

Expected payload:

```json
{
  "type": "x_api_authorize",
  "session_id": "...",
  "execution_mode": "api_only",
  "external_user_id": "...",
  "external_username": "...",
  "reason_code": "...",
  "reason_message": "..."
}
```

The SDK should not send a fake approval response after printing the URL. OAuth completion happens out of band. The user or calling agent should continue the session through the existing input mechanism after completing authorization.

## Connector Selection

When handling `x_api_authorize`, the SDK should call:

```python
client.user.authorize_x_account(target_connector_id=...)
```

Before calling it, SDK should attempt to find an existing connector:

1. Call `client.user.list_x_accounts()`.
2. Prefer exact match on `external_user_id`.
3. Fall back to exact match on `external_username`.
4. If one account matches, pass its `connector_id` as `target_connector_id`.
5. If none match, pass `None`.

This maps agent reasons to backend behavior:

1. `TOKEN_EXPIRED`: likely existing connector, reauthorize the same credential.
2. `INSUFFICIENT_SCOPE` / `ACCOUNT_SCOPE_MISSING`: likely existing connector, reauthorize the same credential with current backend Twitter scopes.
3. `AUTH_REQUIRED` / `CREDENTIAL_NOT_FOUND`: create a new connector if no match exists.
4. `ACCOUNT_IDENTIFIER_REQUIRED`: no reliable target exists, create a new connector.

If listing connectors fails, SDK should still call `authorize_x_account(None)` and print/log that it could not target an existing credential.

## Redirect URL

The existing SDK `UserService.authorize_x_account()` already sends:

```text
{extension_webapp_host}/settings/integrations/x/callback?scene=connector_x_bind
```

This is compatible with the Go connector callback. No SDK change is required unless product wants a CLI-specific success page later.

## Error Handling

If `authorize_x_account()` fails:

1. Print a concise error for CLI users.
2. Add an execution log entry when event logging is enabled.
3. Leave the task pending; do not send a success response.

If URL opening fails while `could_use_browser` is true:

1. Log a warning in English.
2. Print the URL.

## Files To Change

1. `octoevo/mate/task_runner.py`
   - Add tolerant `x_api_authorize` detection.
   - Add handler that lists connectors, picks `target_connector_id`, calls `authorize_x_account()`, and sends URL to the unified URL helper.
   - Route `x_confirm` through the same URL helper.

2. `octoevo/mate/browser_runtime.py` or similar small module
   - Hold `could_use_browser = False`.
   - Provide `set_browser_available()` and `show_or_open_url()`.

3. `examples/getting_started/example.py` and quickstart docs
   - Show `extra["execution_mode"] = "api_only"` in the API-only marketing example.
   - Keep URL completion as text-first.

## Verification

Run:

```bash
python -m compileall octoevo/mate
```

Manual checks:

1. `x_confirm` no longer attempts to open a browser by default.
2. `x_api_authorize` prints a connector OAuth URL.
3. Matching by `external_user_id` passes `target_connector_id`.
4. Missing match passes `target_connector_id=None`.
5. `extra.execution_mode` appears unchanged in the WebSocket start payload.
