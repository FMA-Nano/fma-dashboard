class RefreshManager:
    """
    Global refresh controller.

    Pages register their refresh functions here.
    The app timer calls refresh() periodically.
    """

    def __init__(self):

        self.callbacks = []


    def register(self, callback):

        if callback not in self.callbacks:

            self.callbacks.append(callback)

            print(
                "Registered refresh:",
                callback.__qualname__
            )


    def unregister(self, callback):

        if callback in self.callbacks:

            self.callbacks.remove(callback)


    def refresh(self):

        print("Refreshing all services...")

        for callback in self.callbacks:

            try:

                callback()

            except Exception as e:

                print(
                    "Refresh error:",
                    callback.__qualname__,
                    e
                )


# Global instance
refresh_manager = RefreshManager()