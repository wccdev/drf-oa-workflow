from rest_framework.viewsets import GenericViewSet


class CusGenericViewSet(GenericViewSet):
    default_serializer_class_key = "default"

    def get_serializer_class(self):
        """
        Return the class to use for the serializer.
        Defaults to using `self.serializer_class`.

        You may want to override this if you need to provide different
        serializations depending on the incoming request.

        (Eg. admins get full serialization, others get basic serialization)
        """
        serializer_class = super().get_serializer_class()
        if isinstance(serializer_class, dict):
            if self.action in serializer_class:
                return serializer_class[self.action]
            return serializer_class[self.default_serializer_class_key]

        return serializer_class
