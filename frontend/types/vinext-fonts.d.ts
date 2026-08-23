declare module "next" {
  export interface Metadata {
    [key: string]: unknown;
  }
}

declare module "next/font/google" {
  interface FontOptions {
    variable?: string;
    subsets?: string[];
    display?: string;
    weight?: string | string[];
  }

  interface LoadedFont {
    className: string;
    style: { fontFamily: string };
    variable: string;
  }

  export function Geist(options?: FontOptions): LoadedFont;
  export function Geist_Mono(options?: FontOptions): LoadedFont;
}

declare module "next/link" {
  interface LinkProps {
    href: string | { pathname?: string; query?: Record<string, string> };
    children?: import("react").ReactNode;
    className?: string;
    "aria-label"?: string;
  }

  const Link: import("react").ForwardRefExoticComponent<
    LinkProps & import("react").RefAttributes<HTMLAnchorElement>
  >;
  export default Link;
}

declare module "next/navigation" {
  interface AppRouter {
    push(href: string): void;
    replace(href: string): void;
    refresh(): void;
    back(): void;
    forward(): void;
  }

  export function usePathname(): string;
  export function useRouter(): AppRouter;
}

declare module "next/headers" {
  export function headers(): Promise<Headers>;
}
