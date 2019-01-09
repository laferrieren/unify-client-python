from time import time as now, sleep

from unify_api_v1.models.base_resource import BaseResource
from unify_api_v1_proto.operation_pb2 import Operation as OperationProto
from unify_api_v1_proto.common_pb2 import OperationState as OperationStateProto


class Operation(BaseResource):
    """A long-running operation performed by Unify.
    Operations appear on the "Jobs" page of the Unify UI.

    By design, client-side operations represent server-side operations *at a
    particular point in time* (namely, when the operation was fetched from the
    server). In other words: Operations *will not* pick up on server-side
    changes automatically. To get an up-to-date representation, refetch the
    operation e.g. ``op = op.poll()``.
    """

    @classmethod
    def from_json(cls, client, resource_json, api_path=None):
        return super().from_json(client, resource_json, OperationProto, api_path)

    def apply_options(self, asynchronous=False, **options):
        """Applies operation options to this operation.

        **NOTE**: This function **should not** be called directly. Rather, options should be
        passed in through a higher-level function e.g. :func:`~unify_api_v1.models.dataset.resource.Dataset.refresh` .

        Synchronous mode:
            Automatically waits for operation to resolve before returning the
            operation.

        asynchronous mode:
            Immediately return the ``'PENDING'`` operation. It is
            up to the user to coordinate this operation with their code via
            :func:`~unify_api_v1.models.operation.Operation.wait` and/or
            :func:`~unify_api_v1.models.operation.Operation.poll` .

        :param asynchronous: Whether or not to run in asynchronous mode. Default: ``False``.
        :type asynchronous: bool
        :param **options: When running in synchronous mode, these options are
            passed to the underlying :func:`~unify_api_v1.models.operation.Operation.wait` call.
        :return: Operation with options applied.
        :rtype: :class:`~unify_api_v1.models.operation.Operation`
        """
        if asynchronous:
            return self
        return self.wait(**options)

    @property
    def type(self):
        """:type: str"""
        return self.data.type

    @property
    def description(self):
        """:type: str"""
        return self.data.description

    @property
    def status(self):
        return self.data.status

    @property
    def state(self):
        """Server-side state of this operation.

        Operation state can be unresolved (i.e. ``state`` is one of: ``'PENDING'``, ``'RUNNING'``),
        or resolved (i.e. `state` is one of: ``'CANCELED'``, ``'SUCCEEDED'``, ``'FAILED'``).
        Unless opting into asynchronous mode, all exposed operations should be resolved.

        Note: you only need to manually pick up server-side changes when opting into asynchronous mode when kicking off this operation.

        Usage:
            >>> op.status # operation is currently 'PENDING'
            'PENDING'
            >>> op.wait() # continually polls until operation resolves
            >>> op.status # incorrect usage; operation object status never changes.
            'PENDING'
            >>> op = op.poll() # correct usage; use value returned by Operation.poll or Operation.wait
            >>> op.status
            'SUCCEEDED'
        """
        return OperationStateProto.Name(self.status.state)

    def poll(self):
        """Poll this operation for server-side updates.

        Does not update the calling :class:`~unify_api_v1.models.Operation` object.
        Instead, returns a new :class:`~unify_api_v1.models.Operation`.

        :return: Updated representation of this operation.
        :rtype: :class:`~unify_api_v1.models.Operation`
        """
        op_json = self.client.get(self.api_path).json()
        return Operation.from_json(self.client, op_json)

    def wait(self, poll_interval_seconds=3, timeout_seconds=None):
        """Continuously polls for this operation's server-side state.

        :param int poll_interval_seconds: Time interval (in seconds) between subsequent polls.
        :param int timeout_seconds: Time (in seconds) to wait for operation to resolve.
        :raises TimeoutError: If operation takes longer than `timeout_seconds` to resolve.
        :return: Resolved operation.
        :rtype: :class:`~unify_api_v1.models.Operation`
        """
        started = now()
        op = self
        while timeout_seconds is None or now() - started < timeout_seconds:
            # https://github.com/Datatamer/javasrc/blob/f8495f0c1bac91ee2f52958059a8dcaa94fce352/pubapi/proto/src/main/proto/v1.common.proto#L13
            if op.state in ["PENDING", "RUNNING"]:
                sleep(poll_interval_seconds)
            elif op.state in ["CANCELED", "SUCCEEDED", "FAILED"]:
                return op
            op = op.poll()
        raise TimeoutError(
            f"Waiting for operation took longer than {timeout_seconds} seconds."
        )

    def succeeded(self):
        """Convenience method for checking if operation was successful.

        :return: ``True`` if operation's state is ``'SUCCEEDED'``, ``False`` otherwise.
        :rtype: :py:class:`bool`
        """
        return self.state == "SUCCEEDED"