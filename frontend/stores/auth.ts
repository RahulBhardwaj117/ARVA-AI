"use client";

import { create } from "zustand";
import type { User } from "@/lib/types";

const SESSION_KEY = "arva-session";

interface StoredSession {
  token: string;
  user: User;
}

interface AuthState {
  token: string | null;
  user: User | null;
  hydrated: boolean;
  hydrate: () => void;
  setSession: (token: string, user: User) => void;
  clearSession: () => void;
  setUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  hydrated: false,
  hydrate: () => {
    if (typeof window === "undefined") {
      return;
    }
    const raw = window.sessionStorage.getItem(SESSION_KEY);
    if (raw === null) {
      set({ hydrated: true });
      return;
    }
    try {
      const session = JSON.parse(raw) as StoredSession;
      set({ token: session.token, user: session.user, hydrated: true });
    } catch {
      window.sessionStorage.removeItem(SESSION_KEY);
      set({ token: null, user: null, hydrated: true });
    }
  },
  setSession: (token, user) => {
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(SESSION_KEY, JSON.stringify({ token, user }));
    }
    set({ token, user, hydrated: true });
  },
  clearSession: () => {
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(SESSION_KEY);
    }
    set({ token: null, user: null, hydrated: true });
  },
  setUser: (user) => {
    if (typeof window !== "undefined") {
      const token = useAuthStore.getState().token;
      if (token) {
        window.sessionStorage.setItem(SESSION_KEY, JSON.stringify({ token, user }));
      }
    }
    set({ user });
  },
}));

