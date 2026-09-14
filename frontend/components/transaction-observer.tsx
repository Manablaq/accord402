"use client";

import {
  FormEvent,
  useState,
} from "react";

type Observation = {
  txId: string;
  consensusStatus: string;
  consensusStatusCode: number;
  finalized: boolean;
  txExecutionResult: number;
  executionSucceeded: boolean;
  canonicalSuccess: boolean;
};

type ApiError = {
  error?: string;
  message?: string;
};

const TX_ID = /^0x[0-9a-fA-F]{64}$/;

export function TransactionObserver() {
  const [txId, setTxId] = useState("");
  const [result, setResult] =
    useState<Observation | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] =
    useState(false);

  async function observe(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const normalized = txId.trim();

    setResult(null);
    setError("");

    if (!TX_ID.test(normalized)) {
      setError(
        "Enter a 32-byte GenLayer transaction ID.",
      );
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `/api/tx/${normalized}`,
        {
          cache: "no-store",
        },
      );

      const payload =
        (await response.json()) as
          | Observation
          | ApiError;

      if (!response.ok) {
        const failed = payload as ApiError;

        throw new Error(
          failed.message ||
            failed.error ||
            "Observation failed",
        );
      }

      setResult(payload as Observation);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Observation failed",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section
      className="panel observer"
      aria-labelledby="observer-title"
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">
            Canonical transaction observer
          </p>

          <h2 id="observer-title">
            Finality is not execution success.
          </h2>
        </div>

        <span className="network-pill">
          Bradbury · 4221
        </span>
      </div>

      <p className="muted">
        Accord402 treats a transaction as
        canonically successful only when Bradbury
        reports <strong>Finalized</strong> and the
        receipt reports{" "}
        <strong>FINISHED_WITH_RETURN</strong>.
      </p>

      <form
        className="observer-form"
        onSubmit={observe}
      >
        <label htmlFor="tx-id">
          Transaction ID
        </label>

        <div className="observer-row">
          <input
            id="tx-id"
            value={txId}
            onChange={(event) =>
              setTxId(event.target.value)
            }
            placeholder="0x…"
            spellCheck={false}
            autoComplete="off"
          />

          <button
            type="submit"
            disabled={loading}
          >
            {loading
              ? "Observing…"
              : "Observe"}
          </button>
        </div>
      </form>

      {error ? (
        <p
          className="result-card danger"
          role="alert"
        >
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="result-grid">
          <article className="metric">
            <span>Consensus</span>
            <strong>
              {result.consensusStatus}
            </strong>
          </article>

          <article className="metric">
            <span>Finalized</span>
            <strong>
              {result.finalized ? "YES" : "NO"}
            </strong>
          </article>

          <article className="metric">
            <span>Execution result</span>
            <strong>
              {result.txExecutionResult}
            </strong>
          </article>

          <article className="metric">
            <span>Canonical success</span>
            <strong>
              {result.canonicalSuccess
                ? "YES"
                : "NO"}
            </strong>
          </article>
        </div>
      ) : null}
    </section>
  );
}
