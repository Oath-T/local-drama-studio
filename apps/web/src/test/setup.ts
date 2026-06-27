import "@testing-library/jest-dom/vitest";

import { afterEach, vi } from "vitest";

import { queryClient } from "@/lib/query-client";

afterEach(() => {
  queryClient.clear();
  vi.restoreAllMocks();
});
