"use client";

import { useEffect, useState } from "react";
import {
  createWalletClient,
  custom,
  type Address,
} from "viem";
import { testnetBradbury } from "genlayer-js/chains";

import { accord402WriteAbi } from "@/lib/accord402-abi";
import type { Covenant } from "@/components/case-lookup";

type WalletProvider = {
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
};

type WalletActionPanelProps = {
  covenant: Covenant | null;
  coreAddress: string;
  onTransactionSubmitted: (hash: string) => void;
};

const chainIdHex = "0x" + testnetBradbury.id.toString(16);

function shorten(value: string) {
  return value.slice(0, 8) + "…" + value.slice(-6);
}

function friendlyWalletError(error: unknown) {
  const message = error instanceof Error ? error.message : "";
  const lower = message.toLowerCase();
  if (lower.includes("user rejected") || lower.includes("denied")) {
    return "The wallet request was cancelled. No transaction was sent.";
  }
  if (lower.includes("insufficient funds")) {
    return "This wallet does not have enough GEN for the network fee.";
  }
  if (lower.includes("chain") || lower.includes("network")) {
    return "Switch the wallet to GenLayer Bradbury (chain 4221) and try again.";
  }
  return message || "Wallet action failed. No transaction was confirmed.";
}

type ActionName =
  | "retryReview"
  | "claimSettlement"
  | "authorizeUnchallengedSettlement"
  | "expireUnaccepted"
  | "expireNonDelivery"
  | "expireRepair"
  | "expireReview"
  | "challengeDelivery";

type Action = {
  label: string;
  functionName: ActionName;
  hint: string;
};

function remaining(deadline: string, now: number) {
  const seconds = Number(deadline) - now;
  if (!Number.isFinite(seconds) || seconds <= 0) return "deadline passed";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.max(1, Math.floor((seconds % 3600) / 60));
  return hours ? `available for about ${hours}h ${minutes}m` : `available for about ${minutes}m`;
}

