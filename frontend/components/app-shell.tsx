"use client";

import {
  Bell,
  Boxes,
  BrainCircuit,
  ChevronRight,
  CircleUserRound,
  ClipboardCheck,
  FlaskConical,
  Gauge,
  LayoutDashboard,
  LogOut,
  Server,
  Settings,
  ShieldCheck,
  Workflow,
  TriangleAlert,
  ScrollText,
  History,
  Menu,
  Network,
  Radio,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { logout } from "@/lib/api";
import type { User } from "@/lib/types";
import { useAuthStore } from "@/stores/auth";

const navigation = [
  {
    label: "Operate",
    items: [
      { label: "Command center", icon: LayoutDashboard, href: "/dashboard" },
      { label: "Infrastructure", icon: Server, href: "/infrastructure" },
      { label: "Node explorer", icon: Network, href: "/nodes" },
      { label: "Workloads", icon: Boxes, href: "/workloads" },
      { label: "Simulation", icon: Workflow, href: "/simulation" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { label: "Forecasting", icon: BrainCircuit, href: "/forecasting" },
      { label: "Risk center", icon: TriangleAlert, href: "/risks" },
      { label: "Decisions", icon: ClipboardCheck, href: "/decisions" },
      { label: "Experiments", icon: FlaskConical, href: "/experiments" },
      { label: "Model monitoring", icon: Gauge, href: "/models" },
    ],
  },
  {
    label: "Governance",
    items: [
      { label: "Replay", icon: History, href: "/replay" },
      { label: "Policies", icon: ShieldCheck, href: "/policies" },
      { label: "Audit log", icon: ScrollText, href: "/audit" },
    ],
  },
];

export function AppShell({
  user,
  children,
}: {
  user: User;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [navigationOpen, setNavigationOpen] = useState(false);
  const clearSession = useAuthStore((state) => state.clearSession);

  useEffect(() => {
    setNavigationOpen(false);
  }, [pathname]);

  async function signOut() {
    try {
      await logout();
    } finally {
      clearSession();
      router.replace("/login");
    }
  }

  return (
    <div className="control-plane">
      <aside
        className={`sidebar ${navigationOpen ? "is-open" : ""}`}
        aria-label="Application navigation"
      >
        <div className="sidebar-head">
          <Link href="/" className="brand sidebar-brand" aria-label="ARVA AI home">
            <span className="brand-mark" aria-hidden="true">
              A
            </span>
            <span>
              <strong>ARVA</strong>
              <small>CONTROL PLANE</small>
            </span>
          </Link>
          <button
            className="sidebar-close"
            type="button"
            onClick={() => setNavigationOpen(false)}
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        </div>

        <div className="sidebar-mode">
          <span className="pulse-dot" />
          <span>
            <small>DEPLOYMENT MODE</small>
            <strong>{user.organization.deployment_mode.replaceAll("_", " ")}</strong>
          </span>
        </div>

        <nav className="sidebar-nav" aria-label="Control plane">
          {navigation.map((group) => (
            <div className="nav-group" key={group.label}>
              <span className="nav-label">{group.label}</span>
              {group.items.map(({ label, icon: Icon, href }) => {
                const active =
                  pathname === href || pathname.startsWith(`${href}/`);
                return (
                  <Link
                    key={label}
                    href={href}
                    className={active ? "active" : ""}
                    aria-current={active ? "page" : undefined}
                  >
                    <Icon size={17} />
                    <span>{label}</span>
                    <ChevronRight size={14} />
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <Link href="/settings">
            <Settings size={17} />
            <span>Settings</span>
            <ChevronRight size={14} />
          </Link>
          <div className="sidebar-user">
            <span className="user-avatar" aria-hidden="true">
              <CircleUserRound size={25} />
            </span>
            <span>
              <strong>{user.name}</strong>
              <small>{user.role.replaceAll("_", " ")}</small>
            </span>
            <button type="button" onClick={() => void signOut()} aria-label="Sign out">
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      <button
        className={`sidebar-scrim ${navigationOpen ? "is-visible" : ""}`}
        type="button"
        onClick={() => setNavigationOpen(false)}
        aria-label="Close navigation"
        tabIndex={navigationOpen ? 0 : -1}
      />

      <div className="workspace">
        <header className="workspace-header">
          <div className="workspace-header-leading">
            <button
              className="mobile-nav-trigger"
              type="button"
              onClick={() => setNavigationOpen(true)}
              aria-label="Open navigation"
              aria-expanded={navigationOpen}
            >
              <Menu size={19} />
            </button>
            <span className="workspace-product-icon" aria-hidden="true">
              <Gauge size={16} />
            </span>
            <div className="workspace-breadcrumb">
              <small>ARVA OPERATIONS</small>
              <span>
                {pathname.split("/")[1]?.replaceAll("-", " ") || "Overview"}
              </span>
            </div>
          </div>
          <div className="workspace-header-actions">
            <span className="workspace-clock">
              <Radio size={13} />
              Live digital twin
            </span>
            <button
              className="notification-button"
              type="button"
              aria-label="Notifications"
              title="No unread notifications"
            >
              <Bell size={17} />
            </button>
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}
