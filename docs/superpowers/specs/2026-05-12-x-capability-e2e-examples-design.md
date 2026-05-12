# X Capability E2E Examples Design

## Background

The XAgent capability decision document defines a three-dimensional problem space:

- 2 runtime environments: local and remote
- 2 execution capabilities: browser extension and X API
- 4 marketing task types: reply, publish, interact, and direct message

The SDK currently has a minimal marketing example in `examples/getting_started`, but it does not provide a complete Live E2E runner for validating all capability decision paths. The new example project will be a small, focused client that creates real sessions, connects over WebSocket, runs the Agent, and verifies the expected result for every matrix scenario.

This is not a unit test project and not a dry-run simulator. It is a real E2E validation client.

## Goals

- Add a new example project under `examples/x_capability_e2e/`.
- Cover all 16 combinations of environment, execution capability, and marketing task type.
- Run real marketing sessions through the existing SDK and Agent flow.
- Allow real X write actions, including publish, interact, and direct message.
- Verify negative paths by creating real sessions and checking the Agent's rejection or failure reason.
- Reuse existing SDK configuration and session runner patterns from `examples/getting_started`.
- Keep the project small, explicit, and easy to read.

## Non-Goals

- Do not build a general test framework.
- Do not add pytest or another test runner.
- Do not add a dry-run mode.
- Do not add a write-safety gate such as `allow_write`.
- Do not introduce new SDK or Agent protocol fields.
- Do not implement environment auto-detection.
- Do not run scenarios in parallel.

## Project Layout

```text
examples/x_capability_e2e/
├── README.md
├── main.py
├── config.py
├── scenarios.py
├── runner.py
├── assertions.py
├── mate.yaml.example
└── results/
    └── .gitkeep
```

Responsibilities:

- `main.py`: CLI entry point, scenario filtering, sequential execution, summary output.
- `config.py`: load `mate.yaml` and E2E environment variables.
- `scenarios.py`: define the fixed 16 scenarios and their expected outcomes.
- `runner.py`: create sessions, connect WebSocket, run `TaskRunner.run_interactive_session()`, and collect output.
- `assertions.py`: classify captured output as pass, fail, timeout, or error.
- `README.md`: explain setup and warn that this runner performs real X actions.
- `results/latest.json`: generated at runtime and not committed.

## Configuration

The example will use `mate.yaml`, matching `examples/getting_started`:

```yaml
mate:
  api_key: "your-api-key"
  # or jwt_token: "your-jwt-token"
  base_url: "https://api.dev.weclaw.ai"
  timeout: 30
```

Additional E2E inputs come from environment variables:

- `MATE_E2E_PRODUCT_ID`: optional marketing product ID.
- `MATE_E2E_TARGET_TWEET_URL`: tweet URL used by reply and interact scenarios.
- `MATE_E2E_TARGET_X_USER`: X username used by direct-message scenarios.
- `MATE_E2E_PUBLISH_TEXT_PREFIX`: optional prefix for publish scenarios.
- `MATE_E2E_TIMEOUT_SECONDS`: per-scenario timeout, default `900`.

The runner will not include an `allow_write` option. Running it means the user accepts real X write operations.

## CLI

Supported commands:

```bash
python main.py --all
python main.py --scenario local-api-publish
python main.py --environment remote
python main.py --capability api
python main.py --task-type dm
```

Filtering is simple AND filtering. For example, `--environment remote --capability api` runs only remote API scenarios.

## Scenario Model

Each scenario is an explicit data object, not a dynamically generated DSL:

```python
Scenario(
    id="local-api-publish",
    environment="local",
    capability="api",
    task_type="publish",
    execution_mode="api_only",
    browser_available=True,
    expected="success",
    expected_path="api",
)
```

Field meanings:

- `environment`: `local` or `remote`.
- `capability`: `extension` or `api`.
- `task_type`: `reply`, `publish`, `interact`, or `dm`.
- `execution_mode`: sent in `extra.execution_mode`.
- `browser_available`: passed to `TaskExecutionOptions`.
- `expected`: `success` or `failure`.
- `expected_path`: expected execution path when relevant.

Capability mapping:

- `capability=api` maps to `extra.execution_mode="api_only"`.
- `capability=extension` maps to `extra.execution_mode="extension_only"`.
- `environment=local` maps to `TaskExecutionOptions(browser_available=True)`.
- `environment=remote` maps to `TaskExecutionOptions(browser_available=False)`.

This uses existing SDK and Agent behavior without adding protocol fields.

## Scenario Matrix

| Scenario | Expected | Reason |
| --- | --- | --- |
| `local-extension-reply` | success | Browser extension supports replies |
| `local-extension-publish` | success | Extension can publish, although API is more reliable |
| `local-extension-interact` | success | Extension supports full interaction |
| `local-extension-dm` | failure | Extension does not support direct messages |
| `local-api-reply` | failure | X API does not support replies |
| `local-api-publish` | success | X API supports publishing |
| `local-api-interact` | success | X API supports limited interaction |
| `local-api-dm` | success | X API supports direct messages |
| `remote-extension-reply` | failure | Remote environment has no browser extension |
| `remote-extension-publish` | failure | Remote environment has no browser extension |
| `remote-extension-interact` | failure | Remote environment has no browser extension |
| `remote-extension-dm` | failure | Remote environment has no browser extension and extension cannot DM |
| `remote-api-reply` | failure | X API does not support replies |
| `remote-api-publish` | success | X API is the only remote publish path |
| `remote-api-interact` | success | X API is the only remote interaction path, with limits |
| `remote-api-dm` | success | X API is the only remote DM path |

