# Contributing to Workboard

Workboard is a local, view-only companion built with Python's standard library and browser JavaScript. There is no build step, package installation or hosted backend. Use synthetic data for examples and screenshots:

```sh
python3 server.py --demo --port 43128
```

Open `http://127.0.0.1:43128`. Demo mode does not read Codex databases, conversation files, Git repositories, global instructions or GitHub. It exercises current, missing and stale session telemetry and changed checkouts. It is a preview, not a source of real project status.

Run relevant checks with existing Python and Node:

```sh
python3 -m unittest -q
node --check static/app.js
node --check static/signals.js
node test_focus.cjs
node test_delivery_ui.cjs
node test_cleanup.cjs
node test_pwa.cjs
node test_signals.cjs
```

The HTTP tests bind a temporary loopback port. Check responsive changes at 320, 360 and 420 px, plus an expanded desktop window. Exercise unknown/stale states, keyboard navigation, pause and privacy mode. Keep personal screenshots, logs, databases, local configuration and tokens out of changes. Use synthetic reproductions in issues.

## Boundaries and adapters

`server.py` owns bounded, read-only Codex/Git discovery and fixed HTTP routes. `telemetry.py` allowlists numeric Codex usage observations from those existing log reads. `delivery.py` owns cached GitHub evidence. `configuration.py` selects display scope; it cannot execute code or introduce discovery roots. `static/signals.js` contains pure conservative signal rules; presentation lives in `static/app.js`.

`doctor.py` provides read-only first-run diagnostics without scanning projects or logging in. `service.py` records selected executable/source paths for optional macOS login startup; never copy token environment variables into its plist.

Provider extensions must declare coverage and timestamp observations. Distinguish last context usage, accumulated token consumption, account allowance and monetary billing. Missing is not zero; old snapshots are not current. Do not combine snapshots whose account identity is unverified. Do not scrape authentication secrets, execute external helpers, install dependencies or add an LLM call for classification. Unsupported providers remain unknown until an explicit, tested adapter exists.

Never introduce source-project or Codex database writes, automatic chat rollover, silent message submission or cleanup execution. A shared path is not ownership. A merge is not proof of deployment or completion of every acceptance criterion. Keep source-backed tasks in the existing project ledger. See CHARTER.md for durable product boundaries. TASKS.md is the local canonical ledger; it and tasks/lessons.md are intentionally untracked. New contributors may create their own local TASKS.md using the same filename without publishing personal workflow history.

## Public contributions

Workboard is created by [Sam Daoud](https://wisamdaoud.com) and BlueLux and distributed under MIT. Submit only work you have the right to license under those terms. Use synthetic examples and check both staged content and history for private material. Security findings should use the private channel in [SECURITY.md](SECURITY.md), not public issues.

Supported platform coverage and installation are documented in README.md. There is no automatic CI or signed distribution pipeline yet; run the listed checks locally and include actual results with a proposed change. Keep changes focused and preserve unknown source state.
