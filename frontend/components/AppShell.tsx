"use client";

import { AuthProvider } from "@/contexts/AuthContext";
import { AppNav } from "@/components/AppNav";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <AppNav />
      {children}
    </AuthProvider>
  );
}
