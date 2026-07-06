import { EmptyState } from "@/components/ui/empty-state";

export function AssetPickerEmptyState({
  title,
  description
}: {
  title: string;
  description: string;
}) {
  return <EmptyState title={title} description={description} />;
}
