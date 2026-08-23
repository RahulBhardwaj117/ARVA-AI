import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { AppShell } from "@/components/app-shell";
import type { User } from "@/lib/types";

vi.mock("next/navigation", () => ({
  usePathname: () => "/simulation",
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

const user: User = {
  id: "user-1",
  organization_id: "org-1",
  name: "ARVA Administrator",
  email: "admin@arva.local",
  role: "administrator",
  is_active: true,
  last_login_at: null,
  organization: {
    id: "org-1",
    name: "ARVA Labs",
    slug: "arva-labs",
    deployment_mode: "simulation",
  },
};

describe("AppShell", () => {
  it("exposes every operational navigation surface", () => {
    render(
      <AppShell user={user}>
        <p>Control content</p>
      </AppShell>,
    );

    expect(screen.getByRole("link", { name: /command center/i })).toHaveAttribute(
      "href",
      "/dashboard",
    );
    expect(screen.getByRole("link", { name: /risk center/i })).toHaveAttribute(
      "href",
      "/risks",
    );
    expect(screen.getByRole("link", { name: /model monitoring/i })).toHaveAttribute(
      "href",
      "/models",
    );
    expect(screen.getByRole("link", { name: /audit log/i })).toHaveAttribute(
      "href",
      "/audit",
    );
    expect(screen.getByRole("link", { name: /simulation/i })).toHaveClass("active");
  });
});

