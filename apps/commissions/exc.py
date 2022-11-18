class ComissionException(Exception):
    def __init__(self, message: str):
        self.message = message


class NoCuentaComission(ComissionException):
    """Si el cliente tiene un producto distinto a empresa o liberate"""
