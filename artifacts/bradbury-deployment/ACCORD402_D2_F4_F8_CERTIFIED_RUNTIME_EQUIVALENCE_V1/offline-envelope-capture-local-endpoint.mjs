import {
  createServer,
} from "node:http";

import {
  readFile,
  writeFile,
} from "node:fs/promises";

import {
  createHash,
} from "node:crypto";

import {
  join,
} from "node:path";

import {
  pathToFileURL,
} from "node:url";


const [
  ,
  ,
  sdkRoot,
  canonicalPath,
  d2Path,
  outputPath,
  senderAddress,
  expectedCanonicalBytesRaw,
  expectedCanonicalOuterRaw,
  largestOkRaw,
  smallestBlockedRaw,
  marginTargetRaw,
] = process.argv;


const expectedCanonicalBytes =
  Number(
    expectedCanonicalBytesRaw
  );

const expectedCanonicalOuter =
  Number(
    expectedCanonicalOuterRaw
  );

const largestOk =
  Number(
    largestOkRaw
  );

const smallestBlocked =
  Number(
    smallestBlockedRaw
  );

const marginTarget =
  Number(
    marginTargetRaw
  );


const sdk =
  await import(
    pathToFileURL(
      join(
        sdkRoot,
        "dist",
        "index.js",
      )
    ).href
  );


const chains =
  await import(
    pathToFileURL(
      join(
        sdkRoot,
        "dist",
        "chains",
        "index.js",
      )
    ).href
  );


if (
  typeof sdk.createClient
  !== "function"
) {
  throw new Error(
    "createClient export missing"
  );
}


if (
  !chains.testnetBradbury
) {
  throw new Error(
    "testnetBradbury export missing"
  );
}


const canonicalSource =
  await readFile(
    canonicalPath,
    "utf8",
  );


const d2Source =
  await readFile(
    d2Path,
    "utf8",
  );


if (
  Buffer.byteLength(
    canonicalSource,
    "utf8",
  )
  !== expectedCanonicalBytes
) {
  throw new Error(
    "canonical source byte count mismatch"
  );
}


/*
 * Freeze Date.now once so canonical and D2 use exactly the same
 * six-argument addTransaction validUntil value.
 */
const realDateNow =
  Date.now.bind(Date);

const captureMs =
  realDateNow();

Date.now = () =>
  captureMs;

const captureUnixSeconds =
  Math.floor(
    captureMs / 1000
  );

const derivedValidUntilUnix =
  captureUnixSeconds + 3600;


/*
 * Local JSON-RPC capture state.
 */
const requestLog = [];
const capturedTransactions = [];

let localRpcFetchCount = 0;
let forbiddenExternalFetchAttemptCount = 0;


function jsonResponse(
  response,
  id,
  payload,
) {
  response.statusCode = 200;

  response.setHeader(
    "content-type",
    "application/json",
  );

  response.end(
    JSON.stringify({
      jsonrpc:
        "2.0",

      id,

      ...payload,
    })
  );
}


