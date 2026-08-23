import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  Cpu,
  Gauge,
  GitCompareArrows,
  Radar,
  ShieldCheck,
  Sparkles,
  Waypoints,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Autonomous infrastructure decisions",
  description:
    "ARVA AI predicts infrastructure pressure, evaluates candidate futures and explains the safest action.",
};

const decisionLoop = [
  { label: "Observe", detail: "Telemetry", icon: Radar },
  { label: "Predict", detail: "Forecasts + risk", icon: BrainCircuit },
  { label: "Compare", detail: "Candidate futures", icon: GitCompareArrows },
  { label: "Govern", detail: "Policy validation", icon: ShieldCheck },
  { label: "Act", detail: "Approve or automate", icon: Waypoints },
];

const principles = [
  {
    eyebrow: "Simulation first",
    title: "Explore consequences before touching infrastructure.",
    copy: "A digital twin gives every candidate plan a measurable cost, performance and reliability outcome.",
    icon: Cpu,
  },
  {
    eyebrow: "Explainable by design",
    title: "Every action carries evidence, trade-offs and confidence.",
    copy: "Operators see what changed, which constraints mattered and why ARVA selected one future over another.",
    icon: Sparkles,
  },
  {
    eyebrow: "Policy governed",
    title: "Autonomy stays inside organizational guardrails.",
    copy: "Approval gates, role boundaries and explicit policies turn recommendations into controlled action.",
    icon: ShieldCheck,
  },
];

export default function Home() {
  return (
    <main className="site-shell">
      <header className="site-header">
        <Link href="/" className="brand" aria-label="ARVA AI home">
          <span className="brand-mark" aria-hidden="true">
            A
          </span>
          <span>
            <strong>ARVA</strong>
            <small>AUTONOMOUS DECISION INTELLIGENCE</small>
          </span>
        </Link>
        <nav className="site-nav" aria-label="Primary navigation">
          <a href="#platform">Platform</a>
          <a href="#loop">Decision loop</a>
          <span className="phase-badge">
            <span className="pulse-dot" />
            Closed loop online
          </span>
          <Link href="/login" className="button button-compact button-outline">
            Operator sign in
          </Link>
        </nav>
      </header>

      <section className="hero" id="platform">
        <div className="hero-copy">
          <div className="eyebrow">
            <span>Autonomous AI infrastructure optimization</span>
            <span className="eyebrow-line" />
          </div>
          <h1>
            Don&apos;t just detect the problem.
            <span>Decide what happens next.</span>
          </h1>
          <p className="hero-lede">
            ARVA predicts compute pressure, evaluates possible responses and
            selects the best policy-compliant action—before bottlenecks become
            outages.
          </p>
          <div className="hero-actions">
            <Link href="/login" className="button button-primary">
              Enter control plane <ArrowRight size={17} />
            </Link>
            <a href="#loop" className="button button-ghost">
              Explore the decision loop
            </a>
          </div>
          <div className="trust-row" aria-label="Platform properties">
            <span>
              <CheckCircle2 size={15} /> Simulation first
            </span>
            <span>
              <CheckCircle2 size={15} /> Explainable
            </span>
            <span>
              <CheckCircle2 size={15} /> Policy governed
            </span>
          </div>
        </div>

        <div className="hero-console" aria-label="ARVA decision engine overview">
          <div className="console-topbar">
            <div className="console-dots" aria-hidden="true">
              <i />
              <i />
              <i />
            </div>
            <span>ARVA / DECISION ENGINE</span>
            <span className="console-live">CLOSED LOOP</span>
          </div>
          <div className="console-grid">
            <div className="signal-panel">
              <span className="panel-label">CLOSED-LOOP CONTROL</span>
              <div className="signal-orbit" aria-hidden="true">
                <div className="orbit orbit-one" />
                <div className="orbit orbit-two" />
                <div className="orbit orbit-three" />
                <div className="orbit-core">
                  <Gauge size={28} />
                  <small>ARVA</small>
                </div>
                <i className="orbit-node node-a" />
                <i className="orbit-node node-b" />
                <i className="orbit-node node-c" />
                <i className="orbit-node node-d" />
              </div>
              <div className="signal-foot">
                <span>OBSERVE</span>
                <span>PREDICT</span>
                <span>OPTIMIZE</span>
                <span>ACT</span>
              </div>
            </div>
            <div className="console-feed">
              <div className="feed-head">
                <span>CONTROL PLANE</span>
                <span>LIVE MVP</span>
              </div>
              <div className="feed-item active">
                <span className="feed-index">01</span>
                <span>
                  <strong>Identity boundary</strong>
                  <small>JWT + Argon2 + tenant-scoped roles</small>
                </span>
                <b>READY</b>
              </div>
              <div className="feed-item">
                <span className="feed-index">02</span>
                <span>
                  <strong>Persistent state</strong>
                  <small>PostgreSQL with versioned migrations</small>
                </span>
                <b>READY</b>
              </div>
              <div className="feed-item">
                <span className="feed-index">03</span>
                <span>
                  <strong>Runtime fabric</strong>
                  <small>API, worker and Redis readiness</small>
                </span>
                <b>READY</b>
              </div>
              <div className="console-foot">
                <span>Observe → predict → decide → recover</span>
                <span>COMPLETE LOOP</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="decision-loop-section" id="loop">
        <div className="section-heading">
          <span className="section-number">01</span>
          <div>
            <span className="eyebrow">The intelligence loop</span>
            <h2>From signal to governed action.</h2>
          </div>
          <p>
            ARVA closes the gap between infrastructure observability and safe,
            measurable intervention.
          </p>
        </div>
        <div className="loop-track">
          {decisionLoop.map(({ label, detail, icon: Icon }, index) => (
            <article className="loop-step" key={label}>
              <div className="loop-step-head">
                <span>{String(index + 1).padStart(2, "0")}</span>
                <Icon size={21} />
              </div>
              <strong>{label}</strong>
              <small>{detail}</small>
            </article>
          ))}
        </div>
      </section>

      <section className="principles-section">
        {principles.map(({ eyebrow, title, copy, icon: Icon }) => (
          <article className="principle-card" key={eyebrow}>
            <div className="principle-icon">
              <Icon size={22} />
            </div>
            <span>{eyebrow}</span>
            <h3>{title}</h3>
            <p>{copy}</p>
          </article>
        ))}
      </section>

      <footer className="site-footer">
        <span>ARVA AI</span>
        <p>Predict demand. Optimize compute. Automate intelligent decisions.</p>
        <span>SIMULATION-FIRST MVP / ONLINE</span>
      </footer>
    </main>
  );
}
