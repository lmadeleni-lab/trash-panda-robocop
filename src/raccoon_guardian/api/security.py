from __future__ import annotations

from ipaddress import ip_address, ip_network

from fastapi import Depends, HTTPException, Request, status

from raccoon_guardian.api.dependencies import AppContainer, get_container


def _client_host(request: Request) -> str | None:
    client = request.client
    return client.host if client is not None else None


def _trusted_client(request: Request, container: AppContainer) -> bool:
    host = _client_host(request)
    if host is None:
        return False
    try:
        host_ip = ip_address(host)
    except ValueError:
        return False
    return any(
        host_ip in ip_network(cidr, strict=False)
        for cidr in container.config.security.trusted_client_cidrs
    )


def require_trusted_network_access(
    request: Request,
    container: AppContainer = Depends(get_container),
) -> None:
    security = container.config.security
    if not security.trusted_network_required:
        return
    if not _trusted_client(request, container):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="client is outside the trusted network boundary",
        )


def require_control_access(
    request: Request,
    container: AppContainer = Depends(get_container),
) -> None:
    require_trusted_network_access(request, container)
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


def require_sensitive_read_access(
    request: Request,
    container: AppContainer = Depends(get_container),
) -> None:
    require_trusted_network_access(request, container)
