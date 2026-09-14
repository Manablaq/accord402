import { TransactionObserver } from "@/components/transaction-observer";
import {
  configuredContractAddress,
  isConfiguredContractAddress,
} from "@/lib/client";

const CONTRACT_SHA =
  "d6f52562d0686ff213eb33773f201441f50f15a15190533306afd0a91ccf50c4";

export default function Home() {
  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">
            A402
          </span>

          <div>
            <strong>Accord402</strong>
            <span>
              Service warranty protocol
            </span>
          </div>
        </div>

        <div className="status-chip">
          <span className="status-dot" />
          Bradbury release preparation
        </div>
      </header>

      <section className="hero">
        <p className="eyebrow">
          GEN-native intelligent escrow
        </p>

        <h1>
          Agreements that resolve on evidence,
          not trust.
        </h1>

        <p className="hero-copy">
          Accord402 binds immutable service
          terms, evidence policy, deterministic
          recovery, exact adjudication and
          finality-only settlement into one
          reviewer-verifiable protocol.
        </p>

        <div className="hero-meta">
          <div>
            <span>Network</span>
            <strong>
              GenLayer Bradbury
            </strong>
          </div>

          <div>
            <span>Chain ID</span>
            <strong>4221</strong>
          </div>

          <div>
            <span>Contract source</span>
            <code>
              {CONTRACT_SHA.slice(0, 12)}…
            </code>
          </div>
        </div>
      </section>

      <section className="grid">
        <article className="panel">
          <p className="eyebrow">
            Canonical deployment
          </p>

          <h2>
            {isConfiguredContractAddress
              ? "Bradbury address bound"
              : "Pending deployment"}
          </h2>

          <p className="muted">
            The frontend will not invent or
            silently substitute a deployment
            address. Production reads become
            active only after the canonical
            Bradbury deployment is finalized,
            successfully executed, source-parity
            verified and explicitly bound here.
          </p>

          <div className="binding">
            <span>
              Contract address
            </span>

            <code>
              {isConfiguredContractAddress
                ? configuredContractAddress
                : "NOT YET BOUND"}
            </code>
          </div>
        </article>

        <article className="panel">
          <p className="eyebrow">
            Trust boundary
          </p>

          <h2>
            The interface is never the authority.
          </h2>

          <p className="muted">
            Authorization, evidence policy,
            deadlines, accounting, recipient
            selection and settlement amount remain
            enforced by the Intelligent Contract.
          </p>

          <div className="state-list">
            <span>Submitted</span>
            <span>Consensus running</span>
            <span>Accepted / provisional</span>
            <span>Finality pending</span>
            <span>Finalized</span>
            <span>Execution verified</span>
          </div>
        </article>
      </section>

      <TransactionObserver />

      <footer>
        <span>
          Accord402 · V1 release surface
        </span>

        <span>
          No payment claim before finality +
          execution proof.
        </span>
      </footer>
    </main>
  );
}
