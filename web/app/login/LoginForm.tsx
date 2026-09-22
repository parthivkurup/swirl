"use client";

import { useState } from "react";

export default function LoginForm() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const password = new FormData(e.currentTarget).get("password");
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (res.ok) {
      window.location.href = "/review";
    } else {
      const data = await res.json().catch(() => ({}));
      setError(data.error ?? "Login failed.");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-3">
      <input
        type="password"
        name="password"
        required
        autoFocus
        placeholder="Admin password"
        className="rounded border border-neutral-300 px-2 py-1"
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <button disabled={busy} className="rounded bg-neutral-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
        {busy ? "Signing in..." : "Sign in"}
      </button>
    </form>
  );
}
