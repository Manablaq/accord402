"use client";

import { useState } from "react";
import {
  createPublicClient,
  createWalletClient,
  custom,
  http,
  isAddress,
  type Address,
} from "viem";
import { testnetBradbury } from "genlayer-js/chains";

import { accord402VaultAbi, accord402WriteAbi } from "@/lib/accord402-abi";

type WalletProvider = {
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
};

type OpenCovenantPanelProps = {
  coreAddress: string;
  vaultAddress: string;
  onTransactionSubmitted: (hash: string) => void;
};

const chainIdHex = "0x" + testnetBradbury.id.toString(16);
const RPC_URL = process.env.NEXT_PUBLIC_GENLAYER_RPC?.trim() || "https://rpc-bradbury.genlayer.com";
const DEFAULT_CRITERIA = JSON.stringify([
  { criterionId: "service-complete", criterionText: "The provider completes the agreed service." },
], null, 2);
const DEFAULT_AUTHORITIES = JSON.stringify([
  { authorityId: "primary-source", authorityRevision: 1, role: "PRIMARY", identityKind: "publisher", identityValue: "primary.example", canonicalOrigin: "https://primary.example" },
  { authorityId: "corroborator-source", authorityRevision: 1, role: "CORROBORATOR", identityKind: "publisher", identityValue: "corroborator.example", canonicalOrigin: "https://corroborator.example" },
], null, 2);

const initialForm = {
  provider: "",
  buyerPayout: "",
  principal: "1",
  serviceSpec: "Deliver the agreed service with verifiable evidence.",
  acceptanceLeadMinutes: "60",
  deliveryLeadMinutes: "1440",
  challengeDurationMinutes: "60",
  absoluteHorizonHours: "72",
  evidenceRepairWindowMinutes: "60",
  reviewRetryWindowMinutes: "60",
  maxReviewGenerations: "3",
  maxEvidenceAgeMinutes: "15",
  requiredCorroborationCount: "1",
  criteriaJson: DEFAULT_CRITERIA,
  authoritiesJson: DEFAULT_AUTHORITIES,
};

function getProvider() {
  const provider = (window as Window & { ethereum?: WalletProvider }).ethereum;
  if (!provider) throw new Error("No browser wallet detected. Install MetaMask or another EIP-1193 wallet.");
  return provider;
}

function parseGen(value: string) {
  if (!/^\d+(?:\.\d{1,18})?$/.test(value.trim())) throw new Error("Principal must be a positive GEN amount with up to 18 decimals.");
  const [whole, fraction = ""] = value.trim().split(".");
  const wei = BigInt(whole) * BigInt("1000000000000000000") + BigInt((fraction + "0".repeat(18)).slice(0, 18));
  if (wei <= BigInt(0)) throw new Error("Principal must be greater than zero.");
  return wei;
}

function parseRecords(raw: string, kind: "criteria" | "authorities") {
  let parsed: unknown;
  try { parsed = JSON.parse(raw); } catch { throw new Error(`${kind === "criteria" ? "Criteria" : "Authorities"} must be valid JSON.`); }
  if (!Array.isArray(parsed) || parsed.length === 0 || parsed.length > 16) throw new Error(`${kind === "criteria" ? "Criteria" : "Authorities"} must contain 1 to 16 records.`);
  return parsed;
}

function parseCriteria(raw: string) {
  return parseRecords(raw, "criteria").map((value, index) => {
    if (!value || typeof value !== "object") throw new Error(`Criterion ${index + 1} is not an object.`);
    const item = value as Record<string, unknown>;
    const criterionId = String(item.criterionId || "").trim();
    const criterionText = String(item.criterionText || "").trim();
    if (!criterionId || !criterionText) throw new Error(`Criterion ${index + 1} needs criterionId and criterionText.`);
    return { criterionId, criterionText };
  });
}