const server =
  createServer(
    async (
      request,
      response,
    ) => {
      try {
        if (
          request.method !== "POST"
        ) {
          response.statusCode = 405;
          response.end();

          return;
        }

        const chunks = [];

        for await (
          const chunk
          of request
        ) {
          chunks.push(
            chunk
          );
        }

        const rawBody =
          Buffer
            .concat(
              chunks
            )
            .toString(
              "utf8"
            );

        const rpc =
          JSON.parse(
            rawBody
          );

        if (
          Array.isArray(
            rpc
          )
        ) {
          throw new Error(
            "JSON-RPC batch requests are forbidden"
          );
        }

        const method =
          rpc.method;

        const params =
          rpc.params ?? [];

        requestLog.push({
          method,
          params,
        });

        switch (
          method
        ) {
          case "eth_chainId":
            jsonResponse(
              response,
              rpc.id,
              {
                result:
                  "0x107d",
              },
            );

            return;


          case "eth_getTransactionCount":
            jsonResponse(
              response,
              rpc.id,
              {
                result:
                  "0x0",
              },
            );

            return;


          case "eth_estimateGas":
            /*
             * Deterministic LOCAL result.
             * This is not a Bradbury estimate.
             */
            jsonResponse(
              response,
              rpc.id,
              {
                result:
                  "0x30d40",
              },
            );

            return;


          case "eth_gasPrice":
            jsonResponse(
              response,
              rpc.id,
              {
                result:
                  "0x1",
              },
            );

            return;


          case "eth_sendTransaction": {
            if (
              !Array.isArray(
                params
              )
              || params.length !== 1
              || typeof params[0] !== "object"
              || params[0] === null
            ) {
              throw new Error(
                "invalid eth_sendTransaction params"
              );
            }

            capturedTransactions.push(
              structuredClone(
                params[0]
              )
            );

            /*
             * Deliberately terminate SDK flow here.
             * No receipt polling can occur.
             */
            jsonResponse(
              response,
              rpc.id,
              {
                error: {
                  code:
                    -32000,

                  message:
                    "ACCORD402_OFFLINE_CAPTURE_STOP",
                },
              },
            );

            return;
          }


          default:
            jsonResponse(
              response,
              rpc.id,
              {
                error: {
                  code:
                    -32001,

                  message:
                    "ACCORD402_UNEXPECTED_LOCAL_RPC_METHOD:"
                    + String(
                      method
                    ),
                },
              },
            );

            return;
        }
      } catch (
        error
      ) {
        response.statusCode = 500;

        response.setHeader(
          "content-type",
          "application/json",
        );

        response.end(
          JSON.stringify({
            error:
              error
              instanceof Error
                ? error.message
                : String(error),
          })
        );
      }
    }
  );


await new Promise(
  (
    resolve,
    reject,
  ) => {
    server.once(
      "error",
      reject,
    );

    server.listen(
      0,
      "127.0.0.1",
      resolve,
    );
  }
);


const address =
  server.address();


if (
  !address
  || typeof address === "string"
) {
  throw new Error(
    "localhost capture server address unavailable"
  );
}


if (
  address.address
  !== "127.0.0.1"
) {
  throw new Error(
    "capture server not bound to 127.0.0.1"
  );
}


const localRpcUrl =
  "http://127.0.0.1:"
  + String(
    address.port
  );


console.log(
  "LOCAL_CAPTURE_RPC_URL="
  + localRpcUrl
);


/*
 * Guard global fetch:
 * exactly the localhost capture endpoint is permitted.
 * Bradbury or any other URL hard-fails.
 */
const realFetch =
  globalThis
    .fetch
    .bind(
      globalThis
    );


function extractUrl(
  input,
) {
  if (
    typeof input === "string"
  ) {
    return input;
  }

  if (
    input instanceof URL
  ) {
    return input.href;
  }

  if (
    input
    && typeof input.url === "string"
  ) {
    return input.url;
  }

  return String(
    input
  );
}


const allowedHref =
  new URL(
    localRpcUrl
  ).href;


globalThis.fetch =
  async (
    input,
    init,
  ) => {
    const rawUrl =
      extractUrl(
        input
      );

    const actualHref =
      new URL(
        rawUrl
      ).href;

    if (
      actualHref !== allowedHref
    ) {
      forbiddenExternalFetchAttemptCount += 1;

      throw new Error(
        "ACCORD402_EXTERNAL_FETCH_FORBIDDEN:"
        + actualHref
      );
    }

    localRpcFetchCount += 1;

    return realFetch(
      input,
      init,
    );
  };


function sha256Hex(
  bytes,
) {
  return createHash(
    "sha256"
  )
    .update(
      bytes
    )
    .digest(
      "hex"
    );
}


