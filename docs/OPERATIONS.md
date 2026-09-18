# Accord402 operations runbook

This runbook is for contributors who need to verify the contracts, run the
Bradbury console, or publish the frontend. It deliberately separates local
build evidence from live-chain evidence.

## Prerequisites

- Foundry with the version expected by `foundry.toml`.
- Python with the development dependencies from `requirements-lock.txt`.
- Node.js 24.x and npm 11.x for the frontend.
- GenLayer CLI/linter for adjudicator schema checks.
- A funded Bradbury wallet only when a live write is explicitly required.

Never place a wallet private key, issuer private key, or Vercel credential in
the repository or in `frontend/.env.local`.

## Verification sequence

Run the deterministic checks first:

```bash
forge build --root .
forge test --root .
python -m py_compile contracts/Accord402Adjudicator.py
genvm-lint check contracts/Accord402Adjudicator.py --json
```

Then verify the frontend independently:

```bash
cd frontend
npm ci
npm run check
npm run dev
```

The frontend build must complete without configuration errors. Wallet actions
must remain disabled if any public deployment variable is missing or disagrees
with the deployed Core/Registry limits.

## Frontend configuration

Copy the checked-in template and fill every value for the target network:

```bash
cp frontend/.env.example frontend/.env.local
```

For Bradbury, the public values bind the console to chain `4221`, the
Bradbury RPC/explorer, the deployed Core/Registry/Adjudicator/Vault addresses,
the canonical source fingerprint, and the frozen protocol limits. The frontend
must never contain signing keys or issuer secrets.

## Vercel deployment

The Vercel project is `accord402` and the production alias is
[accord402.vercel.app](https://accord402.vercel.app). From `frontend/`:

```bash
vercel pull --yes --environment=production
vercel build --prod
vercel deploy --prebuilt --prod
```

`frontend/vercel.json` declares the Next.js framework so Vercel produces the
correct serverless and static output rather than looking for a `public/`
directory.

After deployment:

```bash
vercel inspect accord402.vercel.app
vercel curl / --deployment accord402.vercel.app
vercel curl /api/covenant/1 --deployment accord402.vercel.app
```

The final browser check should confirm the page title, Bradbury network label,
canonical contract address, covenant read surface, and theme toggle. A
successful HTML response alone is not enough if the page reports a configuration
error.

## Live Bradbury verification

The deployed contract graph is listed in the root README. A live lifecycle
smoke run should use a fresh, small test covenant and record:

1. Open/fund transaction and covenant ID.
2. Provider acceptance.
3. Timestamp-exact delivery and evidence submission.
4. Buyer challenge with ordered criterion IDs.
5. Adjudicator transaction ID, consensus outcome, and execution result.
6. Finalized callback processing.
7. Settlement authorization and the recipient balance delta.
8. A repeat settlement attempt proving duplicate-claim resistance.

An `Accepted` consensus result is not final settlement. The canonical result
must be finalized and must have execution result `FINISHED_WITH_RETURN`.
Persist transaction IDs and block references in the deployment evidence
directory; do not rely on screenshots as the only evidence.

## Troubleshooting

### The console shows a configuration error

Check that every key in `frontend/.env.example` exists and that the address,
chain ID, source fingerprint, replay scope, repair mask, and protocol limits
match the deployed graph. Restart the dev server after changing environment
files.

### A transaction is accepted but the UI does not report success

This is expected until Bradbury reports `Finalized` and the execution receipt
reports `FINISHED_WITH_RETURN`. Continue observing the original transaction ID;
do not submit a replacement transaction solely because finality is delayed.

### A covenant is `REVIEW_RETRY_REQUIRED`

This is a non-economic intermediate outcome for a transient or non-attributable
review failure. Retry only while the retry window and review-generation limits
permit it. If the absolute dispute deadline or generation limit is reached,
follow the neutral expiry path defined in `STATE_MACHINE_V1.md`.

### A Vercel login code cannot be verified

Issue a fresh device code from the same authenticated CLI process and do not
reuse an expired code. Confirm that the CLI can resolve `vercel.com` before
retrying the browser step.
