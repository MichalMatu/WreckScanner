import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const stateSource = readFileSync(new URL("../../web/app/photo_review_state.js", import.meta.url), "utf8");

function reviewStateContext() {
  const state = { confirmed: false, insurance: "unknown", draws: 0, insuranceUpdates: 0 };
  const context = {
    FIELD_PHOTO_ISSUE_TYPE_VEHICLE: "vehicle",
    activePhotoReview: { id: "photo-1", issue_type: "vehicle", redactions: [] },
    activePhotoReviewRedactionIndex: -1,
    apiLocalizedText: (_key, fallback) => fallback,
    confirmAction: async () => state.confirmed,
    drawPhotoReviewCanvas: () => { state.draws += 1; },
    normalizePhotoReviewRedaction: (value) => value,
    photoReviewActionInFlight: false,
    photoReviewDraftRect: null,
    photoReviewRedactions: [],
    photoReviewSavedSnapshot: null,
    photoReviewVehicleInsuranceStatus: () => state.insurance,
    updatePhotoReviewVehicleInsuranceUi: () => { state.insuranceUpdates += 1; },
  };
  vm.createContext(context);
  vm.runInContext(`${stateSource}
    globalThis.reviewStateApi = {
      capturePhotoReviewSnapshot,
      confirmPhotoReviewDiscard,
      photoReviewHasUnsavedChanges,
      setRedactions(value) { photoReviewRedactions = value; },
    };`, context);
  return { api: context.reviewStateApi, context, state };
}

test("photo review asks before discarding redaction changes and restores saved state", async () => {
  const { api, context, state } = reviewStateContext();
  api.capturePhotoReviewSnapshot();
  api.setRedactions([{ points: [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }] }]);
  assert.equal(api.photoReviewHasUnsavedChanges(), true);

  state.confirmed = false;
  assert.equal(await api.confirmPhotoReviewDiscard(), false);
  assert.equal(api.photoReviewHasUnsavedChanges(), true);

  state.confirmed = true;
  assert.equal(await api.confirmPhotoReviewDiscard(), true);
  assert.equal(api.photoReviewHasUnsavedChanges(), false);
  assert.equal(context.photoReviewRedactions.length, 0);
  assert.equal(state.draws, 1);
  assert.equal(state.insuranceUpdates, 1);
});

test("photo review detects an unsaved insurance decision", () => {
  const { api, state } = reviewStateContext();
  api.capturePhotoReviewSnapshot();

  state.insurance = "insured";

  assert.equal(api.photoReviewHasUnsavedChanges(), true);
});