function measure(
  data,
) {
  if (
    typeof data !== "string"
    || !/^0x[0-9a-fA-F]*$/.test(
      data
    )
    || (
      data.length - 2
    ) % 2 !== 0
  ) {
    throw new Error(
      "captured transaction data is invalid hex"
    );
  }

  const bytes =
    Buffer.from(
      data.slice(2),
      "hex",
    );

  let zeroBytes = 0;

  for (
    const value
    of bytes
  ) {
    if (
      value === 0
    ) {
      zeroBytes += 1;
    }
  }

  const nonzeroBytes =
    bytes.length
    - zeroBytes;

  const calldataTokens =
    zeroBytes
    + (
      4
      * nonzeroBytes
    );

  const standardIntrinsicGas =
    21000
    + (
      4
      * zeroBytes
    )
    + (
      16
      * nonzeroBytes
    );

  const eip7623GasFloor =
    21000
    + (
      10
      * calldataTokens
    );

  return {
    outerCalldataBytes:
      bytes.length,

    zeroBytes,

    nonzeroBytes,

    calldataTokens,

    standardIntrinsicGas,

    eip7623GasFloor,

    effectiveIntrinsicFloor:
      Math.max(
        standardIntrinsicGas,
        eip7623GasFloor,
      ),

    outerCalldataSha256:
      sha256Hex(
        bytes
      ),
  };
}


/*
 * Existing Accord402 EIP-7623 arithmetic self-vector.
 */
const historicalDZero =
  197;

const historicalDNonzero =
  66623;

const historicalDTokens =
  historicalDZero
  + (
    4
    * historicalDNonzero
  );

const historicalDFloor =
  21000
  + (
    10
    * historicalDTokens
  );


if (
  historicalDFloor
  !== 2687890
) {
  throw new Error(
    "historical EIP-7623 self-vector failed"
  );
}


async function capture(
  label,
  code,
) {
  const requestStart =
    requestLog.length;

  const transactionStart =
    capturedTransactions.length;

  /*
   * IMPORTANT:
   * endpoint — not provider — controls ordinary RPC reads
   * in GenLayerJS 1.1.8.
   */
  const client =
    sdk.createClient({
      chain:
        chains.testnetBradbury,

      endpoint:
        localRpcUrl,

      account:
        senderAddress,
    });


  let caught = "";

  try {
    await client.deployContract({
      code,
      args: [],
    });
  } catch (
    error
  ) {
    caught =
      error
      instanceof Error
        ? error.message
        : String(error);
  }


  const localRequests =
    requestLog.slice(
      requestStart
    );

  const localTransactions =
    capturedTransactions.slice(
      transactionStart
    );


  if (
    localTransactions.length !== 1
  ) {
    throw new Error(
      label
      + ": captured transaction count "
      + localTransactions.length
      + " != 1; caught="
      + caught
    );
  }


  const transaction =
    localTransactions[0];


  const methods =
    localRequests.map(
      item =>
        item.method
    );


  const allowedMethods =
    new Set([
      "eth_chainId",
      "eth_getTransactionCount",
      "eth_estimateGas",
      "eth_gasPrice",
      "eth_sendTransaction",
    ]);


  for (
    const method
    of methods
  ) {
    if (
      !allowedMethods.has(
        method
      )
    ) {
      throw new Error(
        label
        + ": unexpected RPC method "
        + method
      );
    }
  }


  for (
    const required
    of [
      "eth_getTransactionCount",
      "eth_estimateGas",
      "eth_gasPrice",
      "eth_sendTransaction",
    ]
  ) {
    if (
      !methods.includes(
        required
      )
    ) {
      throw new Error(
        label
        + ": required local RPC method absent: "
        + required
      );
    }
  }


  if (
    methods.filter(
      method =>
        method
        === "eth_sendTransaction"
    ).length !== 1
  ) {
    throw new Error(
      label
      + ": eth_sendTransaction count != 1"
    );
  }


  if (
    typeof transaction.data
    !== "string"
  ) {
    throw new Error(
      label
      + ": captured transaction data absent"
    );
  }


  if (
    forbiddenExternalFetchAttemptCount !== 0
  ) {
    throw new Error(
      label
      + ": external fetch attempted"
    );
  }


  return {
    label,

    sourceBytes:
      Buffer.byteLength(
        code,
        "utf8",
      ),

    senderAddress,

    to:
      transaction.to
      ?? null,

    localRpcMethodTrace:
      methods,

    localhostRpcOnly:
      true,

    externalNetworkFetchAttemptCount:
      forbiddenExternalFetchAttemptCount,

    realBradburyRpcCalled:
      false,

    realGasEstimatePerformed:
      false,

    realEthSendTransactionSent:
      false,

    ...measure(
      transaction.data
    ),
  };
}