Negative scenarios must still create real sessions and wait for the Agent to return a failure or rejection reason.

## Task Prompts

Each scenario uses a fixed prompt template. A per-scenario run ID is included so real X actions are traceable:

```text
Run ID: 20260512-153000-local-api-publish

Use the configured X account to publish one short test tweet.
The tweet must include this exact run id: 20260512-153000-local-api-publish.
Do not ask for additional confirmation unless the system requires authorization.
```

Task types:

- `reply`: reply to `MATE_E2E_TARGET_TWEET_URL`.
- `publish`: publish a short test tweet containing the run ID.
- `interact`: interact with `MATE_E2E_TARGET_TWEET_URL`, such as like or retweet.
- `dm`: send a direct message to `MATE_E2E_TARGET_X_USER` containing the run ID.

Prompts should be direct and deterministic. They should not ask the model to choose the task type.

## Execution Flow

For each selected scenario:

1. Build the task prompt.
2. Build `extra` with default marketing skills and `execution_mode`.
3. Include `marketing_product.product_id` when `MATE_E2E_PRODUCT_ID` is set.
4. Create a marketing session with `CreateSessionRequest`.
5. Fetch `session_info`.
6. Create `WebSocketClient`.
7. Create `TaskRunner`.
8. Run `run_interactive_session()` with `TaskExecutionOptions`.
9. Capture stdout and stderr while also writing to the terminal.
10. Classify the captured output.
11. Store the result and continue to the next scenario.

Scenarios run sequentially. This keeps real X account state and OAuth interactions easier to reason about.

## Authorization Handling

If the Agent emits `x_api_authorize`, the SDK prints an authorization URL and waits for user input. The E2E runner will not poll authorization status or fake completion.

Expected operator flow:

1. The runner prints the authorization URL.
2. The user opens the URL and completes OAuth.
3. The user returns to the terminal and presses Enter.
4. The current scenario continues.

This verifies the real SDK authorization recovery path.

## Output Capture

The runner will capture both stdout and stderr with a small `Tee` helper:

- write all output to the terminal
- keep the same output in memory for assertions

Each scenario result records:

- `scenario_id`
- `session_id`
- `environment`
- `capability`
- `task_type`
- `execution_mode`
- `browser_available`
- `expected`
- `status`
- `matched_reason`
- `started_at`
- `ended_at`
- `duration_seconds`
- `exception`

## Assertions

Assertions are marker-based and deliberately simple.

Success markers:

```python
SUCCESS_MARKERS = [
    "Task completed",
    "final answer",
    "session completed",
]
```

Authorization markers:

```python
AUTH_MARKERS = [
    "Open this URL to authorize X API access",
    "x_api_authorize",
]
```

Failure reason markers:

```python
FAILURE_REASON_MARKERS = {
    "api_reply_unsupported": ["API", "reply", "not support"],
    "extension_dm_unsupported": ["extension", "direct message", "not support"],
    "extension_unavailable": ["browser", "extension", "unavailable"],
}
```

Pass rules:

- Expected success passes when there is no exception, no timeout, no matched rejection reason, and a completion marker appears.
- Expected failure passes when the output includes the expected rejection reason or the final answer clearly states that the requested path is unavailable.
- Authorization output is not a failure by itself. The scenario continues after the user completes OAuth and presses Enter.

The runner will not call a model to judge output.

## Error Handling

- A single scenario exception records `ERROR` and does not stop the full run.
- Timeout records `TIMEOUT`.
- Assertion mismatch records `FAIL`.
- `KeyboardInterrupt` stops the run and writes partial results.
- Any non-pass status causes process exit code `1`.
- All pass statuses cause process exit code `0`.

## Console Output

Example summary:

```text
X Capability E2E Summary

PASS  local-extension-reply     expected=success  session=sess_...
PASS  local-api-reply           expected=failure  reason=api_reply_unsupported
FAIL  remote-api-publish        expected=success  actual=timeout
ERROR local-api-dm              APIError: ...
```

## JSON Output

Runtime output is written to `examples/x_capability_e2e/results/latest.json`:

```json
{
  "run_id": "20260512-153000",
  "started_at": "2026-05-12T15:30:00+08:00",
  "ended_at": "2026-05-12T16:10:00+08:00",
  "summary": {
    "passed": 14,
    "failed": 1,
    "errors": 1,
    "timeouts": 0
  },
  "results": [
    {
      "scenario_id": "local-api-publish",
      "session_id": "sess_...",
      "expected": "success",
      "status": "PASS",
      "matched_reason": null,
      "duration_seconds": 123.4
    }
  ]
}
```

## Review Notes

This design intentionally favors explicit data and simple control flow over extensibility. The scenario set is fixed because the source document defines a fixed 16-path matrix. Future capabilities should update this example only when the source decision matrix changes.
