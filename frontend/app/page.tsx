import { Accord402App } from "@/components/accord402-app";
import {
  accord402Config,
  configurationErrorMessage,
  isConfigured,
  configuredContractAddress,
} from "@/lib/client";

export default function Home() {
  return (
    <Accord402App
      contractAddress={configuredContractAddress}
      contractReady={isConfigured}
      configurationError={configurationErrorMessage}
      contractSha={accord402Config.sourceFingerprint}
      networkName={accord402Config.networkName}
      chainId={accord402Config.chainId}
      explorerUrl={accord402Config.explorerUrl}
      registryAddress={accord402Config.registryAddress}
      adjudicatorAddress={accord402Config.adjudicatorAddress}
      vaultAddress={accord402Config.vaultAddress}
    />
  );
}
