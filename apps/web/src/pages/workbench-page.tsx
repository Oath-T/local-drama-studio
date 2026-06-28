import { EmptyState } from "@/components/ui/empty-state";
import { AppShell } from "@/components/layout/app-shell";
import { sceneCopy } from "@/features/scenes/copy";
import { shotCopy } from "@/features/shots/copy";
import type { WorkbenchSection } from "@/features/workbench/store";
import { copy as locale } from "@/locales";

const sectionCopy = {
  characters: {
    eyebrow: locale.nav.characters,
    title: locale.nav.characters,
    emptyTitle: locale.empty.charactersTitle,
    emptyDescription: locale.empty.charactersDescription
  },
  scenes: {
    eyebrow: locale.nav.scenes,
    title: locale.nav.scenes,
    emptyTitle: sceneCopy.globalGuideTitle,
    emptyDescription: sceneCopy.globalGuideDescription
  },
  shots: {
    eyebrow: locale.nav.shots,
    title: locale.nav.shots,
    emptyTitle: shotCopy.globalGuideTitle,
    emptyDescription: shotCopy.globalGuideDescription
  },
  tasks: {
    eyebrow: locale.nav.tasks,
    title: locale.nav.tasks,
    emptyTitle: locale.empty.tasksTitle,
    emptyDescription: locale.empty.tasksDescription
  }
};

type PlaceholderSection = Exclude<WorkbenchSection, "projects">;

export function WorkbenchPage({ section }: { section: PlaceholderSection }) {
  const copy = sectionCopy[section];

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