function parseAuthorities(raw: string, requiredCorroborationCount: number) {
  const authorities = parseRecords(raw, "authorities").map((value, index) => {
    if (!value || typeof value !== "object") throw new Error(`Authority ${index + 1} is not an object.`);
    const item = value as Record<string, unknown>;
    const authorityId = String(item.authorityId || "").trim();
    const role = String(item.role || "").trim();
    const identityKind = String(item.identityKind || "").trim();
    const identityValue = String(item.identityValue || "").trim();
    const canonicalOrigin = String(item.canonicalOrigin || "").trim();
    const authorityRevision = Number(item.authorityRevision);
    if (!authorityId || !identityKind || !identityValue || !/^https:\/\//.test(canonicalOrigin) || (role !== "PRIMARY" && role !== "CORROBORATOR")) {
      throw new Error(`Authority ${index + 1} has invalid required fields or origin.`);
    }
    if (!Number.isSafeInteger(authorityRevision) || authorityRevision < 0) throw new Error(`Authority ${index + 1} has an invalid revision.`);
    return { authorityId, authorityRevision, role, identityKind, identityValue, canonicalOrigin };
  });
  if (!authorities.some((authority) => authority.role === "PRIMARY")) throw new Error("Authorities need one PRIMARY binding.");
  const pairs = authorities.map((authority) => `${authority.authorityId}:${authority.authorityRevision}`);
  if (new Set(pairs).size !== pairs.length) throw new Error("Authority ID and revision pairs must be unique.");
  const identities = authorities.map((authority) => `${authority.identityKind}:${authority.identityValue}`);
  if (new Set(identities).size !== identities.length) throw new Error("Authority identities must be unique.");
  if (authorities.filter((authority) => authority.role === "CORROBORATOR").length < requiredCorroborationCount) {
    throw new Error(`Add at least ${requiredCorroborationCount} CORROBORATOR authority binding(s).`);
  }
  return authorities;
}

function friendlyError(error: unknown) {
  const message = error instanceof Error ? error.message : "";
  const lower = message.toLowerCase();
  if (lower.includes("user rejected") || lower.includes("denied")) return "The wallet request was cancelled. No transaction was sent.";
  if (lower.includes("insufficient funds")) return "This wallet does not have enough GEN for the funding amount and network fee.";
  return message || "The covenant transaction failed before confirmation.";
}

