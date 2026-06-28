import { useState, type MouseEvent, type ReactNode } from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger
} from "@/components/ui/alert-dialog";
import { characterCopy } from "@/features/characters/copy";

interface ConfirmDeleteDialogProps {
  title: string;
  description: string;
  trigger: ReactNode;
  onConfirm: () => Promise<void>;
}

export function ConfirmDeleteDialog({
  title,
  description,
  trigger,
  onConfirm
}: ConfirmDeleteDialogProps) {
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleConfirm(event: MouseEvent<HTMLButtonElement>) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await onConfirm();
      setOpen(false);
    } catch {
      // The caller owns the visible error message; keep the dialog state stable on failure.
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>{trigger}</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={submitting}>{characterCopy.cancel}</AlertDialogCancel>
          <AlertDialogAction disabled={submitting} onClick={handleConfirm}>
            {submitting ? characterCopy.deleting : characterCopy.confirmDelete}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
