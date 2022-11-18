class JwtDynamicTokenException(Exception):
    def __init__(self, message):
        self.message = message


class TokenAlreadyActive(JwtDynamicTokenException):
    """El token sigue activo"""


class TokenDoesNotExist(JwtDynamicTokenException):
    """El token no existe"""


class TokenNotProvided(JwtDynamicTokenException):
    """Si el cliente envia vacio el token"""
