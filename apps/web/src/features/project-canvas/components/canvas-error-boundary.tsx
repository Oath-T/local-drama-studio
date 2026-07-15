import { Component, type ReactNode } from "react";
import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { StatusMessage } from "@/components/ui/status-message";

interface CanvasErrorBoundaryProps {
  children: ReactNode;
  title?: string;
}

interface CanvasErrorBoundaryState {
  hasError: boolean;
}

export class CanvasErrorBoundary extends Component<
  CanvasErrorBoundaryProps,
  CanvasErrorBoundaryState
> {
  state: CanvasErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): CanvasErrorBoundaryState {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <section className="rounded-md border border-danger/40 bg-danger/10 p-4">
          <StatusMessage tone="error">
            {this.props.title ?? "创作画布加载失败，请重试。"}
          </StatusMessage>
          <Button
            type="button"
            variant="secondary"
            className="mt-3"
            onClick={() => this.setState({ hasError: false })}
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            重试
          </Button>
        </section>
      );
    }

    return this.props.children;
  }
}
