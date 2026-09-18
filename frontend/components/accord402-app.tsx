"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import { CaseLookup, type Covenant } from "@/components/case-lookup";
import { OpenCovenantPanel } from "@/components/open-covenant-panel";
import { TransactionObserver } from "@/components/transaction-observer";
import { WalletActionPanel } from "@/components/wallet-action-panel";

type Accord402AppProps = {
  contractAddress: string;
  contractReady: boolean;
  configurationError: string;
  contractSha: string;
  networkName: string;
  chainId: number;
  explorerUrl: string;
  registryAddress: string;
  adjudicatorAddress: string;
  vaultAddress: string;
};

function shorten(value: string) {
  return `${value.slice(0, 8)}…${value.slice(-6)}`;
}

function Reveal({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          element.classList.add("is-visible");
          observer.disconnect();
        }
      },
      { threshold: 0.12 },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} className={`reveal ${className}`}>
      {children}
    </div>
  );
}

function ThemeToggle() {
  const [theme, setTheme] = useState("light");

  useEffect(() => {
    setTheme(document.documentElement.dataset.theme || "light");
  }, []);

  function toggleTheme() {
    const next = theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("accord402-theme", next);
    setTheme(next);
  }

  return (
    <button
      className="theme-toggle"
      type="button"
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
    >
      <span>{theme === "light" ? "☾" : "☀"}</span>
      {theme === "light" ? "Dark mode" : "Light mode"}
    </button>
  );
}