export function OpenCovenantPanel({ coreAddress, vaultAddress, onTransactionSubmitted }: OpenCovenantPanelProps) {
  const [form, setForm] = useState(initialForm);
  const [account, setAccount] = useState("");
  const [registered, setRegistered] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  function update(name: keyof typeof initialForm, value: string) {
    setForm((current) => ({ ...current, [name]: value }));
    if (name === "buyerPayout") setRegistered(null);
  }

  async function connect() {
    setBusy(true); setError("");
    try {
      const provider = getProvider();
      const accounts = (await provider.request({ method: "eth_requestAccounts" })) as string[];
      const selected = accounts[0];
      if (!selected) throw new Error("The wallet returned no account.");
      const chain = String(await provider.request({ method: "eth_chainId" })).toLowerCase();
      if (chain !== chainIdHex.toLowerCase()) {
        try {
          await provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId: chainIdHex }] });
        } catch (switchError) {
          if ((switchError as { code?: number }).code !== 4902) throw switchError;
          await provider.request({
            method: "wallet_addEthereumChain",
            params: [{
              chainId: chainIdHex,
              chainName: "GenLayer Bradbury",
              rpcUrls: [testnetBradbury.rpcUrls.default.http[0]],
              nativeCurrency: testnetBradbury.nativeCurrency,
              blockExplorerUrls: testnetBradbury.blockExplorers?.default?.url ? [testnetBradbury.blockExplorers.default.url] : undefined,
            }],
          });
          await provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId: chainIdHex }] });
        }
      }
      setAccount(selected);
      if (!form.buyerPayout) update("buyerPayout", selected);
    } catch (caught) { setError(friendlyError(caught)); } finally { setBusy(false); }
  }

  async function checkRegistration() {
    setBusy(true); setError("");
    try {
      const recipient = form.buyerPayout.trim();
      if (!isAddress(recipient)) throw new Error("Enter a valid buyer payout address first.");
      const client = createPublicClient({ chain: testnetBradbury, transport: http(RPC_URL) });
      const result = await client.readContract({ address: vaultAddress as Address, abi: accord402VaultAbi, functionName: "is_registered_payout", args: [recipient as Address] });
      setRegistered(result); setMessage(result ? "Buyer payout recipient is registered." : "This recipient is not registered yet.");
    } catch (caught) { setError(friendlyError(caught)); } finally { setBusy(false); }
  }

  async function registrationAction(functionName: "begin_payout_registration" | "confirm_payout_registration") {
    setBusy(true); setError("");
    try {
      const provider = getProvider();
      const selected = account || ((await provider.request({ method: "eth_requestAccounts" })) as string[])[0];
      if (!selected) throw new Error("Connect the wallet that owns the payout address.");
      const wallet = createWalletClient({ account: selected as Address, chain: testnetBradbury, transport: custom(provider) });
      const hash = await wallet.writeContract({ address: vaultAddress as Address, abi: accord402VaultAbi, functionName, args: [] });
      onTransactionSubmitted(hash); setMessage(functionName === "begin_payout_registration" ? "Registration started. Wait for the next block, then confirm registration." : "Registration confirmation submitted; check registration again after finality.");
    } catch (caught) { setError(friendlyError(caught)); } finally { setBusy(false); }
  }

  async function openAndFund() {
    setBusy(true); setError(""); setMessage("");
    try {
      const provider = getProvider();
      const selected = account || ((await provider.request({ method: "eth_requestAccounts" })) as string[])[0];
      if (!selected) throw new Error("Connect the buyer wallet before funding.");
      const recipient = form.buyerPayout.trim() || selected;
      if (!isAddress(form.provider.trim()) || !isAddress(recipient)) throw new Error("Provider and buyer payout must be valid addresses.");
      if (form.provider.trim().toLowerCase() === selected.toLowerCase()) throw new Error("Provider must be a different wallet from the buyer.");
      if (registered !== true) throw new Error("Verify a registered buyer payout recipient before funding.");
      const principal = parseGen(form.principal);
      const now = Math.floor(Date.now() / 1000);
      const acceptanceLead = Number(form.acceptanceLeadMinutes) * 60;
      const deliveryLead = Number(form.deliveryLeadMinutes) * 60;
      const challengeDuration = Number(form.challengeDurationMinutes) * 60;
      const absoluteHorizon = Number(form.absoluteHorizonHours) * 3600;
      const repairWindow = Number(form.evidenceRepairWindowMinutes) * 60;
      const retryWindow = Number(form.reviewRetryWindowMinutes) * 60;
      const maxGenerations = Number(form.maxReviewGenerations);
      const maxEvidenceAge = Number(form.maxEvidenceAgeMinutes) * 60;
      const corroborationCount = Number(form.requiredCorroborationCount);
      if (!form.serviceSpec.trim()) throw new Error("Service specification is required.");
      if (acceptanceLead < 60 || acceptanceLead > 604800 || deliveryLead <= acceptanceLead || deliveryLead > 1209600) throw new Error("Acceptance and delivery windows are outside the Core limits.");
      if (challengeDuration < 60 || challengeDuration > 604800 || repairWindow < 60 || repairWindow > 86400 || retryWindow < 60 || retryWindow > 86400) throw new Error("Challenge, repair, and retry windows are outside the Core limits.");
      if (absoluteHorizon <= deliveryLead + challengeDuration + 3600 || absoluteHorizon > 2592000) throw new Error("Absolute dispute horizon must leave the required review guard time.");
      if (!Number.isInteger(maxGenerations) || maxGenerations < 1 || maxGenerations > 4 || !Number.isInteger(maxEvidenceAge) || maxEvidenceAge < 60 || maxEvidenceAge > 2592000 || !Number.isInteger(corroborationCount) || corroborationCount < 1 || corroborationCount > 8) throw new Error("Review, freshness, or corroboration settings are outside the Core limits.");
      const criteria = parseCriteria(form.criteriaJson);
      const authorityBindings = parseAuthorities(form.authoritiesJson, corroborationCount);
      const terms = {
        provider: form.provider.trim() as Address,
        principal,
        serviceSpec: form.serviceSpec.trim(),
        acceptanceDeadline: BigInt(now + acceptanceLead),
        deliveryDeadline: BigInt(now + deliveryLead),
        challengeDuration: BigInt(challengeDuration),
        absoluteDisputeDeadline: BigInt(now + absoluteHorizon),
        evidenceRepairWindow: BigInt(repairWindow),
        reviewRetryWindow: BigInt(retryWindow),
        maxReviewGenerations: maxGenerations,
        maxEvidenceAge: BigInt(maxEvidenceAge),
        requiredCorroborationCount: corroborationCount,
        repairAllowedFieldMask: 252,
        replayScope: "COVENANT",
        criteria,
        authorityBindings,
      };
      const wallet = createWalletClient({ account: selected as Address, chain: testnetBradbury, transport: custom(provider) });
      const hash = await wallet.writeContract({ address: coreAddress as Address, abi: accord402WriteAbi, functionName: "openCovenant", args: [terms, recipient as Address], value: principal });
      setAccount(selected); onTransactionSubmitted(hash); setMessage("Funding submitted. The covenant ID will be assigned by Core; finality and the exact transaction hash are being observed.");
    } catch (caught) { setError(friendlyError(caught)); } finally { setBusy(false); }
  }

  return (
    <section className="open-covenant panel" aria-labelledby="open-covenant-title">
      <div className="section-heading">
        <div><p className="eyebrow">Buyer workspace</p><h2 id="open-covenant-title">Open and fund a covenant.</h2></div>
        <span className="network-pill"><span className="status-dot" /> Bradbury · 4221</span>
      </div>
      <p className="muted open-intro">Create a new Core covenant with exact GEN escrow, bounded deadlines, frozen criteria, and approved evidence authorities. The form validates the protocol limits before your wallet is asked to sign.</p>
      <div className="open-toolbar">
        {account ? <span className="connected-wallet"><span className="status-dot" /><code>{account.slice(0, 8)}…{account.slice(-6)}</code></span> : <button type="button" className="button button-primary wallet-button" onClick={() => void connect()} disabled={busy}>{busy ? "Connecting…" : "Connect buyer wallet"}</button>}
        <button type="button" className="secondary-button" onClick={() => void checkRegistration()} disabled={busy}>Check payout registration</button>
        <button type="button" className="secondary-button" onClick={() => void registrationAction("begin_payout_registration")} disabled={busy}>Begin registration</button>
        <button type="button" className="secondary-button" onClick={() => void registrationAction("confirm_payout_registration")} disabled={busy}>Confirm registration</button>
        {registered === true ? <span className="registration-ok">✓ payout registered</span> : registered === false ? <span className="registration-warn">Register before funding</span> : null}
      </div>
      <div className="open-grid">
        <label>Provider address<input value={form.provider} onChange={(event) => update("provider", event.target.value)} placeholder="0x…" spellCheck={false} /></label>
        <label>Buyer payout address<input value={form.buyerPayout} onChange={(event) => update("buyerPayout", event.target.value)} placeholder="0x… registered in the vault" spellCheck={false} /></label>
        <label>Principal (GEN)<input value={form.principal} onChange={(event) => update("principal", event.target.value)} inputMode="decimal" placeholder="1.0" /></label>
        <label>Acceptance window (minutes)<input value={form.acceptanceLeadMinutes} onChange={(event) => update("acceptanceLeadMinutes", event.target.value)} inputMode="numeric" /></label>
        <label>Delivery window (minutes)<input value={form.deliveryLeadMinutes} onChange={(event) => update("deliveryLeadMinutes", event.target.value)} inputMode="numeric" /></label>
        <label>Challenge window (minutes)<input value={form.challengeDurationMinutes} onChange={(event) => update("challengeDurationMinutes", event.target.value)} inputMode="numeric" /></label>
        <label>Absolute dispute horizon (hours)<input value={form.absoluteHorizonHours} onChange={(event) => update("absoluteHorizonHours", event.target.value)} inputMode="numeric" /></label>
        <label>Evidence repair window (minutes)<input value={form.evidenceRepairWindowMinutes} onChange={(event) => update("evidenceRepairWindowMinutes", event.target.value)} inputMode="numeric" /></label>
        <label>Review retry window (minutes)<input value={form.reviewRetryWindowMinutes} onChange={(event) => update("reviewRetryWindowMinutes", event.target.value)} inputMode="numeric" /></label>
        <label>Maximum review generations<input value={form.maxReviewGenerations} onChange={(event) => update("maxReviewGenerations", event.target.value)} inputMode="numeric" /></label>
        <label>Maximum evidence age (minutes)<input value={form.maxEvidenceAgeMinutes} onChange={(event) => update("maxEvidenceAgeMinutes", event.target.value)} inputMode="numeric" /></label>
        <label>Required corroborators<input value={form.requiredCorroborationCount} onChange={(event) => update("requiredCorroborationCount", event.target.value)} inputMode="numeric" /></label>
        <label className="open-span">Service specification<textarea value={form.serviceSpec} onChange={(event) => update("serviceSpec", event.target.value)} rows={3} maxLength={8192} /></label>
        <label className="open-span">Criteria JSON<textarea value={form.criteriaJson} onChange={(event) => update("criteriaJson", event.target.value)} rows={7} spellCheck={false} /></label>
        <label className="open-span">Authority bindings JSON<textarea value={form.authoritiesJson} onChange={(event) => update("authoritiesJson", event.target.value)} rows={9} spellCheck={false} /></label>
      </div>
      <div className="open-submit"><button type="button" className="button button-primary" onClick={() => void openAndFund()} disabled={busy || registered !== true}>{busy ? "Waiting for wallet…" : "Open and fund covenant"}<span>↗</span></button><span className="form-help">Requires a registered buyer payout recipient and exact GEN value equal to the principal.</span></div>
      {message ? <p className="wallet-success" role="status">{message}</p> : null}
      {error ? <p className="result-card danger" role="alert">{error}</p> : null}
    </section>
  );
}
