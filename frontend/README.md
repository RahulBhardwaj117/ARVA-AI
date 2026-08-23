# ARVA AI control plane

Vinext (the Next.js API surface on Vite), React 19, TypeScript, Tailwind CSS,
TanStack Query, Zustand,
Recharts, React Hook Form, Zod, and Lucide UI for the complete ARVA operational
surface.

Routes include landing, login, command center, infrastructure, cluster detail,
node explorer, workloads, forecasting, risks, decisions, simulation,
experiments, replay, policies, model monitoring, audit, and settings.

```bash
npm install
npm run dev
npm test
npm run lint
npm run build
```

Set `NEXT_PUBLIC_API_URL` to the browser-reachable FastAPI origin.
Authenticated pages consume the organization WebSocket event stream and retain
bounded REST polling as a reconnect fallback.
