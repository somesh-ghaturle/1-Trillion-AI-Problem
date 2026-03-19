# Dashboard

Trust Control Center dashboard (Next.js) — UI for the $1 Trillion AI Problem demo.

## Running

Install and run in development:

```bash
cd dashboard
npm install
npm run dev
# Open http://localhost:3000
```

## Health API

The dashboard exposes a simple health API at `/api/health`:

- `GET /api/health` → `{ "layerActive": boolean }`
- `POST /api/health` → accepts `{ "layerActive": boolean }` to set state. If you POST an empty `{}` payload the API will toggle the current server state.

The demo persists the state to `dashboard/layer_state.json` (best-effort file persistence). In production, replace this with a proper configuration store.

### Production notes

- You can use Redis for production persistence by setting `REDIS_URL` in the environment (e.g. `redis://localhost:6379`). When provided the dashboard will store the boolean state under the key `semantic_layer:active`.
- Protect the control API by setting an `ADMIN_TOKEN` env var. The API expects an `Authorization: Bearer <ADMIN_TOKEN>` header on `POST /api/health` requests. If `ADMIN_TOKEN` is not set the API will allow writes (for local dev convenience).
- For local demos the state is also persisted to `layer_state.json` as a best-effort fallback.

## UI behavior

- The header shows a server-state badge (SSR fallback) and a client badge that polls `/api/health` every 5s.
- You can toggle the server-side layer state using the `Toggle Server Layer` button in the header (sends POST to `/api/health`).
This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Tests

Run the dashboard unit tests (requires Node):

```bash
cd dashboard
npm install
npm test
```

CI workflows should run both the Python tests in the repo root and the dashboard tests/build.

## Flow Diagram

The following Mermaid flowchart illustrates how the dashboard fits into the overall solution and how the Trust Control Center interacts with monitoring, validation, and the trust scoring engine.

```mermaid
flowchart LR
	A[Data Sources<br/>(Snowflake, Tableau, DBs, APIs)] --> B[Integration & Collection Layer<br/>(Connectors, ETL, Sync)]
	B --> C[Data Quality Validation Engine<br/>(Checks, Reconciliation, Anomaly Detection)]
	C --> D[Data Governance Layer<br/>(Metadata, Policies, Lineage)]
	C --> E[Monitoring & Analytics<br/>(Dashboards, Alerts)]
	D --> F[Trust Scoring Engine<br/>(Multi-dim Scores, History)]
	E --> F
	F --> G[AI/ML Consumption<br/>(Model Training, Predictions)]

	subgraph Control
		H[Trust Control Center UI<br/>(Health Map, Trust Cards, Simulator)]
		H -->|server control & metrics| E
		H -->|semantic toggle| C
	end
```

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
