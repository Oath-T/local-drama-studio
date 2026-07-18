import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { StudioShellDemo } from "./components/studio-shell-demo";
import { getStudioShellStorageKey } from "./layout-state";

const storageKey = getStudioShellStorageKey("studio-ui-demo");

function renderDemo() {
  return render(<StudioShellDemo />);
}

function widthOf(testId: string) {
  return (screen.getByTestId(testId) as HTMLElement).style.width;
}

function heightOf(testId: string) {
  return (screen.getByTestId(testId) as HTMLElement).style.height;
}

beforeEach(() => {
  vi.useRealTimers();
  window.localStorage.clear();
  Object.defineProperty(window, "innerWidth", { configurable: true, value: 1920 });
  window.dispatchEvent(new Event("resize"));
});

describe("StudioShellDemo", () => {
  it("toggles the global navigation and changes the active demo module", async () => {
    const user = userEvent.setup();
    renderDemo();

    const menuButton = screen.getByRole("button", { name: "展开全局导航" });
    expect(menuButton).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByTestId("studio-global-nav")).toHaveStyle({ width: "64px" });

    await user.click(menuButton);
    expect(screen.getByRole("button", { name: "折叠全局导航" })).toHaveAttribute(
      "aria-expanded",
      "true"
    );
    expect(screen.getByTestId("studio-global-nav")).toHaveStyle({ width: "200px" });

    await user.click(screen.getByRole("button", { name: "角色库" }));
    expect(screen.getByRole("button", { name: "角色库" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("当前模块：角色库 · 故事板")).toBeInTheDocument();
    expect(screen.getByText("已切换到 角色库 示例模块")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "折叠全局导航" }));
    expect(screen.getByRole("button", { name: "展开全局导航" })).toHaveAttribute(
      "aria-expanded",
      "false"
    );
  });

  it("switches the top workspace tabs and visible center content", async () => {
    const user = userEvent.setup();
    renderDemo();

    expect(screen.getByRole("heading", { name: "故事板演示区域" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "工作流画布" }));
    expect(screen.getByRole("button", { name: "工作流画布" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByRole("heading", { name: "工作流画布演示区域" })).toBeInTheDocument();
    expect(screen.getByText("中央视图已切换：工作流画布")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "镜头生成控制台" }));
    expect(screen.getByRole("heading", { name: "镜头生成控制台演示区域" })).toBeInTheDocument();
    expect(screen.getByLabelText("Prompt 示例")).toBeInTheDocument();
  });

  it("switches inspector tabs and displays different local content", async () => {
    const user = userEvent.setup();
    renderDemo();

    expect(screen.getByRole("heading", { name: "当前示例镜头摘要" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "生成" }));
    expect(screen.getByRole("button", { name: "生成" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { name: "生成参数面板" })).toBeInTheDocument();
    expect(screen.getByLabelText("Inspector 风格选择")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "历史" }));
    expect(screen.getByRole("heading", { name: "历史操作记录" })).toBeInTheDocument();
    expect(screen.getByText("Run #1 · completed")).toBeInTheDocument();
  });

  it("opens the smart-start dialog and closes it with visible feedback", async () => {
    const user = userEvent.setup();
    renderDemo();

    await user.click(screen.getByRole("button", { name: "打开智能续作起点页" }));
    expect(
      await screen.findByRole("dialog", { name: "智能续作起点页预览" })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "确认" }));
    expect(screen.queryByRole("dialog", { name: "智能续作起点页预览" })).not.toBeInTheDocument();
    expect(screen.getByText("智能续作起点页预览已确认")).toBeInTheDocument();
  });

  it("expands the bottom workspace and switches all bottom tabs", async () => {
    const user = userEvent.setup();
    renderDemo();

    expect(screen.getByTestId("studio-bottom-panel")).toHaveStyle({ height: "36px" });
    expect(screen.queryByRole("heading", { name: "时间线演示内容" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "展开底部工作区" }));
    expect(screen.getByTestId("studio-bottom-panel")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "时间线演示内容" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "运行任务" }));
    expect(screen.getByRole("heading", { name: "运行任务演示内容" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "生成队列" }));
    expect(screen.getByRole("heading", { name: "生成队列演示内容" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "问题" }));
    expect(screen.getByRole("heading", { name: "问题演示内容" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "折叠底部工作区" }));
    expect(screen.getByTestId("studio-bottom-panel")).toHaveStyle({ height: "36px" });
    expect(screen.queryByRole("heading", { name: "问题演示内容" })).not.toBeInTheDocument();
  });

  it("keeps component demo controls stateful and visible", async () => {
    const user = userEvent.setup();
    renderDemo();

    await user.click(screen.getByRole("button", { name: "展开底部工作区" }));
    expect(screen.getByRole("heading", { name: "组件演示" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Primary Button" }));
    expect(screen.getByText("Primary Button 已触发")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Secondary Button" }));
    expect(screen.getByText("Secondary Button 已更新本地状态")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Dialog Button" }));
    expect(await screen.findByRole("dialog", { name: "提示" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "取消" }));
    expect(screen.queryByRole("dialog", { name: "提示" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Confirm Dialog" }));
    expect(await screen.findByRole("dialog", { name: "确认操作" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "确认" }));
    expect(screen.getByText("Confirm Dialog 已确认")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Demo 下拉选择"), "商业质感");
    expect(screen.getByText(/当前选择：商业质感/)).toBeInTheDocument();

    await user.click(screen.getByRole("switch", { name: "Demo Switch" }));
    expect(screen.getByRole("switch", { name: "Demo Switch" })).toHaveAttribute(
      "aria-checked",
      "false"
    );
    expect(screen.getByText(/Switch：关/)).toBeInTheDocument();

    await user.type(screen.getByLabelText("TextInput"), "demo");
    expect(screen.getByText(/输入长度：4/)).toBeInTheDocument();

    await user.type(screen.getByLabelText("TextArea"), "abc");
    expect(screen.getByText(/备注字数：3/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "状态" }));
    expect(screen.getByText("Tabs 当前内容：草稿、就绪、失败、已采用等状态规范。")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Disabled Button" }));
    expect(screen.queryByText("Disabled Button 已触发")).not.toBeInTheDocument();
  });

  it("shows a loading state instead of only changing color", async () => {
    const user = userEvent.setup();
    renderDemo();

    await user.click(screen.getByRole("button", { name: "展开底部工作区" }));
    await user.click(screen.getByRole("button", { name: "Loading Button" }));

    expect(screen.getByRole("button", { name: "Loading..." })).toBeDisabled();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Loading Button" })).not.toBeDisabled();
    }, { timeout: 1200 });
  });

  it("clamps resizable panel sizes and clears the resize shield", async () => {
    const user = userEvent.setup();
    renderDemo();

    fireEvent.pointerDown(screen.getByTestId("left-resizer"), { clientX: 0, pointerId: 1 });
    expect(screen.getByTestId("studio-resize-shield")).toBeInTheDocument();
    fireEvent.pointerMove(window, { clientX: 500 });
    fireEvent.pointerUp(window);
    expect(screen.queryByTestId("studio-resize-shield")).not.toBeInTheDocument();
    expect(widthOf("studio-left-panel")).toBe("480px");

    fireEvent.pointerDown(screen.getByTestId("right-resizer"), { clientX: 1000, pointerId: 1 });
    expect(screen.getByTestId("studio-resize-shield")).toBeInTheDocument();
    fireEvent.pointerCancel(window);
    expect(screen.queryByTestId("studio-resize-shield")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "展开底部工作区" }));
    fireEvent.pointerDown(screen.getByTestId("bottom-resizer"), { clientY: 500, pointerId: 1 });
    fireEvent.pointerMove(window, { clientY: -200 });
    fireEvent.pointerUp(window);
    expect(heightOf("studio-bottom-panel")).toBe("560px");

    fireEvent.doubleClick(screen.getByTestId("bottom-resizer"));
    expect(heightOf("studio-bottom-panel")).toBe("260px");
  });

  it("collapses side panels, uses focus mode, and resets defaults", async () => {
    const user = userEvent.setup();
    renderDemo();

    await user.click(screen.getByRole("button", { name: "折叠左侧上下文面板" }));
    expect(screen.queryByTestId("studio-left-panel")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "展开左栏" }));
    expect(screen.getByTestId("studio-left-panel")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "折叠 Inspector" }));
    expect(screen.queryByTestId("studio-right-panel")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "展开 Inspector" }));
    expect(screen.getByTestId("studio-right-panel")).toBeInTheDocument();

    fireEvent.pointerDown(screen.getByTestId("left-resizer"), { clientX: 0, pointerId: 1 });
    fireEvent.pointerMove(window, { clientX: 500 });
    fireEvent.pointerUp(window);
    expect(widthOf("studio-left-panel")).toBe("480px");

    fireEvent.keyDown(window, { key: "Tab" });
    await waitFor(() => {
      expect(screen.queryByTestId("studio-left-panel")).not.toBeInTheDocument();
      expect(screen.queryByTestId("studio-right-panel")).not.toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "退出专注" }));
    expect(screen.getByTestId("studio-left-panel")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "恢复默认布局" }));
    expect(screen.getByTestId("studio-global-nav")).toHaveStyle({ width: "64px" });
    expect(screen.getByTestId("studio-left-panel")).toHaveStyle({ width: "280px" });
    expect(screen.getByTestId("studio-right-panel")).toHaveStyle({ width: "440px" });
  });

  it("does not toggle focus mode when Tab is pressed inside an input", () => {
    renderDemo();

    const searchInput = screen.getByLabelText("镜头列表（7）");
    searchInput.focus();
    fireEvent.keyDown(searchInput, { key: "Tab" });

    expect(screen.getByTestId("studio-left-panel")).toBeInTheDocument();
    expect(screen.getByTestId("studio-right-panel")).toBeInTheDocument();
  });

  it("persists layout and falls back when persisted data is invalid", async () => {
    const user = userEvent.setup();
    const firstRender = renderDemo();

    await user.click(screen.getByRole("button", { name: "展开全局导航" }));
    await user.click(screen.getByRole("button", { name: "展开底部工作区" }));

    expect(JSON.parse(window.localStorage.getItem(storageKey) ?? "{}")).toMatchObject({
      navCollapsed: false,
      bottomExpanded: true
    });

    firstRender.unmount();
    const secondRender = renderDemo();
    expect(screen.getByTestId("studio-global-nav")).toHaveStyle({ width: "200px" });
    expect(screen.getByTestId("studio-bottom-panel")).toBeInTheDocument();

    window.localStorage.setItem(storageKey, JSON.stringify({ version: 999, leftWidth: 999 }));
    secondRender.unmount();
    renderDemo();
    expect(screen.getByTestId("studio-global-nav")).toHaveStyle({ width: "64px" });
    expect(widthOf("studio-left-panel")).toBe("280px");
    expect(widthOf("studio-right-panel")).toBe("440px");
  });

  it("compact drawers close without leaving a blocking backdrop at 1024px and 768px", async () => {
    const user = userEvent.setup();

    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1024 });
    window.dispatchEvent(new Event("resize"));
    const firstRender = renderDemo();

    expect(screen.queryByTestId("studio-left-panel")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "上下文" }));
    expect(screen.getByTestId("compact-drawer-backdrop")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "关闭辅助抽屉" }));
    expect(screen.queryByTestId("compact-drawer-backdrop")).not.toBeInTheDocument();

    firstRender.unmount();
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 768 });
    window.dispatchEvent(new Event("resize"));
    renderDemo();

    await user.click(screen.getByRole("button", { name: "Inspector" }));
    expect(screen.getByTestId("compact-drawer-backdrop")).toBeInTheDocument();
    await user.click(screen.getByTestId("compact-drawer-backdrop"));
    expect(screen.queryByTestId("compact-drawer-backdrop")).not.toBeInTheDocument();
  });
});
