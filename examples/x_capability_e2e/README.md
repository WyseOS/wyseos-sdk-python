# X Capability E2E

This directory runs real Live E2E marketing sessions for the X capability matrix.

These scenarios execute real X actions such as publishing, replying, interacting, and sending DMs with the configured account. Use a dedicated test account and target content.

## Setup

```bash
cp mate.yaml.example mate.yaml
```

Configure credentials in `mate.yaml`, then set the runtime inputs:

```bash
export MATE_E2E_PRODUCT_ID="product-id"
export MATE_E2E_TARGET_TWEET_URL="https://x.com/user/status/123"
export MATE_E2E_TARGET_X_USER="target_user"
export MATE_E2E_PUBLISH_TEXT_PREFIX="Wyse E2E test"
export MATE_E2E_TIMEOUT_SECONDS="900"
export MATE_E2E_USER_INPUT_TIMEOUT_SECONDS="120"
```

API scenarios require a pre-authorized X connector. The runner does not handle interactive OAuth.

## Run

Run from this directory:

```bash
python main.py --all
python main.py --environment local --capability extension
python main.py --scenario local-api-publish
python main.py --task-type dm
```

## Results

The runner writes:

- `results/latest.json`: structured report with run metadata, summary, and scenario results.
- `results/latest.log`: detailed task output for the latest run.
