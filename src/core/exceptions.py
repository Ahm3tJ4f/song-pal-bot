class AlreadyConnectedError(Exception):
    def __init__(self):
        super().__init__("You're already connected. Use /disconnect first.")


class InvalidPairCodeError(Exception):
    def __init__(self):
        super().__init__("Invalid or expired pair code.")


class ConnectionNotFoundError(Exception):
    def __init__(self):
        super().__init__("You're not paired")


class CannotJoinOwnCodeError(Exception):

    def __init__(self):
        super().__init__("You can't join yourself, silly!")