let canonical;
let d2;


try {
  canonical =
    await capture(
      "canonical-h",
      canonicalSource,
    );

  d2 =
    await capture(
      "d2-f4-f8",
      d2Source,
    );
} finally {
  await new Promise(
    (
      resolve,
      reject,
    ) => {
      server.close(
        error => {
          if (
            error
          ) {
            reject(
              error
            );
          } else {
            resolve();
          }
        }
      );
    }
  );
}


if (
  forbiddenExternalFetchAttemptCount !== 0
) {
  throw new Error(
    "external network fetch attempt occurred"
  );
}


if (
  canonical.outerCalldataBytes
  !== expectedCanonicalOuter
) {
  throw new Error(
    "canonical-H historical compatibility failed: "
    + canonical.outerCalldataBytes
    + " != "
    + expectedCanonicalOuter
  );
}


if (
  d2.outerCalldataBytes
  >= smallestBlocked
) {
  throw new Error(
    "D2 outer calldata is not below "
    + "historical blocked sample"
  );
}


const result = {
  formatVersion:
    1,

  stage:
    "R20-R24A5B1F10R3",

  mode:
    "OFFLINE_PINNED_GENLAYERJS_LOCALHOST_ENDPOINT_CAPTURE",

  capturedAtUnixMs:
    captureMs,

  capturedAtUtc:
    new Date(
      captureMs
    ).toISOString(),

  derivedValidUntilUnix:
    derivedValidUntilUnix,

  localRpcUrl:
    localRpcUrl,

  localRpcFetchCount:
    localRpcFetchCount,

  forbiddenExternalFetchAttemptCount:
    forbiddenExternalFetchAttemptCount,

  referenceSenderAddress:
    senderAddress,

  chain: {
    name:
      chains
        .testnetBradbury
        .name,

    id:
      chains
        .testnetBradbury
        .id,

    idHex:
      "0x"
      + chains
        .testnetBradbury
        .id
        .toString(
          16
        ),
  },

  sdk: {
    package:
      "genlayer-js",

    version:
      "1.1.8",

    transportOverride:
      "endpoint",
  },

  historicalAdmissionReference: {
    canonicalHOuterBytes:
      expectedCanonicalOuter,

    observedLargestEstimatableOuterBytes:
      largestOk,

    observedSmallestBlockedOuterBytes:
      smallestBlocked,

    oneKiBMarginTargetOuterBytes:
      marginTarget,
  },

  eip7623: {
    txBaseCost:
      21000,

    zeroByteTokens:
      1,

    nonzeroByteTokens:
      4,

    floorGasPerToken:
      10,

    historicalCandidateDVector: {
      zeroBytes:
        historicalDZero,

      nonzeroBytes:
        historicalDNonzero,

      computedFloor:
        historicalDFloor,

      expectedFloor:
        2687890,

      pass:
        historicalDFloor
        === 2687890,
    },
  },

  canonical,

  d2,

  comparison: {
    sourceByteSavings:
      canonical.sourceBytes
      - d2.sourceBytes,

    outerCalldataByteSavings:
      canonical.outerCalldataBytes
      - d2.outerCalldataBytes,

    d2BytesBelowObservedLargestEstimatableOuter:
      largestOk
      - d2.outerCalldataBytes,

    d2BytesBelowObservedSmallestBlockedOuter:
      smallestBlocked
      - d2.outerCalldataBytes,

    d2BytesBelowOneKiBMarginTarget:
      marginTarget
      - d2.outerCalldataBytes,

    d2BelowObservedLargestEstimatableOuter:
      d2.outerCalldataBytes
      <= largestOk,

    d2BelowObservedSmallestBlockedOuter:
      d2.outerCalldataBytes
      < smallestBlocked,

    d2MeetsOneKiBMarginTarget:
      d2.outerCalldataBytes
      <= marginTarget,
  },

  safety: {
    localhostOnlyEndpoint:
      true,

    externalNetworkFetchAttemptCount:
      forbiddenExternalFetchAttemptCount,

    bradburyRpcCalled:
      false,

    realGasEstimatePerformed:
      false,

    realSendPerformed:
      false,

    privateKeyAccessed:
      false,

    keychainAccessed:
      false,

    transactionSigned:
      false,
  },
};


