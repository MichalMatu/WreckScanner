from __future__ import annotations

import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


class PhotoReviewFrontendContracts(unittest.TestCase):
    def test_admin_review_reload_preserves_selection_context(self):
        review_js = (ROOT_DIR / "web" / "app" / "photo_review.js").read_text(encoding="utf-8")

        self.assertIn("function photoReviewSelectionAfterReload(items, preferredId, fallbackIndex)", review_js)
        self.assertIn("async function loadPhotoReviewQueue(options = {})", review_js)
        self.assertIn("const previousActiveId = options.preferredPhotoId ?? activePhotoReview?.id ?? null;", review_js)
        self.assertIn(
            "const nextActiveId = photoReviewSelectionAfterReload(nextItems, previousActiveId, previousActiveIndex);",
            review_js,
        )
        self.assertIn("selectPhotoReview(nextActiveId, { preserveScrollTop: preservedScrollTop });", review_js)
        self.assertIn("preferredPhotoId: savedPhotoId", review_js)
        self.assertIn("fallbackIndex: savedPhotoIndex", review_js)
        self.assertIn("fallbackIndex: deletedPhotoIndex", review_js)
        self.assertNotIn("if (photoReviewItems[0]) selectPhotoReview(photoReviewItems[0].id);", review_js)

    def test_queue_reload_ignores_stale_responses(self):
        review_js = (ROOT_DIR / "web" / "app" / "photo_review.js").read_text(encoding="utf-8")

        self.assertIn("let photoReviewQueueRequest = 0;", review_js)
        self.assertIn("const queueRequest = ++photoReviewQueueRequest;", review_js)
        self.assertIn("const isCurrentQueueRequest = () => queueRequest === photoReviewQueueRequest;", review_js)
        self.assertIn("if (!isCurrentQueueRequest()) return;", review_js)
        self.assertLess(
            review_js.index("const data = await apiJson(`${ADMIN_PHOTOS_URL}?${params.toString()}`"),
            review_js.index("if (!isCurrentQueueRequest()) return;"),
        )

    def test_review_actions_lock_while_request_is_in_flight(self):
        review_js = (ROOT_DIR / "web" / "app" / "photo_review.js").read_text(encoding="utf-8")

        self.assertIn("let photoReviewActionInFlight = false;", review_js)
        self.assertIn("function setPhotoReviewActionInFlight(inFlight)", review_js)
        self.assertIn("function updatePhotoReviewActionLock()", review_js)
        self.assertIn(".photo-review-actions button", review_js)
        self.assertIn(".photo-review-list button", review_js)
        self.assertIn('input[name="photo-review-vehicle-insurance-status"]', review_js)
        self.assertIn("if (photoReviewActionInFlight) return;", review_js)
        self.assertIn("setPhotoReviewActionInFlight(true);", review_js)
        self.assertIn("setPhotoReviewActionInFlight(false);", review_js)
        self.assertIn("button.disabled = photoReviewActionInFlight || !canDelete;", review_js)

    def test_image_loading_ignores_stale_selection(self):
        review_js = (ROOT_DIR / "web" / "app" / "photo_review.js").read_text(encoding="utf-8")

        self.assertIn("let photoReviewSelectionRequest = 0;", review_js)
        self.assertIn("const selectionRequest = ++photoReviewSelectionRequest;", review_js)
        self.assertIn("const isCurrentSelection = () => selectionRequest === photoReviewSelectionRequest", review_js)
        self.assertIn("if (!isCurrentSelection()) return;", review_js)
        self.assertIn("const imageSrc = await photoReviewOriginalImageSrc(item, isCurrentSelection);", review_js)

    def test_review_list_supports_keyboard_navigation(self):
        review_js = (ROOT_DIR / "web" / "app" / "photo_review.js").read_text(encoding="utf-8")

        self.assertIn('data-photo-review-id="${escapeHtml(item.id)}"', review_js)
        self.assertIn("function focusPhotoReviewItem(itemId)", review_js)
        self.assertIn("function stepPhotoReviewSelection(delta)", review_js)
        self.assertIn("topOpenModalBackdrop()?.id !== 'modal-photo-review'", review_js)
        self.assertIn("if (list && list.contains(target)) return true;", review_js)
        self.assertIn("return target === document.body || target === document.documentElement;", review_js)
        self.assertIn("event.key === 'ArrowDown'", review_js)
        self.assertIn("event.key === 'ArrowUp'", review_js)
        self.assertIn("event.key === 'Home'", review_js)
        self.assertIn("event.key === 'End'", review_js)
        self.assertIn("selectPhotoReview(item.id, { focusListItem: true });", review_js)


if __name__ == "__main__":
    unittest.main()
