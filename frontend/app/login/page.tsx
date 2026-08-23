import type { Metadata } from "next";
import Link from "next/link";
import { Activity, Database, LockKeyhole, Radio } from "lucide-react";

import { LoginForm } from "@/components/login-form";

export const metadata: Metadata = {
  title: "Operator sign in",
};

export default function LoginPage() {
  return (
    <main className="auth-page">
      <section className="auth-brand-panel">
        <Link href="/" className="brand" aria-label="Return to ARVA AI home">
          <span className="brand-mark" aria-hidden="true">
            A
          </span>
          <span>
            <strong>ARVA</strong>
            <small>AUTONOMOUS DECISION INTELLIGENCE</small>
          </span>
        </Link>

        <div className="auth-message">
          <span className="auth-kicker">CONTROL PLANE / ACCESS 01</span>
          <h2>
            Intelligence is useful.
            <span>Governed intelligence is operational.</span>
          </h2>
          <p>
            Enter the complete simulation-first control plane for forecasts,
            risks, alternative plans, governed decisions, incidents and
            measured recovery.
          </p>
        </div>

        <div className="auth-system-grid" aria-label="Platform status">
          <div>
            <LockKeyhole size={17} />
            <span>AUTH</span>
            <strong>JWT / ARGON2</strong>
          </div>
          <div>
            <Database size={17} />
            <span>STATE</span>
            <strong>POSTGRESQL</strong>
          </div>
          <div>
            <Radio size={17} />
            <span>EVENTS</span>
            <strong>REDIS READY</strong>
          </div>
          <div>
            <Activity size={17} />
            <span>MODE</span>
            <strong>SIMULATION</strong>
          </div>
        </div>
      </section>

      <section className="auth-form-panel">
        <div className="auth-panel-meta">
          <span>ARVA / SECURE SESSION</span>
          <Link href="/">Exit</Link>
        </div>
        <LoginForm />
        <p className="auth-legal">
          Access is logged and constrained by organization role. Development
          credentials are configurable through the seed environment.
        </p>
      </section>
    </main>
  );
}
