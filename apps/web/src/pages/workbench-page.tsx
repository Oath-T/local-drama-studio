import { EmptyState } from "@/components/ui/empty-state";
import { AppShell } from "@/components/layout/app-shell";
import { useWorkbenchStore } from "@/features/workbench/store";

const sectionCopy = {
  projects: {
    eyebrow: "项目",
    title: "项目工作台",
    emptyTitle: "还没有创建项目",
    emptyDescription: "项目、角色、场景、道具和镜头资产管理将在后续 Sprint 中逐步接入。"
  },
  characters: {
    eyebrow: "角色库",
    title: "角色资产",
    emptyTitle: "角色库尚未实现",
    emptyDescription: "本页会用于管理人物定妆照、服装和表情参考。"
  },
  scenes: {
    eyebrow: "场景库",
    title: "场景资产",
    emptyTitle: "场景库尚未实现",
    emptyDescription: "本页会用于管理场景、道具和环境参考。"
  },
  shots: {
    eyebrow: "镜头",
    title: "镜头列表",
    emptyTitle: "镜头系统尚未实现",
    emptyDescription: "本页会用于组织镜头、参考图片选择和制作状态。"
  },
  tasks: {
    eyebrow: "生成任务",
    title: "任务队列",
    emptyTitle: "生成任务尚未实现",
    emptyDescription: "当前 Sprint 不调用图像模型、视频模型或 ComfyUI。"
  }
};

export function WorkbenchPage() {
  const activeSection = useWorkbenchStore((state) => state.activeSection);
  const copy = sectionCopy[activeSection];

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5">
        <section className="border-b border-border pb-4">
          <div className="text-xs font-medium uppercase tracking-[0.12em] text-muted">
            {copy.eyebrow}
          </div>
          <h1 className="mt-2 text-2xl font-semibold text-foreground">{copy.title}</h1>
        </section>

        <EmptyState title={copy.emptyTitle} description={copy.emptyDescription} />
      </div>
    </AppShell>
  );
}
