import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "./App";

function renderApp() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false
      }
    }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  );
}

function mockHealthSuccess() {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "ok",
        service: "local-drama-studio-api"
      }),
      {
        status: 200,
        headers: {
          "Content-Type": "application/json"
        }
      }
    )
  );
}

function mockHealthFailure() {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Connection refused"));
}

describe("App", () => {
  it("renders the workbench home page", () => {
    mockHealthSuccess();
    renderApp();

    expect(screen.getByText("项目工作台")).toBeInTheDocument();
    expect(screen.getByText("还没有创建项目")).toBeInTheDocument();
  });

  it("shows a successful health state", async () => {
    mockHealthSuccess();
    renderApp();

    expect(await screen.findByText("后端服务已连接")).toBeInTheDocument();
  });

  it("shows a failed health state", async () => {
    mockHealthFailure();
    renderApp();

    expect(await screen.findByText("后端连接失败")).toBeInTheDocument();
  });

  it("shows a reconnect button after failure", async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new Error("Connection refused"))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            status: "ok",
            service: "local-drama-studio-api"
          }),
          {
            status: 200,
            headers: {
              "Content-Type": "application/json"
            }
          }
        )
      );

    renderApp();

    const reconnectButton = await screen.findByRole("button", { name: "重新连接" });
    expect(reconnectButton).toBeInTheDocument();

    await user.click(reconnectButton);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });
});
