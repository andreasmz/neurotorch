from typing import Callable, Self, Any
import threading
import itertools
import time
from enum import Enum

class TaskState(Enum):
    
    # Sorted by significance
    CREATED = 0
    RUNNING = 1
    FINISHED = 2
    ERROR = 3

class TaskError(Exception):
    pass

class Task:
    """
        A class, which allows to efficiently handle work in the background by running them in a thread. Please note: Due to the Python Interpreter Lock, the function will
        still be running in a synchronous manner, but not blocking the current thread.

        :var list[Task] tasks: A list of all task created
        
    """
    _id_count = itertools.count() # Count the created tasks for unique naming
    _tasks: list[Self] = [] # List of running and recently finished tasks. Garbage collected when accessing this list

    def __init__(self, function:Callable[[Self, Any], None], name:str, run_async:bool=True):
        """
            Creating a new task in either a new thread (sync == False) or in a synchronous manner

            :param Callable[[Self, Any], None] function: When running start, this function will be called. 
            The function must accept as first parameter a Task and may accept arbitary arguments passed when calling task.start()
            :param str|None name: The name of the task
            :param bool run_async: If set to true, the task will run in a new thread
        """
        self.func: Callable[[Self, Any], None] = function # The function of the task
        self.name: str = name
        self.run_async: bool = run_async
        self.thread: threading.Thread|bool|None = None # Either a None (not started), a thread (async mode) or a boolean (sync mode; false while running, true when finished)
        self.error: Exception|bool|None = None
        self.tstart: float|None = None
        self.tend: float|None = None
        self.callback: Callable[[], None] = None
        self.error_callback: Callable[[Exception], None] = None

        self._progress: float|None = None
        self._progress_str: str|None = None
        self._step_count: int|None = None
        self._step: int|None = None

        Task.tasks.append(self)

    # Static functions

    @property
    def active_tasks() -> list[Self]:
        """ Get a list of all currently running tasks """
        return [t for t in Task._task if (t.state == TaskState.Running)]
    
    @property
    def recently_ended_tasks() -> list[Self]:
        """ Get a list of task which ended either successfully or with an error not more then 5 seconds ago """
        return [t for t in Task._task if t.time_since_end is not None and t.time_since_end <= 5]

    def gc_task_list():
        """ The task class stores all created tasks. Calling this function will garbage collect this list and remove inactive tasks"""
        Task._task = [t for t in Task._task if not t.inactive]

    # Runtime related functions

    @property
    def state(self):
        """ Returns the current state of the Task """
        if self.thread is None:
            return TaskState.CREATED
        elif self.error is not None:
            return TaskState.ERROR
        elif (type(self.thread) == bool and self.thread == False) or (isinstance(self.thread, threading.Thread) and self.thread.is_alive()):
            return TaskState.RUNNING
        else:
            return TaskState.FINISHED
        
    @property
    def runtime(self) -> float|None:
        """ Returns the runtime of the task in seconds or None if not finished yet"""
        if self.tstart is None or self.tend is None:
            return None
        return self.tend - self.tstart
    
    @property
    def time_since_start(self) -> float|None:
        """ The seconds since the task has been started or None if not started yet """
        (time.perf_counter() - self.tstart) if self.tstart is not None else None
    
    @property
    def time_since_end(self) -> float|None:
        """ The seconds since the task ended or None if not ended yet """
        return (time.perf_counter() - self.tend) if self.tend is not None else None
    
    @property
    def finished(self) -> bool:
        """ Returns true if the task finished (successfully or with an error)"""
        if type(self.thread) == bool:
            return self.thread
        if self.thread is None or self.thread.is_alive():
            return False
        return True
    
    @property
    def inactive(self) -> bool:
        """ Returns true if the task finished more then 5 seconds ago """
        if self.time_since_end is None:
            return False
        return self.time_since_end <= 5
    
    # Progress related functions 

    @property
    def progress(self) -> float|None:
        """ The progress of the task as a float between 0 and 1. Set to None if the task hasn't been started or the task is indeterminate """
        return self._progress
    
    def set_percentage_mode(self) -> Self:
        """ Report progress in percent (default) """
        self._step_count = None

    def set_indeterminate(self) -> Self:
        """ Marks the task as indeterminate. task.progress will now always return None """
        self._step_count == 0
        return self

    def set_step_mode(self, step_count: int) -> Self:
        """ 
            Calling this function will report a progress in form of steps instead of percentage. Can also be used to update the step count

            :param int step_count:
            :raises ValueError: step_count is not an positve integer
        """
        if not isinstance(step_count, int) or not step_count >= 1:
            raise ValueError("step_count must be a positive integer")
        self._step_count = step_count    
        return self

    def set_progress(self, val: float, description: str|None = None) -> Self:
        """ 
            Set the progress in percent. Use the description parameter to supply a short message for the current state.
            Can only be called when in percent mode

            :raises ValueError: the value is not a float between 0 and 1
            :raises RuntimeError: trying to set a progress value on an step task or in indeterminate mode
        """
        if val < 0 or val > 1:
            raise ValueError("The progress must be a float between 0 and 1")
        if self._step_count is not None:
            raise RuntimeError("Can't set progress when not in percent mode")
        self._progress_str = description
        self._progress = val
        return self

    def set_step_progress(self, step: int, description: str|None = None) -> Self:
        """ 
            When in step mode, set the current progress. Steps are counted from zero. Use the description parameter to supply a short message for the current step 
            
            :raises RuntimeError: trying to set a step progress when not in step_mode
            :raises ValueError: the step_count is not a non negative integer
        """
        if self._step_count is None or self._step_count == 0:
            raise RuntimeError("Trying to set a step progress when not in step mode")
        if not isinstance(step, int) or not step >= 0:
            raise ValueError("step_count must be a positive integer or zero")
        self._step = step
        self._progress_str = description
        self._progress = self._step / self._step_count
        return self
    
    def set_finished(self) -> Self:
        """ Set the percentage to 100% or the step to step count """
        if self._step_count is None:
            self.set_progress(1)
        elif self._step_count == 0:
            self.set_percentage_mode()
            self.set_progress(1)
        else:
            self.set_step_progress(self._step_count)
        return self

    def is_determinate(self) -> bool:
        """ Returns if the task is determinate or indeterminate """
        return (self._step_count == 0)

    # Callback related functions

    def set_callback(self, callback: Callable[[], None]) -> Self:
        """ Set a callback for this task. Can be called even after the task finished """
        self.callback = callback
        if self.finished and self.error is None:
            self.callback()
        return self
    
    def set_error_callback(self, error_callback: Callable[[Exception], None]) -> Self:
        """ 
            Provide a function which is called when an error happens in the task. The exception will be passed to the supplied function.
            Note that when setting an error callback, the exception not raised anymore by the task object. The function works even after
            a task finished.
        """
        self.error_callback = error_callback
        if self.finished and self.error is not None:
            self.error_callback(self.error)
        return self
    
    # Task execution functions

    def start(self, **kwargs) -> Self:
        """ Run the task. Any arguments given are passed to the function """
        if self.thread is not None:
            raise RuntimeError("The task has already been started")
        self._progress = 0
        self.tstart = time.perf_counter()
        if self.run_async:
            self.thread = threading.Thread(target=self._task, args=(self), kwargs=kwargs, name=f"Task {self.name} - {next(Task._id_count)}", daemon=True)
            self.thread.start()
        else:
            self.thread = False
            self._task(**kwargs)
            self.thread = True
        return self

    def _task(self):
        """ Internal wrapper function for the task function to catch errors, measure time and fire the callback"""
        try:
            self.func()
        except Exception as ex:
            self.tend = time.perf_counter()
            self.error = ex
            if self.error_callback is not None:
                self.error_callback(ex)
            else:
                raise ex
        else:
            self.set_finished()
            self.tend = time.perf_counter()
            if self.callback is not None:
                self.callback()
    
    # Format functions

    def to_string_short(self) -> str:
        s = self.name if self.name is not None else 'unkown background task'
        match self.state:
            case TaskState.CREATED:
                return s
            case TaskState.ERROR:
                s += f": Failed after {self.runtime:.3f}s"
                return s
            case TaskState.FINISHED:
                s += f": Finished in {self.runtime:3f}s"
                return s
            case _:
                pass
        if self._step_count is None:
            s += f": {int(round(self._progress*100),0)}%"
        elif self._step_count == 0:
            pass
        elif self._step is None:
            s += ": preparing"
        elif self._step == self._step_count:
            s += ": finishing"
        else:
            s += f"step {self._step+1}/{self._step_count}"

        if self._progress_str is not None:
            s += " (" + self._progress_str + ")"

        return s

    