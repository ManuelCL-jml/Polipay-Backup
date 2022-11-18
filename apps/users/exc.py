class UserAdminException(Exception):
    def __init__(self, message: str):
        self.message = message


class YouNotSuperUser(UserAdminException):
    """Si el usuario actual hace una operación que unicamente un super puede hacer"""


class NotificationPolipayExceptions(Exception):
    def __init__(self, message: str):
        self.message = message


class NotificationCodeExpired(NotificationPolipayExceptions):
    """ Si el codigo de 4 digitos ya expiro """


class NotificationUserNotExists(NotificationPolipayExceptions):
    """ Si el usuario no existe """


class NotificationUserCodeInvalid(NotificationPolipayExceptions):
    """ Si el codigo de cuatro digitos es invalido """