export function WalletActionPanel({
  covenant,
  coreAddress,
  onTransactionSubmitted,
}: WalletActionPanelProps) {
  const [address, setAddress] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [submittedHash, setSubmittedHash] = useState("");
  const [now, setNow] = useState(() => Math.floor(Date.now() / 1000));
  const [challengeClaim, setChallengeClaim] = useState("");
  const [criterionIds, setCriterionIds] = useState("");

  const covenantId = covenant?.covenantId || "";
  const state = covenant?.state || "";
  let action: Action | null = null;
  if (covenant) {
    if (state === "REVIEW_RETRY_REQUIRED") {
      action = Number(covenant.retryDeadline) > now && covenant.reviewGeneration < covenant.maxReviewGenerations
        ? { label: "Retry review", functionName: "retryReview", hint: remaining(covenant.retryDeadline, now) }
        : { label: "Expire review", functionName: "expireReview", hint: "the retry window has closed" };
    } else if (state === "SETTLEMENT_AUTHORIZED_PROVIDER" || state === "SETTLEMENT_AUTHORIZED_BUYER") {
      action = { label: "Claim settlement", functionName: "claimSettlement", hint: "final settlement is authorized" };
    } else if (state === "DELIVERED") {
      action = Number(covenant.challengeDeadline) <= now
        ? { label: "Authorize unchallenged settlement", functionName: "authorizeUnchallengedSettlement", hint: "the challenge window has closed" }
        : { label: "Challenge delivery", functionName: "challengeDelivery", hint: remaining(covenant.challengeDeadline, now) };
    } else if (state === "FUNDED") {
      action = Number(covenant.acceptanceDeadline) <= now
        ? { label: "Expire unaccepted covenant", functionName: "expireUnaccepted", hint: "the acceptance deadline has passed" }
        : null;
    } else if (state === "SERVICE_ACCEPTED") {
      action = Number(covenant.deliveryDeadline) <= now
        ? { label: "Expire non-delivery", functionName: "expireNonDelivery", hint: "the delivery deadline has passed" }
        : null;
    } else if (state === "EVIDENCE_REPAIR_REQUIRED") {
      action = Number(covenant.repairDeadline) <= now && covenant.reviewGeneration < covenant.maxReviewGenerations
        ? { label: "Expire repair window", functionName: "expireRepair", hint: "the repair deadline has passed" }
        : null;
    } else if (state === "CHALLENGED" && Number(covenant.absoluteDisputeDeadline) <= now) {
      action = { label: "Expire review", functionName: "expireReview", hint: "the absolute dispute deadline has passed" };
    }
  }

  useEffect(() => {
    const timer = setInterval(() => setNow(Math.floor(Date.now() / 1000)), 15000);
    return () => clearInterval(timer);
  }, []);

  async function getProvider() {
    const provider = (window as Window & { ethereum?: WalletProvider }).ethereum;
    if (!provider) {
      throw new Error(
        "No browser wallet detected. Install MetaMask or another EIP-1193 wallet.",
      );
    }
    return provider;
  }

  async function connectWallet() {
    setBusy(true);
    setError("");
    try {
      const provider = await getProvider();
      const accounts = (await provider.request({
        method: "eth_requestAccounts",
      })) as string[];
      const selected = accounts[0];
      if (!selected) throw new Error("The wallet returned no account.");

      const currentChain = String(
        await provider.request({ method: "eth_chainId" }),
      ).toLowerCase();
      if (currentChain !== chainIdHex.toLowerCase()) {
        try {
          await provider.request({
            method: "wallet_switchEthereumChain",
            params: [{ chainId: chainIdHex }],
          });
        } catch (switchError) {
          const code =
            switchError && typeof switchError === "object" && "code" in switchError
              ? switchError.code
              : undefined;
          if (code !== 4902) throw switchError;
          await provider.request({
            method: "wallet_addEthereumChain",
            params: [
              {
                chainId: chainIdHex,
                chainName: "GenLayer Bradbury",
                rpcUrls: [testnetBradbury.rpcUrls.default.http[0]],
                nativeCurrency: testnetBradbury.nativeCurrency,
                blockExplorerUrls: [
                  "https://explorer-bradbury.genlayer.com",
                ],
              },
            ],
          });
          await provider.request({
            method: "wallet_switchEthereumChain",
            params: [{ chainId: chainIdHex }],
          });
        }
      }
      setAddress(selected);
    } catch (caught) {
      setError(friendlyWalletError(caught));
    } finally {
      setBusy(false);
    }
  }

  async function performAction() {
    if (!action || !covenantId) return;
    setBusy(true);
    setError("");
    setSubmittedHash("");
    try {
      const provider = await getProvider();
      const selected = address || ((await provider.request({
        method: "eth_requestAccounts",
      })) as string[])[0];
      if (!selected) throw new Error("Connect a wallet before continuing.");
      const wallet = createWalletClient({
        account: selected as Address,
        chain: testnetBradbury,
        transport: custom(provider),
      });
      let hash: `0x${string}`;
      if (action.functionName === "challengeDelivery") {
        const challengedCriterionIds = criterionIds
          .split(/[\n,]/)
          .map((value) => value.trim())
          .filter(Boolean);
        if (!challengeClaim.trim()) throw new Error("Write the reason for the challenge before continuing.");
        if (!challengedCriterionIds.length) throw new Error("Add at least one criterion ID to challenge.");
        if (new Set(challengedCriterionIds).size !== challengedCriterionIds.length) {
          throw new Error("Each challenged criterion ID must appear only once.");
        }
        hash = await wallet.writeContract({
          address: coreAddress as Address,
          abi: accord402WriteAbi,
          functionName: "challengeDelivery",
          args: [BigInt(covenantId), challengeClaim.trim(), challengedCriterionIds],
        });
      } else {
        hash = await wallet.writeContract({
          address: coreAddress as Address,
          abi: accord402WriteAbi,
          functionName: action.functionName,
          args: [BigInt(covenantId)],
        });
      }
      setAddress(selected);
      setSubmittedHash(hash);
      onTransactionSubmitted(hash);
    } catch (caught) {
      setError(friendlyWalletError(caught));
    } finally {
      setBusy(false);
    }
  }

  function toggleCriterion(criterionId: string) {
    const current = criterionIds.split(/[\n,]/).map((value) => value.trim()).filter(Boolean);
    const next = current.includes(criterionId)
      ? current.filter((value) => value !== criterionId)
      : [...current, criterionId];
    setCriterionIds(next.join(", "));
  }

  return (
    <section className="wallet-actions panel" aria-labelledby="wallet-actions-title">
      <div className="wallet-copy">
        <p className="eyebrow">Wallet actions</p>
        <h2 id="wallet-actions-title">
          {action ? action.label + " when you are ready." : "Actions follow the case state."}
        </h2>
        <p className="muted">
          The console never guesses. It only offers permissionless actions that
          match the current on-chain state, and it keeps the exact submitted
          hash under observation afterward.
        </p>
      </div>
      <div className="wallet-controls">
        {address ? (
          <div className="connected-wallet">
            <span className="status-dot" />
            <span><small>Connected wallet</small><code>{shorten(address)}</code></span>
            <button type="button" className="disconnect-button" onClick={() => setAddress("")}>Disconnect</button>
          </div>
        ) : (
          <button type="button" className="button button-primary wallet-button" onClick={() => void connectWallet()} disabled={busy}>
            {busy ? "Connecting…" : "Connect wallet"} <span>↗</span>
          </button>
        )}
        {action?.functionName === "challengeDelivery" ? (
          <form className="wallet-form" onSubmit={(event) => { event.preventDefault(); void performAction(); }}>
            <label htmlFor="challenge-claim">Challenge claim</label>
            <textarea
              id="challenge-claim"
              value={challengeClaim}
              onChange={(event) => setChallengeClaim(event.target.value)}
              placeholder="Describe the specific delivery failure to review."
              maxLength={8192}
              rows={4}
            />
            <label htmlFor="criterion-ids">Criterion IDs to review</label>
            <input
              id="criterion-ids"
              value={criterionIds}
              onChange={(event) => setCriterionIds(event.target.value)}
              placeholder="criterion-id-1, criterion-id-2"
              aria-describedby="criterion-help"
            />
            {covenant?.criteria?.length ? (
              <div className="criterion-picker" aria-label="Available covenant criteria">
                {covenant.criteria.map((criterion) => {
                  const selected = criterionIds.split(/[\n,]/).map((value) => value.trim()).includes(criterion.criterionId);
                  return (
                    <button
                      key={criterion.criterionId}
                      type="button"
                      className={selected ? "criterion-chip selected" : "criterion-chip"}
                      onClick={() => toggleCriterion(criterion.criterionId)}
                      title={criterion.criterionText}
                    >
                      {criterion.criterionId}
                    </button>
                  );
                })}
              </div>
            ) : null}
            <span id="criterion-help" className="form-help">Use IDs defined by this covenant’s evidence policy.</span>
            <button type="submit" className="action-button" disabled={busy || !address}>
              {busy ? "Waiting for wallet…" : action.label}
            </button>
          </form>
        ) : action ? (
          <button type="button" className="action-button" onClick={() => void performAction()} disabled={busy || !address}>
            {busy ? "Waiting for wallet…" : action.label}
          </button>
        ) : (
          <span className="action-hint">
            {covenantId
              ? state === "DELIVERED"
                ? "The challenge window is still open; settlement cannot be authorized yet."
                : "No user action is available for " + state.toLowerCase().replaceAll("_", " ") + "."
              : "Load a covenant to see available actions."}
          </span>
        )}
        {action ? <span className="action-hint">{action.hint}.</span> : null}
        {submittedHash ? (
          <p className="wallet-success" role="status">
            Submitted safely. Finality is still pending; the observer is tracking {shorten(submittedHash)}.
          </p>
        ) : null}
        {error ? <p className="result-card danger" role="alert">{error}</p> : null}
      </div>
    </section>
  );
}
