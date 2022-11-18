class ProductException(Exception):
    def __init__(self, message: str):
        self.message = message


class YouNotHaveProduct(ProductException):
    """ Si el cliente tiene un producto distinto al de polipay dispersa o liberate """


class ProductDoestNotExists(ProductException):
    """ Si el producto no coincide con el catalogado en la base de datos """