export function Accord402App({
  contractAddress,
  contractReady,
  configurationError,
  contractSha,
  networkName,
  chainId,
  explorerUrl,
  registryAddress,
  adjudicatorAddress,
  vaultAddress,
}: Accord402AppProps) {
  const [liveCovenant, setLiveCovenant] = useState<Covenant | null>(null);
  const [submittedTxId, setSubmittedTxId] = useState("");
  const [covenantRefreshToken, setCovenantRefreshToken] = useState(0);
  const steps = [
    ["01", "Fund the covenant", "The buyer locks the required GEN escrow against immutable terms."],
    ["02", "Deliver evidence", "The provider submits issuer-bound records before the SLA deadline."],
    ["03", "Review independently", "GenLayer validators evaluate the same policy and evidence."],
    ["04", "Challenge with cause", "A bounded window protects both parties from silent outcomes."],
    ["05", "Release on finality", "Only a finalized successful transaction can authorize settlement."],
  ];
  const contracts = [
    ["Registry", registryAddress],
    ["Adjudicator", adjudicatorAddress],
    ["Settlement vault", vaultAddress],
  ];

  return (
    <main>
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <header className="site-header shell">
        <a className="brand" href="#top" aria-label="Accord402 home">
          <span className="brand-mark">A4<span>02</span></span>
          <span className="brand-name">Accord<span>402</span></span>
        </a>
        <nav className="desktop-nav" aria-label="Primary navigation">
          <a href="#protocol">Protocol</a>
          <a href="#console">Live console</a>
          <a href="#proof">Why it holds</a>
        </nav>
        <div className="header-actions">
          <span className="live-indicator"><span className="status-dot" /> {networkName} live</span>
          <ThemeToggle />
        </div>
      </header>

      <div id="top" className="hero shell">
        <Reveal className="hero-copy-block">
          <p className="eyebrow"><span className="eyebrow-mark">✦</span> Intelligent agreements for uncertain services</p>
          <h1>Settle the hard part<span>.</span></h1>
          <p className="hero-copy">Accord402 turns service promises into proof-bound covenants. Terms, evidence, review, and settlement move through a verifiable trail on GenLayer.</p>
          <div className="hero-actions">
            <a className="button button-primary" href="#console">Open live console <span>↗</span></a>
            <a className="button button-quiet" href="#protocol">See how it works <span>↓</span></a>
          </div>
          <div className="hero-proof"><span className="proof-avatar">◎</span><span>Built for finality-first operations</span><span className="proof-line" /><strong>{networkName} / {chainId}</strong></div>
        </Reveal>

        <Reveal className="hero-map-wrap">
          <div className="hero-map">
            <div className="map-topline"><span>FIELD NOTE 04</span><span>LIVE</span></div>
            <svg className="contours" viewBox="0 0 560 520" aria-hidden="true">
              <path d="M-20 432c76-70 140-89 201-54 75 43 103 37 152-5 73-63 136-77 253-20" />
              <path d="M-24 384c74-69 139-84 195-52 73 42 105 34 159-8 76-59 144-65 250-12" />
              <path d="M-28 335c74-65 137-78 188-48 71 41 106 28 164-12 77-54 149-52 255-4" />
              <path d="M-24 282c71-57 133-67 183-41 67 35 103 22 167-15 74-44 147-40 248 5" />
              <path d="M-18 226c72-51 133-57 182-31 64 33 100 13 163-19 75-38 149-23 254 20" />
              <path d="M2 168c68-43 126-42 177-18 61 28 101 3 163-23 73-30 142-14 235 27" />
              <path className="contour-highlight" d="M52 466c80-72 145-78 205-39 67 44 112 35 164-12 50-46 92-52 142-38" />
            </svg>
            <div className="trail-route"><span className="trail-start">01</span><span className="trail-pin pin-one">02</span><span className="trail-pin pin-two">03</span><span className="trail-end">✓</span></div>
            <div className="map-caption"><span>THE PROOFBOUND TRAIL</span><strong>From terms to release</strong></div>
            <div className="map-stamp"><span>GEN</span><strong>402</strong></div>
          </div>
        </Reveal>
      </div>

      <section className="signal-strip shell" aria-label="Protocol highlights">
        <div><span className="signal-number">01</span><strong>Policy-bound evidence</strong><span>not vibes</span></div>
        <div><span className="signal-number">02</span><strong>Independent review</strong><span>not a black box</span></div>
        <div><span className="signal-number">03</span><strong>Finality-safe release</strong><span>not a promise</span></div>
      </section>

      <section id="protocol" className="section shell">
        <Reveal className="section-intro">
          <p className="eyebrow">A clearer route through uncertainty</p>
          <h2>Every agreement carries its own evidence trail.</h2>
          <p className="muted">A covenant does not ask users to trust an interface. It records the rules, lets validators inspect the evidence, and releases value only after the chain says the outcome is final.</p>
        </Reveal>
        <div className="steps-grid">
          {steps.map(([number, title, body]) => (
            <Reveal key={number} className="step-card">
              <span className="step-number">{number}</span>
              <div><h3>{title}</h3><p>{body}</p></div>
              <span className="step-arrow">↗</span>
            </Reveal>
          ))}
        </div>
      </section>

      <section id="console" className="console-section shell">
        <Reveal className="console-heading">
          <div><p className="eyebrow">Live protocol console</p><h2>See the chain’s answer.</h2></div>
          <p className="muted">Read-only by design. Use the exact {networkName} transaction hash you want to certify; the console keeps watching until the outcome is canonical.</p>
        </Reveal>
        <div className="console-grid">
          <Reveal className="contract-card panel">
            <div className="card-kicker"><span className="live-indicator"><span className="status-dot" /> Network online</span><span className="card-index">A402 / 01</span></div>
            <h3>Accord402 Core</h3>
            <p className="muted">The deployed V2 covenant engine coordinating registry, adjudication, evidence, and settlement paths.</p>
            <div className="address-row"><span>Canonical {networkName} address</span><code>{contractReady ? shorten(contractAddress) : "not bound"}</code></div>
            <div className="address-row"><span>Source fingerprint</span><code>{contractSha.slice(0, 10)}…</code></div>
            <a className="text-link" href={`${explorerUrl}/address/${contractAddress}`} target="_blank" rel="noreferrer">Open in explorer ↗</a>
          </Reveal>
          <Reveal className="stack-card panel">
            <div className="card-kicker"><span className="eyebrow">Live deployment map</span><span className="card-index">{networkName.toUpperCase()}</span></div>
            <div className="contract-stack">
              {contracts.map(([label, address]) => (
                <div className="stack-row" key={label}><span className="stack-dot" /><div><strong>{label}</strong><code>{shorten(address)}</code></div><span className="stack-state">verified</span></div>
              ))}
            </div>
            <p className="stack-note">The interface exposes addresses as references. Authority remains in the deployed Intelligent Contracts.</p>
          </Reveal>
        </div>
        <Reveal>
          {!contractReady ? <p className="result-card danger" role="alert">Frontend configuration is incomplete. {configurationError}</p> : null}
          <OpenCovenantPanel
            coreAddress={contractAddress}
            vaultAddress={vaultAddress}
            networkName={networkName}
            chainId={chainId}
            configReady={contractReady}
            onTransactionSubmitted={setSubmittedTxId}
          />
        </Reveal>
        <Reveal>
          <CaseLookup
            onCovenantLoaded={setLiveCovenant}
            refreshToken={covenantRefreshToken}
            networkName={networkName}
            configReady={contractReady}
          />
        </Reveal>
        <Reveal>
          <WalletActionPanel
            covenant={liveCovenant}
            coreAddress={contractAddress}
            configReady={contractReady}
            onTransactionSubmitted={setSubmittedTxId}
          />
        </Reveal>
        <Reveal>
          <TransactionObserver
            submittedTxId={submittedTxId}
            networkName={networkName}
            chainId={chainId}
            configReady={contractReady}
            onCanonicalSuccess={() => setCovenantRefreshToken((value) => value + 1)}
          />
        </Reveal>
      </section>

      <section id="proof" className="proof-section shell">
        <Reveal className="proof-layout">
          <div><p className="eyebrow">Why Accord402 holds</p><h2>Built for the moment after “accepted.”</h2><p className="muted">Consensus is a step. Finality and execution success are the proof. That distinction shapes every state, button, and message in this interface.</p><a className="button button-primary" href="#console">Inspect a transaction <span>↗</span></a></div>
          <div className="proof-list">
            <div><strong>01</strong><span><b>Exact transaction identity</b><small>Uncertain observation resumes the same write; it never blindly replays it.</small></span></div>
            <div><strong>02</strong><span><b>Deterministic state machine</b><small>Deadlines, challenge windows, and review outcomes are enforced by contract state.</small></span></div>
            <div><strong>03</strong><span><b>Settlement with receipts</b><small>Release is reported only after finality and FINISHED_WITH_RETURN.</small></span></div>
          </div>
        </Reveal>
      </section>

      <footer className="site-footer shell">
        <a className="brand" href="#top"><span className="brand-mark">A4<span>02</span></span><span className="brand-name">Accord<span>402</span></span></a>
        <span>Proof-bound agreements on {networkName}.</span>
        <span>V2 release surface</span>
      </footer>
    </main>
  );
}
