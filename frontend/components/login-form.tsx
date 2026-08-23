"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Eye, EyeOff, LoaderCircle, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import { ApiError, login } from "@/lib/api";
import { loginSchema, type LoginInput } from "@/lib/schemas";
import { useAuthStore } from "@/stores/auth";

export function LoginForm() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const { hydrate, setSession } = useAuthStore();
  const {
    register,
    handleSubmit,
    formState: { dirtyFields, errors, isSubmitting },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    mode: "onChange",
    defaultValues: {
      email: "admin@arva.local",
      password: "",
    },
  });

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
      const response = await login(values);
      setSession(response.access_token, response.user);
      router.push("/dashboard");
    } catch (error) {
      setServerError(
        error instanceof ApiError
          ? error.message
          : "Sign in failed. Please try again.",
      );
    }
  });

  return (
    <form className="login-form" onSubmit={onSubmit} noValidate>
      <div className="form-heading">
        <span className="eyebrow">Secure operator access</span>
        <h1>Enter the control plane.</h1>
        <p>
          Authenticate against the ARVA API to access organization-scoped
          infrastructure, simulation and governed decision controls.
        </p>
      </div>

      {serverError ? (
        <div className="form-error" role="alert">
          <ShieldCheck size={17} />
          <span>{serverError}</span>
        </div>
      ) : null}

      <div className="field-group">
        <label htmlFor="email">Operator email</label>
        <input
          id="email"
          type="email"
          autoComplete="username"
          className={dirtyFields.email && !errors.email ? "is-valid" : ""}
          aria-invalid={Boolean(errors.email)}
          aria-describedby={errors.email ? "email-error" : undefined}
          {...register("email")}
        />
        {errors.email ? (
          <small className="field-error" id="email-error">
            {errors.email.message}
          </small>
        ) : null}
      </div>

      <div className="field-group">
        <div className="field-label-row">
          <label htmlFor="password">Password</label>
          <span>Argon2 protected</span>
        </div>
        <div className="password-field">
          <input
            id="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            autoFocus
            className={
              dirtyFields.password && !errors.password ? "is-valid" : ""
            }
            aria-invalid={Boolean(errors.password)}
            aria-describedby={errors.password ? "password-error" : undefined}
            {...register("password")}
          />
          <button
            type="button"
            onClick={() => setShowPassword((current) => !current)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            aria-pressed={showPassword}
          >
            {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
          </button>
        </div>
        {errors.password ? (
          <small className="field-error" id="password-error">
            {errors.password.message}
          </small>
        ) : null}
      </div>

      <button
        className="button button-primary login-submit"
        disabled={isSubmitting}
      >
        {isSubmitting ? (
          <>
            <LoaderCircle className="spin" size={17} /> Authenticating
          </>
        ) : (
          <>
            Sign in securely <ArrowRight size={17} />
          </>
        )}
      </button>

      <div className="demo-credentials">
        <span>Development seed</span>
        <code>admin@arva.local</code>
        <code>ArvaDemo!2026</code>
      </div>
    </form>
  );
}
