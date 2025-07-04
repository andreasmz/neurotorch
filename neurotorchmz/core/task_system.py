import itertools
import threading
import time
from enum import Enum
from typing import Callable, Self, Any, Dict

from .logs import logger

class TaskState(Enum):
    
    # Sorted by significance
    CREATED = 0
    """ The task has been created and is awaiting to be started """
    RUNNING = 10
    """ The task is currently running """
    STANDBY = 20
    """ The task has ended but is staying in standby such that no new task needs to be created when calling start() again. Useful in async mode as it keeps the thread alive """
    FINISHED = 25
    """ The task has finished. If the keep_alive parameter is set, this state will never be reached """
    ERROR = 30
    """ The task failed """

class TaskError(Exception):
    pass

class Task:
    """
        A class, which allows to efficiently handle work in the background by running them in a thread. Please note: Due to the Python Interpreter Lock, the function will
        still be running effectively on one core
    """
    _id_count = itertools.count() # Count the created tasks for unique naming
    _tasks: list["Task"] = [] # List of running and recently finished tasks. Garbage collected when accessing this list

    def __init__(self, function:Callable[..., None], name:str, run_async:bool=True, keep_alive:bool=False, background: bool = False):
        """
            Creating a new task in either a new thread (sync == False) or in a synchronous manner

            :param Callable[[Self, ...], None] function: When running start, this function will be called. 
            The function must accept as first parameter a Task and may accept arbitary arguments passed when calling task.start()
            :param str|None name: The name of the task
            :param bool run_async: If set to true, the task will run in a new thread
            :param bool background: Marks the task as a background task
            :raise ValueError: keep alive and not run_async is not supported
        """
        if keep_alive and not run_async:
            raise ValueError("Can't keep a synchronous thread alive")

        self.thread: threading.Thread|None = None # Either None (not started or in sync mode) or a thread (async mode)
        self._standby_cv = threading.Condition()
        self.reset(function=function, name=name, run_async=run_async, keep_alive=keep_alive, background=background)
        Task._tasks.append(self)

    def reset(self, function:Callable[..., None], name:str, run_async:bool=True, keep_alive:bool=False, background: bool = False):
        """ Reinitalize the task object as it would have been newly created but keeps the resources like the thread for example """
        if keep_alive and not run_async:
            raise ValueError("Can't keep a synchronous thread alive")

        self.func = function # The function of the task
        self.name = name
        self.run_async = run_async
        self.background = background
        self.keep_alive = keep_alive
        self.error: Exception|None = None
        self.tstart: float|None = None
        self.tend: float|None = None
        self.callbacks: list[Callable[[], None]] = []
        self.error_callback: Callable[[Exception], None] | None = None

        self._result: None # Return value of the finished func() call
        self._progress: float|None = None
        self._progress_str: str|None = None
        self._step_count: int|None = None
        self._step: int|None = None

    # Static functions

    @staticmethod
    def get_tasks() -> list["Task"]:
        """ Get a list of all tasks ever created """
        return Task._tasks

    @staticmethod
    def get_active_tasks() -> list["Task"]:
        """ Get a list of all currently running tasks """
        return [t for t in Task._tasks if (t.state == TaskState.RUNNING)]
    
    @staticmethod
    def get_recently_ended_tasks() -> list["Task"]:
        """ Get a list of task which ended either successfully or with an error not more then 5 seconds ago """
        return [t for t in Task._tasks if (t.state == TaskState.FINISHED or t.state == TaskState.STANDBY) and t.time_since_end is not None and t.time_since_end <= 5]
    
    @staticmethod
    def get_recently_failed_tasks() -> list["Task"]:
        return [t for t in Task._tasks if t.state == TaskState.ERROR and t.time_since_end is not None and t.time_since_end <= 5]

    @staticmethod
    def gc_task_list() -> None:
        """ The task class stores all created tasks. Calling this function will garbage collect this list and remove inactive tasks """
        Task._tasks = [t for t in Task._tasks if not t.inactive]

    # Runtime related functions

    @property
    def state(self) -> TaskState:
        """ Returns the current state of the Task """

        # First catch created and running using the runtime, as they are always set no matter if an error happened or not
        if self.tstart is None:
            return TaskState.CREATED
        elif self.tend is None:
            return TaskState.RUNNING
        # Now we now the task finished in some way, as tstart and tend are set

        # Sync mode
        if self.thread is None:
            if self.error is not None:
                return TaskState.ERROR
            return TaskState.FINISHED
        
        # Async mode
        if self.error:
            return TaskState.ERROR
        if self.thread.is_alive(): # is_alive is only true after thread.run()
            return TaskState.STANDBY
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
        return (time.perf_counter() - self.tstart) if self.tstart is not None else None
    
    @property
    def time_since_end(self) -> float|None:
        """ The seconds since the task ended or None if not ended yet """
        return (time.perf_counter() - self.tend) if self.tend is not None else None
    
    @property
    def finished(self) -> bool:
        """ Returns true if the task finished (successfully or with an error)"""
        return (self.tend is not None)
    
    @property
    def inactive(self) -> bool:
        """ Returns true if the task finished more then 5 seconds ago """
        if self.time_since_end is None:
            return False
        return (self.time_since_end <= 5)
    
    @property
    def running(self) -> bool:
        """ Returns true if the task is currently running """
        return (self.state == TaskState.RUNNING)
    
    # Progress related functions 

    @property
    def progress(self) -> float|None:
        """ The progress of the task as a float between 0 and 1. Set to None if the task hasn't been started or the task is indeterminate """
        return self._progress
    
    def set_percentage_mode(self) -> Self:
        """ Report progress in percent (default) """
        self._step_count = None
        return self

    def set_indeterminate(self) -> Self:
        """ Marks the task as indeterminate; task.progress will now always return None """
        self._step_count = 0
        return self
    
    def set_message(self, description: str|None = None) -> Self:
        """ Set the given text as short info message about the current state """
        self._progress_str = str(description)
        return self

    def set_step_mode(self, step_count: int) -> Self:
        """ 
            Calling this function will report a progress in form of steps instead of percentage. Can also be used to update the step count

            :param int step_count:
            :raises ValueError: step_count is not an positve integer
            :raises ValueError: step_count is higher then the current step
        """
        if not isinstance(step_count, int) or not step_count >= 1:
            raise ValueError("step_count must be a positive integer")
        if self._step is not None and self._step > step_count:
            raise ValueError("step_count must not be higher then the current step")
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
        elif self._step_count is not None and self._step_count != 0:
            raise RuntimeError("Can't set progress when not in percent mode")
        self._progress_str = str(description)
        self._progress = val
        return self

    def set_step_progress(self, step: int, description: str|None = None) -> Self:
        """ 
            When in step mode, set the current progress. Steps are counted from zero. Use the description parameter to supply a short message for the current step 
            
            :raises RuntimeError: trying to set a step progress when not in step_mode
            :raises ValueError: step is not a non negative integer
            :raises ValueError: step is greater than step_count
        """
        if self._step_count is None or self._step_count == 0:
            raise RuntimeError("Trying to set a step progress when not in step mode")
        elif not isinstance(step, int) or not step >= 0:
            raise ValueError("step must be a positive integer or zero")
        elif step > self._step_count:
            raise ValueError("step must not be greater than step_count")
        self._step = step
        self._progress_str = str(description)
        self._progress = self._step / self._step_count
        return self
    
    def reset_progress(self) -> Self:
        """ Reset the current progress to zero """
        if self._step_count is None:
            self.set_progress(0)
        elif self._step_count == 0:
            self.set_progress(0)
        else:
            self.set_step_progress(0)
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
        return (self._step_count != 0)
    
    def reinitalize(self) -> Self:
        """ Reset all properties of this task"""
        raise NotImplementedError()

    # Callback related functions

    def add_callback(self, callback: Callable[[], None]) -> Self:
        """ Add a callback for this task. Can be called even after the task finished """
        self.callbacks.append(callback)
        if self.finished and self.error is None:
            callback()
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
        """ Run the task. Any arguments given are passed to the function. If the task is already running, do nothing. Otherwise start a new one or wake it up from standby """
        if self.run_async:
            if self.thread is not None and self.thread.is_alive():
                with self._standby_cv:
                    self._standby_cv.notify_all()
            else:
                realname = f"Task {self.name} - {next(Task._id_count)}"
                self.thread = threading.Thread(target=self._task_wrapper, kwargs=kwargs, name=realname, daemon=True)
                self.thread.start()
        else:
            self._task_wrapper(**kwargs)
        return self

    def _task_wrapper(self, **kwargs):
        """ 
            Internal wrapper function for the task function to catch errors, measure time and fire the callback 
            
            :meta private:
        """
        while True:
            self.reset_progress()
            self.tstart, self.tend, self._result, self.error = time.perf_counter(), None, None, None
            try:
                self._result = self.func(self, **kwargs)
            except Exception as ex:
                self.tend = time.perf_counter()
                self.error = ex
                if self.error_callback is not None:
                    self.error_callback(ex)
                else:
                    raise ex
            else:
                self.tend = time.perf_counter()
                self.set_finished()
                if self.error is not None and self.error_callback is not None:
                    self.error_callback(self.error)
                elif len(self.callbacks) >= 1:
                    for c in self.callbacks:
                        c()
            
            if not self.keep_alive:
                break

            
            with self._standby_cv:
                self._standby_cv.wait()
    
    # Format functions

    def __str__(self) -> str:
        s = self.name if self.name is not None else 'unkown background task'
        match self.state:
            case TaskState.CREATED:
                return s
            case TaskState.ERROR:
                return f"{s}: failed after {self.runtime:.2f}s"
            case TaskState.FINISHED|TaskState.STANDBY:
                return f"{s}: finished after {self.runtime:.2f}s"
            case _:
                pass
        if self._step_count is None:
            s += f"{': ' + self._progress_str if self._progress_str is not None else ''} {(str(int(round(self._progress*100,0))) + "%") if self._progress is not None else ''}"
        elif self._step_count == 0: # indeterminated mode
            s += f"{': ' + self._progress_str if self._progress_str is not None else ''}"
        elif self._step is None:
            s += ": preparing"
        elif self._step == self._step_count:
            s += ": finishing"
        else:
            s += f":{' ' + self._progress_str if self._progress_str is not None else ''} (step {self._step+1}/{self._step_count})"
        s += f" for {self.time_since_start:.2f}s" if self.time_since_start is not None else ''

        return s

    def __repr__(self):
        return "<Task " + str(self) + (" (standby)" if self.state == TaskState.STANDBY else '') + ">"