import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { LoginForm } from "@/components/login-form";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

describe("LoginForm", () => {
  it("renders accessible credential controls and the sign-in action", () => {
    render(<LoginForm />);

    expect(screen.getByLabelText("Operator email")).toHaveValue(
      "admin@arva.local",
    );
    expect(screen.getByLabelText("Password")).toHaveAttribute("type", "password");
    expect(
      screen.getByRole("button", { name: "Sign in securely" }),
    ).toBeEnabled();
  });
});

