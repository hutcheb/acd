

class CompsRecordException(Exception):

    def __init__(self, record_number, message):
        super().__init__(message + f"Unknown {message} version found- {record_number}")


class UnknownRxTagVersion(CompsRecordException):

    def __init__(self, record_number):
        super().__init__(record_number, "RxTag")
