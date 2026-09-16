from abc import ABC, abstractmethod


class NotificationSender(ABC):
    @abstractmethod
    def send(self, title: str, message: str) -> None:
        raise NotImplementedError
