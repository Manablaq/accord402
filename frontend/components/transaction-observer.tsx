"use client";

import {
  FormEvent,
  useEffect,
  useRef,
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

type TransactionObserverProps = {
  submittedTxId?: string;
  networkName: string;
  chainId: number;
  configReady: boolean;
  onCanonicalSuccess?: () => void;
};

function statusTone(result: Observation) {
  return result.canonicalSuccess
    ? "success"
    : result.finalized
      ? "warning"
      : "pending";
}

export function TransactionObserver({
  submittedTxId = "",
  networkName,
  chainId,
  configReady,
  onCanonicalSuccess,
}: TransactionObserverProps) {
  const [txId, setTxId] = useState("");
  const [result, setResult] = useState<Observation | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastChecked, setLastChecked] = useState("");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const notifiedTxRef = useRef("");

  async function loadObservation(normalized: string, showLoading = true) {
    if (showLoading) setLoading(true);

    try {
      const response = await fetch("/api/tx/" + normalized, {
        cache: "no-store",
      });
      const payload = (await response.json()) as Observation | ApiError;

      if (!response.ok) {
        const failed = payload as ApiError;
        throw new Error(
          failed.message || failed.error || "Observation failed",
        );
      }

      const observation = payload as Observation;
      setResult(observation);
      if (observation.canonicalSuccess && notifiedTxRef.current !== normalized) {
        notifiedTxRef.current = normalized;
        onCanonicalSuccess?.();
      }
      setLastChecked(
        new Intl.DateTimeFormat(undefined, {
          hour: "numeric",
          minute: "2-digit",
          second: "2-digit",
        }).format(new Date()),
      );
      setError("");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Observation failed",
      );
    } finally {
      if (showLoading) setLoading(false);
    }
  }

  async function observe(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = txId.trim();
    setResult(null);
    setError("");
    setLastChecked("");

    if (!TX_ID.test(normalized)) {
      setError("Enter a 32-byte GenLayer transaction ID.");
      return;
    }

    await loadObservation(normalized);
  }

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);

    if (result && !result.canonicalSuccess && TX_ID.test(txId.trim())) {
      timerRef.current = setInterval(() => {
        void loadObservation(txId.trim(), false);
      }, 15000);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [result, txId]);

  useEffect(() => {
    if (!TX_ID.test(submittedTxId)) return;
    setTxId(submittedTxId);
    setResult(null);
    setError("");
    void loadObservation(submittedTxId);
  }, [submittedTxId]);

  const tone = result ? statusTone(result) : "pending";

  return (
    <section className="observer panel" aria-labelledby="observer-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Canonical transaction observer</p>
          <h2 id="observer-title">Follow the exact transaction to finality.</h2>
        </div>
          <span className="network-pill">
          <span className="status-dot" /> {networkName} · {chainId}
        </span>
      </div>

      <p className="muted observer-intro">
        Accord402 never treats <strong>Accepted</strong> as payment proof. A
        consequential write is canonical only when {networkName} reports
        <strong> Finalized</strong> and the receipt reports
        <strong> FINISHED_WITH_RETURN</strong>.
      </p>

      <form className="observer-form" onSubmit={observe}>
        <label htmlFor="tx-id">Transaction ID</label>
        <div className="observer-row">
          <input
            id="tx-id"
            value={txId}
            onChange={(event) => setTxId(event.target.value)}
            placeholder={`0x… paste a ${networkName} transaction hash`}
            spellCheck={false}
            autoComplete="off"
            aria-describedby="observer-help"
          />
          <button type="submit" disabled={loading || !configReady}>
            {loading ? "Reading…" : "Observe transaction"}
          </button>
        </div>
        <span id="observer-help" className="form-help">
          Live reads refresh every 15 seconds while finality is pending.
        </span>
      </form>

      {error ? (
        <p className="result-card danger" role="alert">
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="observation-wrap" aria-live="polite">
          <div className={"observation-banner " + tone}>
            <span className="banner-icon">
              {result.canonicalSuccess ? "✓" : result.finalized ? "!" : "…"}
            </span>
            <div>
              <strong>
                {result.canonicalSuccess
                  ? "Canonical success"
                  : result.finalized
                    ? "Finalized with an execution issue"
                    : "Consensus is still being observed"}
              </strong>
              <span>
                {lastChecked ? "Last checked " + lastChecked : `Checking ${networkName}`}
              </span>
            </div>
          </div>
          <div className="result-grid">
            <article className="metric">
              <span>Consensus</span>
              <strong>{result.consensusStatus}</strong>
            </article>
            <article className="metric">
              <span>Finalized</span>
              <strong>{result.finalized ? "YES" : "NO"}</strong>
            </article>
            <article className="metric">
              <span>Execution result</span>
              <strong>{result.txExecutionResult}</strong>
            </article>
            <article className="metric">
              <span>Canonical success</span>
              <strong>{result.canonicalSuccess ? "YES" : "NO"}</strong>
            </article>
          </div>
        </div>
      ) : null}
    </section>
  );
}
