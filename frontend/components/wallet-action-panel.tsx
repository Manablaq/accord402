"use client";

import { useState } from "react";
import {
  createWalletClient,
  custom,
  type Address,
} from "viem";
import { testnetBradbury } from "genlayer-js/chains";

import { accord402WriteAbi } from "@/lib/accord402-abi";

type WalletProvider = {
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
};

type WalletActionPanelProps = {
  covenantId: string;
  state: string;
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

export function WalletActionPanel({
  covenantId,
  state,
  coreAddress,
  onTransactionSubmitted,
}: WalletActionPanelProps) {
  const [address, setAddress] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [submittedHash, setSubmittedHash] = useState("");

  const action =
    state === "REVIEW_RETRY_REQUIRED"
      ? { label: "Retry review", functionName: "retryReview" as const }
      : state === "SETTLEMENT_AUTHORIZED_PROVIDER" ||
          state === "SETTLEMENT_AUTHORIZED_BUYER"
        ? { label: "Claim settlement", functionName: "claimSettlement" as const }
        : null;

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
      const hash = await wallet.writeContract({
        address: coreAddress as Address,
        abi: accord402WriteAbi,
        functionName: action.functionName,
        args: [BigInt(covenantId)],
      });
      setAddress(selected);
      setSubmittedHash(hash);
      onTransactionSubmitted(hash);
    } catch (caught) {
      setError(friendlyWalletError(caught));
    } finally {
      setBusy(false);
    }
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
        {action ? (
          <button type="button" className="action-button" onClick={() => void performAction()} disabled={busy || !address}>
            {busy ? "Waiting for wallet…" : action.label}
          </button>
        ) : (
          <span className="action-hint">
            {covenantId ? "No user action is available for " + state.toLowerCase().replaceAll("_", " ") + "." : "Load a covenant to see available actions."}
          </span>
        )}
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
