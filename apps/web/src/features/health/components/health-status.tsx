import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, RefreshCw, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { fetchHealth } from "@/features/health/api";

export function HealthStatus() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth
  });

  if (healthQuery.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted" role="status">
        <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" />
        正在连接后端服务
      </div>
    );
  }

  if (healthQuery.isError) {
    return (
      <div className="flex flex-wrap items-center gap-3" role="alert">
        <div className="flex items-center gap-2 text-sm text-danger">
          <XCircle className="h-4 w-4" aria-hidden="true" />
          后端连接失败
        </div>
        <span className="text-xs text-muted">请确认 FastAPI 服务正在运行。</span>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={() => void healthQuery.refetch()}
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          重新连接
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-sm text-success" role="status">
      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
      后端服务已连接
    </div>
  );
}
