import datetime
from contextlib import contextmanager
from functools import wraps
from typing import Any, Dict, Iterable, TypeVar, Union, Callable, List

import prefect
from prefect.core import Flow, Task
from prefect.engine.flow_runner import FlowRunner
from prefect.engine.state import State
from prefect.engine.task_runner import TaskRunner
from prefect.utilities.json import Serializable

Future = TypeVar("Future")


class Executor(Serializable):
    def __init__(self):
        pass

    @contextmanager
    def start(self):
        """
        This method is called
        """
        yield self

    def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> Future:
        """
        Submit a function to the executor for execution. Returns a future.
        """
        raise NotImplementedError()

    def wait(self, futures: List[Future], timeout: datetime.timedelta = None) -> Any:
        """
        Resolves futures to their values. Blocks until the future is complete.
        """
        raise NotImplementedError()

    def set_state(
        self,
        current_state: State,
        state: State,
        data: Any = None,
        message: Union[str, Exception] = None,
    ) -> State:
        return state(data=data, message=message)

    def run_flow(
        self,
        flow: Flow,
        state: State,
        task_states: Dict[Task, State],
        start_tasks: Iterable[Task],
        return_tasks: Iterable[Task],
        parameters: Dict,
        context: Dict,
    ):
        context = context or {}
        context.update(prefect.context)
        flow_runner = FlowRunner(flow=flow, executor=self)

        return self.submit(
            flow_runner.run,
            flow=flow,
            state=state,
            task_states=task_states,
            start_tasks=start_tasks,
            return_tasks=return_tasks,
            context=context,
            parameters=parameters,
        )

    def run_task(
        self,
        task: Task,
        state: State,
        upstream_states: Dict[Task, State],
        inputs: Dict[str, Any],
        ignore_trigger=False,
        context=None,
    ):
        context = context or {}
        context.update(prefect.context, _executor=self)
        task_runner = prefect.engine.TaskRunner(task=task)

        checked_state = self.submit(
            task_runner.check_task,
            state=state,
            upstream_states=upstream_states,
            ignore_trigger=ignore_trigger,
            context=context,
        )

        # if check_task returns None, then the state should not be changed
        if not checked_state:
            return state

        final_state = self.submit(
            task_runner.run_task, state=checked_state, inputs=inputs, context=context
        )

        # if run_task returns None, then the state should not be changed
        if not final_state:
            return checked_state

        return final_state