await writeFile(
  outputPath,
  JSON.stringify(
    result,
    null,
    2,
  )
  + "\n",
  "utf8",
);


console.log(
  "LOCALHOST_RPC_ONLY=YES"
);

console.log(
  "LOCAL_RPC_FETCH_COUNT="
  + localRpcFetchCount
);

console.log(
  "EXTERNAL_NETWORK_FETCH_ATTEMPT_COUNT="
  + forbiddenExternalFetchAttemptCount
);

console.log(
  "CANONICAL_H_SOURCE_BYTES="
  + canonical.sourceBytes
);

console.log(
  "CANONICAL_H_OUTER_CALLDATA_BYTES="
  + canonical.outerCalldataBytes
);

console.log(
  "CANONICAL_H_OUTER_COMPATIBILITY=PASS"
);

console.log(
  "D2_SOURCE_BYTES="
  + d2.sourceBytes
);

console.log(
  "D2_OUTER_CALLDATA_BYTES="
  + d2.outerCalldataBytes
);

console.log(
  "D2_OUTER_CALLDATA_SHA256="
  + d2.outerCalldataSha256
);

console.log(
  "D2_ZERO_BYTES="
  + d2.zeroBytes
);

console.log(
  "D2_NONZERO_BYTES="
  + d2.nonzeroBytes
);

console.log(
  "D2_CALLDATA_TOKENS="
  + d2.calldataTokens
);

console.log(
  "D2_STANDARD_INTRINSIC_GAS="
  + d2.standardIntrinsicGas
);

console.log(
  "D2_EIP7623_GAS_FLOOR="
  + d2.eip7623GasFloor
);

console.log(
  "D2_EFFECTIVE_INTRINSIC_FLOOR="
  + d2.effectiveIntrinsicFloor
);

console.log(
  "D2_BYTES_BELOW_OBSERVED_LARGEST_ESTIMATABLE_OUTER="
  + result
    .comparison
    .d2BytesBelowObservedLargestEstimatableOuter
);

console.log(
  "D2_BYTES_BELOW_OBSERVED_SMALLEST_BLOCKED_OUTER="
  + result
    .comparison
    .d2BytesBelowObservedSmallestBlockedOuter
);

console.log(
  "D2_BYTES_BELOW_ONE_KIB_MARGIN_TARGET="
  + result
    .comparison
    .d2BytesBelowOneKiBMarginTarget
);

console.log(
  "D2_ONE_KIB_MARGIN_TARGET_GATE="
  + (
    result
      .comparison
      .d2MeetsOneKiBMarginTarget
      ? "PASS"
      : "FAIL"
  )
);

console.log(
  "BRADBURY_RPC_CALLED=NO"
);

console.log(
  "REAL_GAS_ESTIMATE_PERFORMED=NO"
);

console.log(
  "REAL_ETH_SEND_TRANSACTION_SENT=NO"
);

console.log(
  "LOCAL_ENDPOINT_OFFLINE_ENVELOPE_CAPTURE=PASS"
);
