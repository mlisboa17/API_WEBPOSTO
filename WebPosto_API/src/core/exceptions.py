class WebPostoIntegrationError(Exception):
    pass


class AuthorizationError(WebPostoIntegrationError):
    pass


class BlockedEndpointError(WebPostoIntegrationError):
    pass
