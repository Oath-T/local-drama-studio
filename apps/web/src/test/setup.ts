import "@testing-library/jest-dom/vitest";

import { afterEach, vi } from "vitest";

import { queryClient } from "@/lib/query-client";

if (!window.PointerEvent) {
  window.PointerEvent = MouseEvent as typeof PointerEvent;
}

if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
}

if (!Element.prototype.setPointerCapture) {
  Element.prototype.setPointerCapture = () => undefined;
}

if (!Element.prototype.releasePointerCapture) {
  Element.prototype.releasePointerCapture = () => undefined;
}

if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => undefined;
}

afterEach(() => {
  queryClient.clear();
  vi.restoreAllMocks();
});
