"use client";

import { useEffect, useState } from "react";
import {
  createWalletClient,
  custom,
  isAddress,
  type Address,
} from "viem";
import { accord402WriteAbi } from "@/lib/accord402-abi";
import { submitAdjudicationWrite } from "@/lib/adjudicator-write";
import { parseEvidenceRepairJson } from "@/lib/evidence-repair";
import { accord402Chain, accord402Config, protocolLimits } from "@/lib/config";
import type { Covenant } from "@/components/case-lookup";

type WalletProvider = {
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
};

type WalletActionPanelProps = {
  covenant: Covenant | null;
  coreAddress: string;
  configReady: boolean;
  onTransactionSubmitted: (hash: string) => void;
};

const chainIdHex = accord402Config.chainIdHex;

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
    return `Switch the wallet to ${accord402Config.networkName} (chain ${accord402Config.chainId}) and try again.`;
  }
  return message || "Wallet action failed. No transaction was confirmed.";
}

function isValidCanonicalSource(value: string) {
  if (!value.startsWith("https://") || value.length < "https://a.b/c".length) return false;
  if (/[?#%\\]/.test(value) || /[^\x20-\x7e]/.test(value)) return false;
  const separator = value.indexOf("/", "https://".length);
  if (separator < 0 || separator === value.length - 1 || value.includes("//", separator)) return false;
  const host = value.slice("https://".length, separator);
  if (!host.includes(".") || host.startsWith(".") || host.endsWith(".")) return false;
  if (!/^[a-z0-9.-]+$/.test(host)) return false;
  return !value.endsWith("/");
}

type ActionName =
  | "adjudicate"
  | "acceptCovenant"
  | "submitDelivery"
  | "submitEvidenceRepair"
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
  if (!Number.isFinite(seconds) || seconds < 0) return "deadline passed";
  if (seconds === 0) return "available until this second";
  const secondsPerMinute = 60;
  const secondsPerHour = 60 * secondsPerMinute;
  const hours = Math.floor(seconds / secondsPerHour);
  const minutes = Math.max(1, Math.floor((seconds % secondsPerHour) / secondsPerMinute));
  return hours ? `available for about ${hours}h ${minutes}m` : `available for about ${minutes}m`;
}

function parseEvidenceJson(raw: string, requiredCorroborationCount: number) {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error("Evidence must be valid JSON.");
  }
  if (!Array.isArray(parsed) || parsed.length === 0 || parsed.length > protocolLimits.maxEvidence) {
    throw new Error(`Evidence must be a JSON array with 1 to ${protocolLimits.maxEvidence} records.`);
  }
  const records = parsed.map((value, index) => {
    if (!value || typeof value !== "object") throw new Error(`Evidence record ${index + 1} is not an object.`);
    const item = value as Record<string, unknown>;
    const required = [
      "evidenceId", "authorityId", "authorityRevision", "subject", "kind",
      "sourceKind", "canonicalSource", "immutableVersionOrRecordId",
      "publishedAt", "observedAt", "expiresAt", "contentDigest", "isPrimary",
    ];
    for (const field of required) {
      if (item[field] === undefined || item[field] === null || item[field] === "") {
        throw new Error(`Evidence record ${index + 1} is missing ${field}.`);
      }
    }
    const digest = String(item.contentDigest);
    if (!/^0x[0-9a-fA-F]{64}$/.test(digest)) {
      throw new Error(`Evidence record ${index + 1} needs a 32-byte contentDigest.`);
    }
    const authorityRevision = Number(item.authorityRevision);
    if (!Number.isSafeInteger(authorityRevision) || authorityRevision < 0) {
      throw new Error(`Evidence record ${index + 1} has an invalid authorityRevision.`);
    }
    const lengths: Array<[string, number]> = [
      ["evidenceId", protocolLimits.maxEvidenceIdBytes],
      ["authorityId", protocolLimits.maxAuthorityIdBytes],
      ["subject", protocolLimits.maxStringBytes],
      ["kind", protocolLimits.maxStringBytes],
      ["sourceKind", protocolLimits.maxStringBytes],
      ["canonicalSource", protocolLimits.maxSourceBytes],
      ["immutableVersionOrRecordId", protocolLimits.maxVersionBytes],
    ];
    for (const [field, maximum] of lengths) {
      if (new TextEncoder().encode(String(item[field])).length > maximum) {
        throw new Error(`Evidence record ${index + 1} has an oversized ${field}.`);
      }
    }
    if (!["LIVE", "IMMUTABLE", "VERSIONED"].includes(String(item.sourceKind))) {
      throw new Error(`Evidence record ${index + 1} has an invalid sourceKind.`);
    }
    if (!isValidCanonicalSource(String(item.canonicalSource))) {
      throw new Error(`Evidence record ${index + 1} needs an HTTPS canonicalSource with a non-empty path and no query or fragment.`);
    }
    return {
      evidenceId: String(item.evidenceId),
      authorityId: String(item.authorityId),
      authorityRevision,
      subject: String(item.subject),
      kind: String(item.kind),
      sourceKind: String(item.sourceKind),
      canonicalSource: String(item.canonicalSource),
      immutableVersionOrRecordId: String(item.immutableVersionOrRecordId),
      publishedAt: BigInt(String(item.publishedAt)),
      observedAt: BigInt(String(item.observedAt)),
      expiresAt: BigInt(String(item.expiresAt)),
      contentDigest: digest as `0x${string}`,
      isPrimary: item.isPrimary === true,
    };
  });
  if (!records.some((record) => record.isPrimary)) throw new Error("Evidence needs one primary record.");
  const corroborators = records.filter((record) => !record.isPrimary);
  if (corroborators.length < requiredCorroborationCount) {
    throw new Error(`Add at least ${requiredCorroborationCount} corroborating record(s).`);
  }
  return records;
}

