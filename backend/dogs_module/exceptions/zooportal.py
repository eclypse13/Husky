"""
Ошибки при работе с Zooportal.
"""

# Страница открылась, но сайт показал своё сообщение об ошибке (например, результаты скрыты, исп. для zooportal_show)
class SiteMessageError(RuntimeError):
    def __init__(self, message: str, html: str = ''):
        super().__init__(message)
        self.html = html