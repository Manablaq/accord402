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
  d2Path,
  capturePath,
  requestPath,
  senderAddress,
  expectedSourceSha,
  expectedSourceBytesRaw,
  expectedOuterBytesRaw,
  expectedChainIdRaw,
  expectedConsensusAddress,
] = process.argv;


const expectedSourceBytes =
  Number(
    expectedSourceBytesRaw
  );

const expectedOuterBytes =
  Number(
    expectedOuterBytesRaw
  );

const expectedChainId =
  Number(
    expectedChainIdRaw
  );


function sha256Hex(
  bytes,
) {
  return createHash(
    "sha256"
  )
    .update(bytes)
    .digest("hex");
}


const sourceBuffer =
  await readFile(
    d2Path
  );

const source =
  sourceBuffer.toString(
    "utf8"
  );


if (
  sha256Hex(sourceBuffer)
  !== expectedSourceSha
) {
  throw new Error(
    "persisted D2 SHA mismatch inside capture"
  );
}


if (
  sourceBuffer.length
  !== expectedSourceBytes
) {
  throw new Error(
    "persisted D2 byte count mismatch inside capture"
  );
}


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


const chain =
  chains.testnetBradbury;


if (!chain) {
  throw new Error(
    "testnetBradbury export missing"
  );
}


if (
  chain.id
  !== expectedChainId
) {
  throw new Error(
    "Bradbury chain ID mismatch: "
    + String(chain.id)
  );
}


const actualConsensusAddress =
  chain
    .consensusMainContract
    ?.address;


if (
  typeof actualConsensusAddress
  !== "string"
  || actualConsensusAddress.toLowerCase()
     !== expectedConsensusAddress.toLowerCase()
) {
  throw new Error(
    "pinned consensus-main address mismatch: "
    + String(actualConsensusAddress)
  );
}


/*
 * Use real current time: this payload will immediately be sent
 * to Bradbury for eth_estimateGas and must not contain a stale
 * validUntil.
 */
const captureUnixMs =
  Date.now();


let capturedEstimateParams = null;
let capturedSendTransaction = null;

const methods = [];