export function WalletActionPanel({
  covenant,
  coreAddress,
  configReady,
  onTransactionSubmitted,
}: WalletActionPanelProps) {
  const [address, setAddress] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [submittedHash, setSubmittedHash] = useState("");
  const [now, setNow] = useState(() => Math.floor(Date.now() / 1000));
  const [challengeClaim, setChallengeClaim] = useState("");
  const [criterionIds, setCriterionIds] = useState("");
  const [providerPayoutRecipient, setProviderPayoutRecipient] = useState("");
  const [deliveryPayload, setDeliveryPayload] = useState("");
  const [evidenceJson, setEvidenceJson] = useState("");
  const [repairEvidenceJson, setRepairEvidenceJson] = useState("");

  const covenantId = covenant?.covenantId || "";
  const state = covenant?.state || "";
  let action: Action | null = null;
  if (covenant) {
    if (state === "REVIEW_RETRY_REQUIRED") {
      action = Number(covenant.retryDeadline) >= now && covenant.reviewGeneration < covenant.maxReviewGenerations
        ? { label: "Retry review", functionName: "retryReview", hint: remaining(covenant.retryDeadline, now) }
        : { label: "Expire review", functionName: "expireReview", hint: "the retry window has closed" };
    } else if (state === "SETTLEMENT_AUTHORIZED_PROVIDER" || state === "SETTLEMENT_AUTHORIZED_BUYER") {
      action = { label: "Claim settlement", functionName: "claimSettlement", hint: "final settlement is authorized" };
    } else if (state === "DELIVERED") {
      action = Number(covenant.challengeDeadline) < now
        ? { label: "Authorize unchallenged settlement", functionName: "authorizeUnchallengedSettlement", hint: "the challenge window has closed" }
        : address.toLowerCase() === covenant.buyer.toLowerCase()
          ? { label: "Challenge delivery", functionName: "challengeDelivery", hint: remaining(covenant.challengeDeadline, now) }
          : null;
    } else if (state === "FUNDED") {
      action = Number(covenant.acceptanceDeadline) < now
        ? { label: "Expire unaccepted covenant", functionName: "expireUnaccepted", hint: "the acceptance deadline has passed" }
        : address.toLowerCase() === covenant.provider.toLowerCase()
          ? { label: "Accept covenant", functionName: "acceptCovenant", hint: "provider wallet connected" }
          : null;
    } else if (state === "SERVICE_ACCEPTED") {
      action = Number(covenant.deliveryDeadline) < now
        ? { label: "Expire non-delivery", functionName: "expireNonDelivery", hint: "the delivery deadline has passed" }
        : address.toLowerCase() === covenant.provider.toLowerCase()
          ? { label: "Submit delivery", functionName: "submitDelivery", hint: remaining(covenant.deliveryDeadline, now) }
          : null;
    } else if (state === "EVIDENCE_REPAIR_REQUIRED") {
      const absoluteExpired =
        now > Number(covenant.absoluteDisputeDeadline);
      const generationExhausted =
        covenant.reviewGeneration >= covenant.maxReviewGenerations;
      const repairExpired =
        now > Number(covenant.repairDeadline);
      const authorizationCurrent =
        covenant.repairAuthorizationActive &&
        covenant.repairAuthorizationGeneration === covenant.reviewGeneration;

      if (absoluteExpired || generationExhausted) {
        action = {
          label: "Expire review",
          functionName: "expireReview",
          hint: "review recovery is no longer available",
        };
      } else if (repairExpired) {
        action = {
          label: "Expire repair window",
          functionName: "expireRepair",
          hint: "the repair deadline has passed",
        };
      } else if (
        authorizationCurrent &&
        address.toLowerCase() === covenant.provider.toLowerCase()
      ) {
        action = {
          label: "Submit evidence repair",
          functionName: "submitEvidenceRepair",
          hint: remaining(covenant.repairDeadline, now),
        };
      } else {
        action = null;
      }
    } else if (state === "CHALLENGED") {
      action = Number(covenant.absoluteDisputeDeadline) < now
        ? { label: "Expire review", functionName: "expireReview", hint: "the absolute dispute deadline has passed" }
        : {
            label: "Adjudicate challenged delivery",
            functionName: "adjudicate",
            hint: remaining(covenant.absoluteDisputeDeadline, now),
          };
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
      if (!configReady) throw new Error("Frontend configuration is incomplete. Add the required public environment variables before using wallet actions.");
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
                chainName: accord402Config.networkName,
                rpcUrls: [accord402Config.rpcUrl],
                nativeCurrency: {
                  name: accord402Config.nativeCurrencyName,
                  symbol: accord402Config.nativeCurrencySymbol,
                  decimals: accord402Config.nativeCurrencyDecimals,
                },
                blockExplorerUrls: accord402Config.explorerUrl ? [accord402Config.explorerUrl] : undefined,
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
      if (!configReady) throw new Error("Frontend configuration is incomplete. Add the required public environment variables before using wallet actions.");
      const provider = await getProvider();
      const selected = address || ((await provider.request({
        method: "eth_requestAccounts",
      })) as string[])[0];
      if (!selected) throw new Error("Connect a wallet before continuing.");
      const wallet = createWalletClient({
        account: selected as Address,
        chain: accord402Chain,
        transport: custom(provider),
      });
      let hash: `0x${string}`;
      if (action.functionName === "adjudicate") {
        hash = await submitAdjudicationWrite({
          provider,
          account: selected,
          coreAddress,
          covenantId,
        });
      } else if (action.functionName === "acceptCovenant") {
        const recipient = providerPayoutRecipient.trim() || selected;
        if (!isAddress(recipient)) throw new Error("Enter a valid registered provider payout address.");
        hash = await wallet.writeContract({
          address: coreAddress as Address,
          abi: accord402WriteAbi,
          functionName: "acceptCovenant",
          args: [BigInt(covenantId), recipient as Address],
        });
      } else if (action.functionName === "submitDelivery") {
        if (!deliveryPayload.trim()) throw new Error("Add the delivery payload before continuing.");
        if (new TextEncoder().encode(deliveryPayload.trim()).length > protocolLimits.maxDeliveryPayloadBytes) {
          throw new Error("Delivery payload is longer than the Core limit.");
        }
        const evidence = parseEvidenceJson(evidenceJson, covenant?.requiredCorroborationCount || 1);
        hash = await wallet.writeContract({
          address: coreAddress as Address,
          abi: accord402WriteAbi,
          functionName: "submitDelivery",
          args: [BigInt(covenantId), deliveryPayload.trim(), evidence],
        });
      } else if (action.functionName === "submitEvidenceRepair") {
        if (!covenant) {
          throw new Error("Load the covenant before submitting a repair.");
        }
        if (
          selected.toLowerCase() !== covenant.provider.toLowerCase()
        ) {
          throw new Error(
            "Only the covenant provider can submit the authorized evidence repair.",
          );
        }
        if (
          !covenant.repairAuthorizationActive ||
          covenant.repairAuthorizationGeneration !== covenant.reviewGeneration
        ) {
          throw new Error(
            "The evidence-repair authorization is not active for the current review generation.",
          );
        }

        const replacements =
          parseEvidenceRepairJson(repairEvidenceJson);

        hash = await wallet.writeContract({
          address: coreAddress as Address,
          abi: accord402WriteAbi,
          functionName: "submitEvidenceRepair",
          args: [BigInt(covenantId), replacements],
        });
      } else if (action.functionName === "challengeDelivery") {
        if (!covenant) {
          throw new Error("Load the covenant before challenging delivery.");
        }
        if (selected.toLowerCase() !== covenant.buyer.toLowerCase()) {
          throw new Error("Only the covenant buyer can challenge delivery.");
        }
        const challengedCriterionIds = criterionIds
          .split(/[\n,]/)
          .map((value) => value.trim())
          .filter(Boolean);
        if (!challengeClaim.trim()) throw new Error("Write the reason for the challenge before continuing.");
        if (new TextEncoder().encode(challengeClaim.trim()).length > protocolLimits.maxStringBytes) {
          throw new Error("Challenge claim is longer than the Core limit.");
        }
        if (!challengedCriterionIds.length) throw new Error("Add at least one criterion ID to challenge.");
        if (challengedCriterionIds.length > protocolLimits.maxCriteria) throw new Error("Too many challenged criteria.");
        if (new Set(challengedCriterionIds).size !== challengedCriterionIds.length) {
          throw new Error("Each challenged criterion ID must appear only once.");
        }
        const knownCriteria = new Set(covenant?.criteria?.map((criterion) => criterion.criterionId) || []);
        if (knownCriteria.size > 0 && challengedCriterionIds.some((criterionId) => !knownCriteria.has(criterionId))) {
          throw new Error("Every challenged criterion ID must belong to this covenant.");
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
          The console never guesses. It only offers state-valid actions to
          wallets permitted by the current on-chain state, and it keeps the
          exact submitted hash under observation afterward.
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
          <button type="button" className="button button-primary wallet-button" onClick={() => void connectWallet()} disabled={busy || !configReady}>
            {busy ? "Connecting…" : "Connect wallet"} <span>↗</span>
          </button>
        )}
        {action?.functionName === "acceptCovenant" ? (
          <form className="wallet-form" onSubmit={(event) => { event.preventDefault(); void performAction(); }}>
            <label htmlFor="provider-payout-recipient">Registered provider payout address</label>
            <input
              id="provider-payout-recipient"
              value={providerPayoutRecipient}
              onChange={(event) => setProviderPayoutRecipient(event.target.value)}
              placeholder="0x…"
              spellCheck={false}
              autoComplete="off"
              aria-describedby="provider-payout-help"
            />
            <span id="provider-payout-help" className="form-help">This address must already be registered in the {accord402Config.networkName} Settlement Vault.</span>
            <button type="submit" className="action-button" disabled={busy || !address || !configReady}>
              {busy ? "Waiting for wallet…" : action.label}
            </button>
          </form>
        ) : action?.functionName === "submitDelivery" ? (
          <form className="wallet-form" onSubmit={(event) => { event.preventDefault(); void performAction(); }}>
            <label htmlFor="delivery-payload">Delivery payload</label>
            <textarea
              id="delivery-payload"
              value={deliveryPayload}
              onChange={(event) => setDeliveryPayload(event.target.value)}
              placeholder="The provider’s service result, bounded by the covenant policy."
              maxLength={protocolLimits.maxDeliveryPayloadBytes}
              rows={4}
            />
            <label htmlFor="evidence-json">Evidence records (JSON array)</label>
            <textarea
              id="evidence-json"
              value={evidenceJson}
              onChange={(event) => setEvidenceJson(event.target.value)}
              placeholder={'[{"evidenceId":"…","authorityId":"…","authorityRevision":1,"subject":"…","kind":"…","sourceKind":"IMMUTABLE","canonicalSource":"https://…","immutableVersionOrRecordId":"…","publishedAt":0,"observedAt":0,"expiresAt":0,"contentDigest":"0x…","isPrimary":true}]'}
              rows={7}
              spellCheck={false}
              aria-describedby="evidence-help"
            />
            <span id="evidence-help" className="form-help">Include one primary record and at least {covenant?.requiredCorroborationCount || 1} corroborating record(s). The contract validates authorities, timestamps, sources, and replay rules.</span>
            <button type="submit" className="action-button" disabled={busy || !address || !configReady}>
              {busy ? "Waiting for wallet…" : action.label}
            </button>
          </form>
        ) : action?.functionName === "submitEvidenceRepair" ? (
          <form
            className="wallet-form"
            onSubmit={(event) => {
              event.preventDefault();
              void performAction();
            }}
          >
            <label htmlFor="repair-evidence-json">
              Authorized replacement evidence (JSON array)
            </label>
            <textarea
              id="repair-evidence-json"
              value={repairEvidenceJson}
              onChange={(event) =>
                setRepairEvidenceJson(event.target.value)
              }
              placeholder={"[{\"replacesEvidenceId\":\"old-id\",\"evidenceId\":\"new-id\",\"authorityId\":\"authority\",\"authorityRevision\":1,\"subject\":\"subject\",\"kind\":\"kind\",\"sourceKind\":\"IMMUTABLE\",\"canonicalSource\":\"https://raw.githubusercontent.com/owner/repo/commit/path\",\"immutableVersionOrRecordId\":\"40-character-commit\",\"publishedAt\":0,\"observedAt\":0,\"expiresAt\":0,\"contentDigest\":\"0x...\",\"isPrimary\":true}]"}
              rows={9}
              spellCheck={false}
              aria-describedby="repair-evidence-help"
            />
            <span
              id="repair-evidence-help"
              className="form-help"
            >
              Submit every replacement authorized by the current
              adjudication. The Core enforces the exact replaced evidence
              IDs and per-record field masks. Review generation{" "}
              {covenant?.reviewGeneration}; authorization generation{" "}
              {covenant?.repairAuthorizationGeneration}; policy repair
              mask {covenant?.repairAllowedFieldMask}.
            </span>
            <button
              type="submit"
              className="action-button"
              disabled={busy || !address || !configReady}
            >
              {busy ? "Waiting for wallet…" : action.label}
            </button>
          </form>
        ) : action?.functionName === "challengeDelivery" ? (
          <form className="wallet-form" onSubmit={(event) => { event.preventDefault(); void performAction(); }}>
            <label htmlFor="challenge-claim">Challenge claim</label>
            <textarea
              id="challenge-claim"
              value={challengeClaim}
              onChange={(event) => setChallengeClaim(event.target.value)}
              placeholder="Describe the specific delivery failure to review."
              maxLength={protocolLimits.maxStringBytes}
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
            <button type="submit" className="action-button" disabled={busy || !address || !configReady}>
              {busy ? "Waiting for wallet…" : action.label}
            </button>
          </form>
        ) : action ? (
          <button type="button" className="action-button" onClick={() => void performAction()} disabled={busy || !address || !configReady}>
            {busy ? "Waiting for wallet…" : action.label}
          </button>
        ) : (
          <span className="action-hint">
            {covenantId
              ? state === "DELIVERED"
                ? "The challenge window is still open; settlement cannot be authorized yet."
                : state === "FUNDED"
                  ? "Connect the provider wallet to accept this covenant, or wait for the acceptance deadline."
                  : state === "SERVICE_ACCEPTED"
                    ? "Connect the provider wallet to submit delivery before the deadline."
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
