from app.domain.health import HealthCheckResponse


class HealthService:
    def get_health(self) -> HealthCheckResponse:
        return HealthCheckResponse(status="ok", service="local-drama-studio-api")


def get_health_service() -> HealthService:
    return HealthService()