const server =
  createServer(
    async (
      request,
      response,
    ) => {
      const chunks = [];

      for await (
        const chunk
        of request
      ) {
        chunks.push(
          chunk
        );
      }

      const rpc =
        JSON.parse(
          Buffer
            .concat(chunks)
            .toString("utf8")
        );

      if (
        Array.isArray(rpc)
      ) {
        throw new Error(
          "batch JSON-RPC forbidden"
        );
      }

      methods.push(
        rpc.method
      );


      const reply =
        payload => {
          response.statusCode = 200;

          response.setHeader(
            "content-type",
            "application/json",
          );

          response.end(
            JSON.stringify({
              jsonrpc:
                "2.0",

              id:
                rpc.id,

              ...payload,
            })
          );
        };


      switch (
        rpc.method
      ) {
        case "eth_chainId":
          reply({
            result:
              "0x107d",
          });

          return;


        case "eth_getTransactionCount":
          reply({
            result:
              "0x0",
          });

          return;


        case "eth_estimateGas":
          if (
            capturedEstimateParams
            !== null
          ) {
            throw new Error(
              "multiple local eth_estimateGas calls"
            );
          }

          if (
            !Array.isArray(
              rpc.params
            )
            || rpc.params.length !== 1
            || typeof rpc.params[0] !== "object"
            || rpc.params[0] === null
          ) {
            throw new Error(
              "invalid eth_estimateGas params"
            );
          }

          capturedEstimateParams =
            structuredClone(
              rpc.params[0]
            );

          /*
           * Dummy LOCAL estimate only, sufficient for SDK
           * to continue until its send boundary.
           */
          reply({
            result:
              "0x30d40",
          });

          return;


        case "eth_gasPrice":
          reply({
            result:
              "0x1",
          });

          return;


        case "eth_sendTransaction":
          if (
            capturedSendTransaction
            !== null
          ) {
            throw new Error(
              "multiple local send calls"
            );
          }

          capturedSendTransaction =
            structuredClone(
              rpc.params?.[0]
            );

          /*
           * Stop before any receipt path.
           */
          reply({
            error: {
              code:
                -32000,

              message:
                "ACCORD402_LOCAL_CAPTURE_STOP",
            },
          });

          return;


        default:
          reply({
            error: {
              code:
                -32001,

              message:
                "UNEXPECTED_LOCAL_METHOD:"
                + String(
                  rpc.method
                ),
            },
          });

          return;
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
    "local capture server address unavailable"
  );
}


const localEndpoint =
  "http://127.0.0.1:"
  + String(
    address.port
  );


const realFetch =
  globalThis
    .fetch
    .bind(globalThis);


let externalFetchAttemptCount = 0;


globalThis.fetch =
  async (
    input,
    init,
  ) => {
    const raw =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input?.url;

    const actual =
      new URL(
        String(raw)
      ).href;

    const allowed =
      new URL(
        localEndpoint
      ).href;

    if (
      actual !== allowed
    ) {
      externalFetchAttemptCount += 1;

      throw new Error(
        "EXTERNAL_FETCH_FORBIDDEN_DURING_LOCAL_CAPTURE:"
        + actual
      );
    }

    return realFetch(
      input,
      init,
    );
  };


try {
  const client =
    sdk.createClient({
      chain,
      endpoint:
        localEndpoint,

      account:
        senderAddress,
    });


  try {
    await client.deployContract({
      code:
        source,

      args:
        [],
    });
  } catch (
    error
  ) {
    /*
     * Expected: local eth_sendTransaction terminates the flow.
     */
  }

} finally {
  await new Promise(
    (
      resolve,
      reject,
    ) => {
      server.close(
        error => {
          if (error) {
            reject(error);
          } else {
            resolve();
          }
        }
      );
    }
  );
}


if (
  externalFetchAttemptCount
  !== 0
) {
  throw new Error(
    "external fetch occurred during local payload construction"
  );
}


if (
  capturedEstimateParams
  === null
) {
  throw new Error(
    "SDK eth_estimateGas params were not captured"
  );
}


if (
  capturedSendTransaction
  === null
) {
  throw new Error(
    "SDK send boundary was not reached locally"
  );
}


const estimateData =
  capturedEstimateParams.data;


const sendData =
  capturedSendTransaction.data;


if (
  typeof estimateData !== "string"
  || estimateData !== sendData
) {
  throw new Error(
    "estimate/send calldata mismatch"
  );
}


if (
  capturedEstimateParams.from
    ?.toLowerCase()
  !== senderAddress.toLowerCase()
) {
  throw new Error(
    "estimate sender mismatch"
  );
}


if (
  capturedEstimateParams.to
    ?.toLowerCase()
  !== expectedConsensusAddress.toLowerCase()
) {
  throw new Error(
    "estimate consensus-main target mismatch"
  );
}


if (
  capturedEstimateParams.value
  !== "0x0"
) {
  throw new Error(
    "unexpected estimate value"
  );
}


if (
  !/^0x[0-9a-fA-F]*$/.test(
    estimateData
  )
) {
  throw new Error(
    "estimate calldata invalid"
  );
}


const calldata =
  Buffer.from(
    estimateData.slice(2),
    "hex",
  );


if (
  calldata.length
  !== expectedOuterBytes
) {
  throw new Error(
    "fresh outer calldata size mismatch: "
    + String(
      calldata.length
    )
  );
}


let zeroBytes = 0;

for (
  const value
  of calldata
) {
  if (value === 0) {
    zeroBytes += 1;
  }
}


const nonzeroBytes =
  calldata.length
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


const requestObject = {
  jsonrpc:
    "2.0",

  id:
    1,

  method:
    "eth_estimateGas",

  params: [
    capturedEstimateParams
  ],
};


await writeFile(
  requestPath,
  JSON.stringify(
    requestObject
  ),
  "utf8",
);


const captureObject = {
  formatVersion:
    1,

  stage:
    "R20-R24A5B1F11",

  captureUnixMs,

  d2Sha256:
    expectedSourceSha,

  d2Bytes:
    expectedSourceBytes,

  chainId:
    chain.id,

  consensusMainContract:
    actualConsensusAddress,

  senderAddress,

  localSdkMethodTrace:
    methods,

  localConstructionExternalFetchAttemptCount:
    externalFetchAttemptCount,

  estimateParams:
    capturedEstimateParams,

  outerCalldataBytes:
    calldata.length,

  outerCalldataSha256:
    sha256Hex(
      calldata
    ),

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

  safety: {
    localPayloadConstructionOnly:
      true,

    privateKeyAccessed:
      false,

    keychainAccessed:
      false,

    transactionSigned:
      false,

    externalSendPerformed:
      false,
  },
};


await writeFile(
  capturePath,
  JSON.stringify(
    captureObject,
    null,
    2,
  )
  + "\n",
  "utf8",
);


console.log(
  "FRESH_D2_OUTER_CALLDATA_BYTES="
  + calldata.length
);

console.log(
  "FRESH_D2_OUTER_CALLDATA_SHA256="
  + captureObject
    .outerCalldataSha256
);

console.log(
  "FRESH_D2_ZERO_BYTES="
  + zeroBytes
);

console.log(
  "FRESH_D2_NONZERO_BYTES="
  + nonzeroBytes
);

console.log(
  "FRESH_D2_EIP7623_GAS_FLOOR="
  + eip7623GasFloor
);

console.log(
  "LOCAL_SDK_METHOD_TRACE="
  + methods.join(",")
);

console.log(
  "LOCAL_CONSTRUCTION_EXTERNAL_FETCH_ATTEMPT_COUNT="
  + externalFetchAttemptCount
);

console.log(
  "EXACT_FRESH_ETH_ESTIMATEGAS_REQUEST_CREATED=YES"
);
