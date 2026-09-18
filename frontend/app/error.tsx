"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Accord402 application error", error);
  }, [error]);

  return (
    <main className="error-shell">
      <p className="eyebrow">Accord402</p>
      <h1>Something interrupted the console.</h1>
      <p className="muted">
        The page could not finish rendering. Retry the console before taking
        any wallet action.
      </p>
      <button className="button button-primary" type="button" onClick={reset}>
        Retry console
      </button>
    </main>
  );
}
