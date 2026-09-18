"use client";

import { FormEvent, useEffect, useState } from "react";

import { configuredCovenantId } from "@/lib/client";

export type Criterion = {
  criterionId: string;
  criterionText: string;
};

export type Covenant = {
  covenantId: string;
  buyer: string;
  provider: string;
  fundedAmount: string;
  outstandingAmount: string;
  state: string;
  openedAt: string;
  acceptanceDeadline: string;
  deliveryDeadline: string;
  challengeDeadline: string;
  repairDeadline: string;
  retryDeadline: string;
  absoluteDisputeDeadline: string;
  maxReviewGenerations: number;
  reviewGeneration: number;
  adjudicationDecision: string;
  failureClassification: string;
  settlementDirection: string;
  settlementClaimed: boolean;
  deliveryPayload: string;
  challengeClaim: string;
  requiredCorroborationCount: number;
  criteria?: Criterion[];
};

type ApiResponse = {
  covenant?: Covenant;
  criteria?: Criterion[];
  error?: string;
  message?: string;
};

const DEFAULT_ID = configuredCovenantId;
const GEN_UNIT = BigInt("1000000000000000000");

type CaseLookupProps = {
  onCovenantLoaded: (covenant: Covenant | null) => void;
  refreshToken?: number;
  networkName: string;
  configReady: boolean;
};

function formatGen(wei: string) {
  try {
    const value = BigInt(wei);
    const whole = value / GEN_UNIT;
    const fraction = (value % GEN_UNIT)
      .toString()
      .padStart(18, "0")
      .replace(/0+$/, "");
    return fraction ? whole.toString() + "." + fraction.slice(0, 4) + " GEN" : whole + " GEN";
  } catch {
    return "Unavailable";
  }
}

function formatState(state: string) {
  return state
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatTime(timestamp: string) {
  const value = Number(timestamp);
  if (!Number.isFinite(value) || value === 0) return "Not recorded";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value * 1000));
}

function shorten(value: string) {
  return value ? value.slice(0, 8) + "…" + value.slice(-6) : "Not recorded";
}

export function CaseLookup({ onCovenantLoaded, refreshToken = 0, networkName, configReady }: CaseLookupProps) {
  const [id, setId] = useState(DEFAULT_ID);
  const [covenant, setCovenant] = useState<Covenant | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastRead, setLastRead] = useState("");

  async function loadCase(covenantId: string, showLoading = true) {
    if (showLoading) setLoading(true);
    try {
      const response = await fetch("/api/covenant/" + covenantId, {
        cache: "no-store",
      });
      const payload = (await response.json()) as ApiResponse;
      if (!response.ok) {
        throw new Error(
          payload.message ||
            (payload.error === "COVENANT_NOT_FOUND"
              ? "No covenant exists with that ID."
              : `Could not read this covenant from ${networkName}.`),
        );
      }
      const loaded = payload.covenant
        ? { ...payload.covenant, criteria: payload.criteria || [] }
        : null;
      setCovenant(loaded);
      onCovenantLoaded(loaded);
      setLastRead(
        new Intl.DateTimeFormat(undefined, {
          hour: "numeric",
          minute: "2-digit",
          second: "2-digit",
        }).format(new Date()),
      );
      setError("");
    } catch (caught) {
      setCovenant(null);
      onCovenantLoaded(null);
      setError(caught instanceof Error ? caught.message : "Covenant read failed.");
    } finally {
      if (showLoading) setLoading(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = id.trim();
    if (!configReady) {
      setError("Frontend configuration is incomplete. Add the required public environment variables before reading a covenant.");
      return;
    }
    if (!/^[1-9][0-9]*$/.test(normalized)) {
      setError("Enter a covenant number, such as 1.");
      return;
    }
    void loadCase(normalized);
  }

  useEffect(() => {
    if (configReady && DEFAULT_ID) void loadCase(DEFAULT_ID);
  }, [configReady]);

  useEffect(() => {
    if (configReady && refreshToken > 0 && id) void loadCase(id, false);
  }, [configReady, id, refreshToken]);

  return (
    <section className="case-lookup panel" aria-labelledby="case-lookup-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Live covenant record</p>
          <h2 id="case-lookup-title">Read a case without guessing.</h2>
        </div>
        <span className="network-pill"><span className="status-dot" /> On-chain read</span>
      </div>
      <p className="muted case-intro">
        Search the deployed Core by covenant number. Every value below comes
        from {networkName} and refreshes only when you ask for a new read.
      </p>
      <form className="case-form" onSubmit={submit}>
        <label htmlFor="covenant-id">Covenant number</label>
        <div className="case-form-row">
          <input
            id="covenant-id"
            inputMode="numeric"
            pattern="[0-9]*"
            value={id}
            onChange={(event) => setId(event.target.value)}
            aria-describedby="case-help"
          />
          <button type="submit" disabled={loading || !configReady}>
            {loading ? "Reading…" : "Load covenant"}
          </button>
        </div>
        <span id="case-help" className="form-help">
          {lastRead ? "Last read " + lastRead : "Enter a covenant number to read the live deployment."}
        </span>
      </form>
      {error ? <p className="result-card danger" role="alert">{error}</p> : null}
      {covenant ? (
        <div className="case-result" aria-live="polite">
          <div className="case-status-row">
            <div><span className="case-label">Covenant #{covenant.covenantId}</span><strong>{formatState(covenant.state)}</strong></div>
            <span className={"state-badge " + (covenant.settlementClaimed ? "closed" : "open")}>{covenant.settlementClaimed ? "Closed" : "Active"}</span>
          </div>
          <div className="case-metrics">
            <div><span>Escrow funded</span><strong>{formatGen(covenant.fundedAmount)}</strong></div>
            <div><span>Outstanding</span><strong>{formatGen(covenant.outstandingAmount)}</strong></div>
            <div><span>Review round</span><strong>{covenant.reviewGeneration}</strong></div>
            <div><span>Evidence threshold</span><strong>{covenant.requiredCorroborationCount} source{covenant.requiredCorroborationCount === 1 ? "" : "s"}</strong></div>
          </div>
          <div className="case-details">
            <div><span>Buyer</span><code>{shorten(covenant.buyer)}</code></div>
            <div><span>Provider</span><code>{shorten(covenant.provider)}</code></div>
            <div><span>Opened</span><strong>{formatTime(covenant.openedAt)}</strong></div>
            <div><span>Delivery deadline</span><strong>{formatTime(covenant.deliveryDeadline)}</strong></div>
          </div>
          {covenant.adjudicationDecision ? <div className="case-callout"><span>Latest decision</span><strong>{formatState(covenant.adjudicationDecision)}</strong><small>{covenant.failureClassification ? formatState(covenant.failureClassification) : "No failure classification recorded."}</small></div> : null}
        </div>
      ) : null}
    </section>
  );
}
