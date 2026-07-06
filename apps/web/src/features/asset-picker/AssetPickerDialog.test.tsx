import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { assetPickerCopy } from "./copy";
import { AssetPickerDialog } from "./components/asset-picker-dialog";
import type { PickerOptionItem } from "./types";

const projectId = "11111111-1111-4111-8111-111111111111";
const shotId = "22222222-2222-4222-8222-222222222222";

const item: PickerOptionItem = {
  id: "character-1",
  type: "character",
  name: "林知夏",
  description: "主角",
  thumbnail_url: "/api/media/media-1/thumbnail",
  content_url: "/api/media/media-1/content",
  badges: ["身份基准图"],
  source: { kind: "character", label: "人物库" },
  is_selected: false,
  is_adopted: false,
  metadata: { default_look_id: "look-1" }
};

function renderWithClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function mockPickerApi(responseItems: PickerOptionItem[], status = 200) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
    Promise.resolve(
      new Response(
        JSON.stringify(
          status >= 400
            ? { error: { code: "PICKER_FAILED", message: "failed" } }
            : { items: responseItems, total: responseItems.length }
        ),
        {
          status,
          headers: { "Content-Type": "application/json" }
        }
      )
    )
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("AssetPickerDialog", () => {
  it("opens, searches, selects an item, and confirms", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    mockPickerApi([item]);

    renderWithClient(
      <AssetPickerDialog
        open
        onOpenChange={() => undefined}
        projectId={projectId}
        scope="shot"
        assetType="character"
        shotId={shotId}
        title={assetPickerCopy.chooseCharacter}
        onConfirm={onConfirm}
      />
    );

    expect(await screen.findByText("林知夏")).toBeInTheDocument();
    await user.type(screen.getByLabelText(assetPickerCopy.searchPlaceholder), "林");
    await user.click(screen.getByRole("button", { name: /林知夏/ }));
    await user.click(screen.getByRole("button", { name: assetPickerCopy.confirm }));

    expect(onConfirm).toHaveBeenCalledWith(expect.objectContaining({ id: item.id }));
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalled();
    });
  });

  it("shows empty state", async () => {
    mockPickerApi([]);
    renderWithClient(
      <AssetPickerDialog
        open
        onOpenChange={() => undefined}
        projectId={projectId}
        scope="shot"
        assetType="scene"
        shotId={shotId}
        title={assetPickerCopy.chooseScene}
        onConfirm={() => undefined}
      />
    );

    expect(screen.getByLabelText(assetPickerCopy.searchPlaceholder)).toBeInTheDocument();
    expect(await screen.findByText(assetPickerCopy.emptyTitle)).toBeInTheDocument();
  });

  it("shows error state", async () => {
    mockPickerApi([], 500);
    renderWithClient(
      <AssetPickerDialog
        open
        onOpenChange={() => undefined}
        projectId={projectId}
        scope="shot"
        assetType="scene"
        shotId={shotId}
        title={assetPickerCopy.chooseScene}
        onConfirm={() => undefined}
      />
    );

    expect(await screen.findByText(assetPickerCopy.loadFailed)).toBeInTheDocument();
  });

  it("does not confirm an already selected item", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    mockPickerApi([{ ...item, is_selected: true, badges: ["已绑定"] }]);

    renderWithClient(
      <AssetPickerDialog
        open
        onOpenChange={() => undefined}
        projectId={projectId}
        scope="shot"
        assetType="character"
        shotId={shotId}
        title={assetPickerCopy.chooseCharacter}
        onConfirm={onConfirm}
      />
    );

    expect(await screen.findByText("林知夏")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: assetPickerCopy.confirm })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: assetPickerCopy.confirm }));
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
