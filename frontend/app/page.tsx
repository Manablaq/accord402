import { Accord402App } from "@/components/accord402-app";
import {
  configuredContractAddress,
  isConfiguredContractAddress,
} from "@/lib/client";

const CONTRACT_SHA =
  "d6f52562d0686ff213eb33773f201441f50f15a15190533306afd0a91ccf50c4";

export default function Home() {
  return (
    <Accord402App
      contractAddress={configuredContractAddress}
      contractReady={isConfiguredContractAddress}
      contractSha={CONTRACT_SHA}
    />
  );
}
