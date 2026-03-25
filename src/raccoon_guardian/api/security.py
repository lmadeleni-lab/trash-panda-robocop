from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from raccoon_guardian.api.dependencies import AppContainer, get_container


def require_control_access(
    request: Request,
    container: AppContainer = Depends(get_container),
) -> None:
    security = container.config.security
    if not security.api_key_enabled:
        if security.allow_unsafe_local_without_key:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="control access is disabled without an API key in this environment",
        )
    if not security.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key protection is enabled but no key is configured",
        )
    provided_key = request.headers.get("x-api-key")
    if provided_key != security.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing API key",
        )
