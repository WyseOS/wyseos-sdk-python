# X Capability E2E

This directory runs real Live E2E marketing sessions for the X capability matrix.

The automatic runner covers 12 SDK-side scenarios:

- `local/remote`
- `api/extension`
- `reply/publish/interact`

It does not cover messaging flows or `auto` mode.

## Setup

```bash
cp mate.yaml.example mate.yaml
```

Configure credentials in `mate.yaml`, then set the runtime inputs:

```bash
export MATE_E2E_PRODUCT_ID="product-id"
export MATE_E2E_TARGET_TWEET_URL="https://x.com/user/status/123"
export MATE_E2E_PUBLISH_TEXT_PREFIX="Wyse E2E test"
export MATE_E2E_TIMEOUT_SECONDS="900"
export MATE_E2E_USER_INPUT_TIMEOUT_SECONDS="120"
```

API scenarios require a pre-authorized X connector. The runner does not handle interactive OAuth.

## Run

```bash
python main.py --all
python main.py --capability extension
python main.py --environment remote
python main.py --task-type reply
python main.py --scenario local-api-publish
```

## Results and Execution Evidence

The runner collects structural evidence directly from `TaskResult` without intercepting standard console output:

- `results/latest.json`: Structured abstract report containing metadata, pass/fail summaries, and timing metrics.
- `results/latest.log`: Deep debugging artifact capturing exact `final_answer`, `error` stacktraces, and detailed agent `execution_logs`.

## Manual smoke

These checks are not covered by the automatic SDK runner. Run them from the agent repository.

1. `api_only + reply=10`
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode api_only --task "只处理当前会话中的待回复推文"
```
Expected: no entry guard; reply returns `REPLY_API_UNSUPPORTED`; pending replies remain.

2. `api_only + interact=5, draft=10 + missing identity`
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode api_only
```
Expected: `ACCOUNT_IDENTIFIER_REQUIRED` with precise user-facing wording.

3. `api_only + interact=5, draft=10 + ready identity + authorized credential`
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode api_only --x-account <x_username_or_id>
```
Expected: normal X API execution.

4. `auto + extension disconnected + reply=10`
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode auto
```
Expected: `EXTENSION_REQUIRED`.

5. `auto + extension connected + draft=10`, then close the extension once
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode auto --x-account <x_username_or_id> --task "只发布当前会话中的待发布推文草稿"
```
Expected: plan A exits cleanly and plan B takes over.

6. `extension_only + extension connected + reply=10 + partial failures`
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode extension_only
```
Expected: user-facing failures are not misclassified as extension-required.

7. `extension_only + extension disconnected`
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode extension_only
```
Expected: cmd fails fast.

8. `api_only` popup suppression
```bash
python3 cmd/launch_x_browser.py --session-id <sid> --user-id <uid> --execution-mode api_only --x-account <x_username_or_id>
```
Expected: no popup creation log and no `TASK_STARTED_DEFAULT`.
