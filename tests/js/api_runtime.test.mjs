import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const apiSource = readFileSync(new URL("../../web/app/api.js", import.meta.url), "utf8");

function apiContext(fetchImpl) {
  const sessionStates = [];
  const events = [];
  const context = {
    AbortController,
    ApiError: undefined,
    CustomEvent: class CustomEvent {
      constructor(type) { this.type = type; }
    },
    DOMException,
    document: { dispatchEvent: (event) => events.push(event.type) },
    fetch: fetchImpl,
    setAdminAuthenticated: (value) => sessionStates.push(value),
    window: { clearTimeout, setTimeout },
  };
  vm.createContext(context);
  vm.runInContext(`${apiSource}\nglobalThis.testApiJson = apiJson;`, context);
  return { apiJson: context.testApiJson, events, sessionStates };
}

function abortablePendingFetch(_url, options) {
  return new Promise((_resolve, reject) => {
    options.signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
  });
}

test("apiJson times out a request that never resolves", async () => {
  const { apiJson } = apiContext(abortablePendingFetch);

  await assert.rejects(
    apiJson("/slow", { timeoutMs: 5 }),
    (error) => error.payload?.code === "timeout",
  );
});

test("apiJson cancels through a caller signal", async () => {
  const { apiJson } = apiContext(abortablePendingFetch);
  const controller = new AbortController();
  const request = apiJson("/cancel", { signal: controller.signal, timeoutMs: 1000 });
  controller.abort();

  await assert.rejects(request, (error) => error.payload?.code === "cancelled");
});

test("apiJson invalidates the admin session on 401", async () => {
  const response = {
    ok: false,
    status: 401,
    headers: { get: () => "request-1" },
    json: async () => ({ error: "expired" }),
  };
  const { apiJson, events, sessionStates } = apiContext(async () => response);

  await assert.rejects(apiJson("/admin"), (error) => error.status === 401 && error.requestId === "request-1");
  assert.deepEqual(sessionStates, [false]);
  assert.deepEqual(events, ["adminsessionexpired"]);
});

test("apiJson distinguishes network failures", async () => {
  const { apiJson } = apiContext(async () => { throw new TypeError("offline"); });

  await assert.rejects(apiJson("/offline"), (error) => error.payload?.code === "network");
});
