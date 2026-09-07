# Understanding the CSE Programming Patterns in Gantry Data Collector

> [!NOTE]
> This guide is written specifically for you — an electrical engineer — to understand **why** a computer science graduate writes code this way. Each pattern has a **rational reason** behind it, often related to **safety, maintainability, and preventing bugs**.

Think of it this way: just as you follow wiring standards (color codes, terminal markings, earthing practices) not because the circuit won't work without them, but because they **prevent dangerous mistakes** — CSE patterns serve the same purpose in software.

---

## 0. Why Write Code in `__init__.py` Instead of `configs.py`?

### The Project Structure

```
src/gantry_data_collector/
├── Configs/
│   └── __init__.py          ← all config code lives here
├── Connector/
│   └── __init__.py          ← all connector code lives here
├── Controller/
│   └── __init__.py          ← all controller code lives here
├── Models/
│   └── __init__.py          ← all model code lives here
└── Helpers/
    └── __init__.py
```

### The Reason

In Python, a folder becomes a **package** (a module you can import) only if it contains an `__init__.py` file. When code is written directly inside `__init__.py`, it allows **clean imports** like this:

```python
# Because code is in __init__.py:
from gantry_data_collector.Configs import Axis, LoopState, MotorState

# If the code was in configs.py instead, you'd have to write:
from gantry_data_collector.Configs.configs import Axis, LoopState, MotorState
```

The first form is **shorter, cleaner, and more readable**. It's a conscious choice when a package is small (one file's worth of code). The folder structure gives you room to add more files later if needed, while keeping imports clean now.

### Electrical Analogy
Think of it like labeling a junction box. If you put the terminal strip right at the entry point (the `__init__.py`), anyone who opens the box sees everything immediately. If you put it in a sub-panel (`configs.py`) inside the junction box, they have to open another cover.

---

## 1. Why Create Classes? Why Enums and IntEnum?

### File: [Configs/\_\_init\_\_.py](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Configs/__init__.py)

### Without Enums (the "just use numbers" approach):

```python
# You COULD just write:
axis = 0          # Which axis? 0 means... AXIS_0? 
motor_state = 1   # Is 1 running or stopped? Who remembers?
loop_state = 0    # Is 0 open loop or closed loop?
```

**Problems:**
- What does `0` mean? You have to remember every time.
- Nothing stops you from writing `motor_state = 42` — a completely invalid value.
- If another person reads `if motor_state == 1:`, they have no idea what `1` means.

### With Enums (the CSE approach):

```python
class MotorState(IntEnum):
    RUNNING = 1
    STOPPED = 0

class LoopState(IntEnum):
    OPEN_LOOP = 1
    CLOSED_LOOP = 0
```

Now the code reads like English:

```python
if motor_state == MotorState.RUNNING:    # Crystal clear!
    print("Motor is running")
```

### Why `IntEnum` instead of `Enum`?

`IntEnum` means the enum values ARE integers — they can be compared directly with integer values coming from the hardware controller. The ACS SDK returns `1` or `0` from the controller, and `MotorState(1)` gives you `MotorState.RUNNING`. This bridges the gap between **human-readable names** and **raw hardware values**.

`Enum` (used for `Axis`) means the values are NOT plain integers — they're `sp.Axis.ACSC_AXIS_0` objects from the SDK. `Enum` prevents accidental math on them (you shouldn't do `axis + 1`).

### Electrical Analogy
An Enum is like a **selector switch with labeled positions** (OFF / FWD / REV) instead of using a variable resistor that can be set to any arbitrary value. It constrains the value to only valid options.

---

## 2. NewType, Singleton, and Special Methods (`__new__`, `__enter__`, `__exit__`, `__del__`)

### File: [Connector/\_\_init\_\_.py](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Connector/__init__.py)

### What is `NewType`?

```python
ConnectionHandle = NewType("ConnectionHandle", int)
ConnectionDescriptor = NewType("ConnectionDescriptor", int)
```

Both of these are just integers at runtime — the program runs **exactly the same** without them. So why bother?

**The purpose is documentation and safety for the programmer.** The ACS SDK returns two different integers:
- One is a **connection handle** (used to send commands)
- One is a **connection descriptor** (used to terminate the connection)

If you accidentally swap them, the hardware could malfunction. `NewType` creates a **named alias** so that:

```python
def connect(self) -> ConnectionHandle:        # Returns a HANDLE
def disconnect(self, desc: ConnectionDescriptor):  # Takes a DESCRIPTOR
```

Anyone reading the code instantly knows which integer goes where. It's like labeling wires — the copper doesn't care about the label, but the electrician does.

### What is a Singleton? (`__new__`)

```python
def __new__(cls, *args, **kwargs):
    if cls._instance is None:
        cls._instance = super().__new__(cls)
    return cls._instance
```

**The problem:** You have ONE physical gantry controller connected via ONE Ethernet cable. If your program accidentally creates two `Connector` objects, you might open two TCP connections to the same controller, causing conflicts.

**The solution:** The Singleton pattern guarantees that no matter how many times you write `Connector(...)`, you always get **the same single object** back.

```python
c1 = Connector("192.168.1.1", logger)
c2 = Connector("192.168.1.1", logger)
print(c1 is c2)  # True — they are the SAME object!
```

#### How `__new__` works

In Python, creating an object happens in two steps:
1. `__new__` — **allocates memory** for the object (like buying the hardware)
2. `__init__` — **configures** the object (like wiring it up)

By overriding `__new__`, the Singleton says: "Don't allocate new memory — return the object we already made."

### Electrical Analogy
A Singleton is like an **interlocking relay**: it prevents a second contactor from engaging when one is already energized. Only one connection can exist.

### `__enter__` and `__exit__` — The Context Manager

```python
def __enter__(self):
    self.connect()
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    self.disconnect()
    return False
```

These enable the `with` statement:

```python
with Connector("192.168.1.1", logger) as conn:
    # connection is OPEN here
    do_stuff(conn)
# connection is AUTOMATICALLY CLOSED here, even if an error occurred
```

**Why?** Without this, if your code crashes between `connect()` and `disconnect()`, the connection stays open forever — like leaving a circuit breaker on after a fault.

**The `with` statement guarantees cleanup**, just like a safety interlock that trips the breaker automatically.

| Parameter     | Meaning |
|---------------|---------|
| `exc_type`    | The type of exception (e.g., `ConnectionError`), or `None` if no error |
| `exc_val`     | The actual error message |
| `exc_tb`      | The traceback (where in the code the error happened) |
| Return `False`| Means "don't suppress the error" — let it propagate |

### `__del__` — The Destructor

```python
def __del__(self):
    if getattr(self, "connection_desc", None) is not None:
        self.disconnect()
```

This is the **last-resort safety net**. If the programmer forgets to use `with` or call `disconnect()`, Python calls `__del__` when the object is garbage-collected (destroyed). It's like an **automatic fire suppression system** — hopefully never needed, but there just in case.

---

## 3. Everything in the Controller

### File: [Controller/\_\_init\_\_.py](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Controller/__init__.py)

### What is `T = TypeVar("T")`?

```python
T = TypeVar("T")
```

`T` is a **placeholder for any type**. It's used in the method [`_read_variables`](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Controller/__init__.py#L239-L277):

```python
def _read_variables(self, names: list[str], model_cls: type[T]) -> T:
```

This says: "Whatever type you pass in as `model_cls`, I'll return an instance **of that same type**."

```python
# Pass in TuningConstants class → get a TuningConstants object back
result = self._read_variables(TUNING_CONSTANT_NAMES, TuningConstants)
# result is of type TuningConstants

# Pass in ContinousVariables class → get a ContinousVariables object back
result = self._read_variables(CONTINUOUS_VARIABLE_NAMES, ContinousVariables)
# result is of type ContinousVariables
```

Without `T`, the return type would just be `object` or `Any`, and your IDE couldn't help you with autocomplete or error-checking.

### Electrical Analogy
`T` is like a **universal connector standard**. It says "this socket accepts any plug shape, and the outlet on the other side will match." The shape isn't fixed — it adapts to what you plug in.

---

### What is `@wraps(method)` and decorators (`@`)?

The `@` symbol in Python is called a **decorator**. It's a way to **wrap a function with extra behavior** without modifying the original function.

Think of it like adding a **protective relay around a circuit** — the original circuit works the same, but the relay adds safety checks before and after.

#### The `motion_lock` decorator explained step by step:

```python
def motion_lock(method: Callable) -> Callable:
    @wraps(method)
    def wrapper(self: "AxisController", *args, **kwargs):
        with self._motion_lock:                    # 1. ACQUIRE the lock
            return method(self, *args, **kwargs)   # 2. RUN the original method
        # 3. RELEASE the lock (automatic with 'with')
    return wrapper
```

**What this does:** Before any motion command runs, it acquires a **lock** (like a mutex). While one motion is in progress, any other thread trying to start a motion on the same axis will **wait** until the first one finishes.

**Why?** Imagine two parts of your program both try to move Axis 0 at the same time — one says "go to position 100" and another says "go to position 200". Without the lock, these commands would collide and the motor behavior would be unpredictable.

**Usage — the `@` syntax:**

```python
@motion_lock
@require_closed_loop
def absolute_move(self, position: float, timeout_ms: int = 10000) -> None:
    # This is the original function
```

This is equivalent to:
```python
def absolute_move(self, position, timeout_ms=10000):
    ...
absolute_move = require_closed_loop(absolute_move)
absolute_move = motion_lock(absolute_move)
```

So `absolute_move` is now **wrapped** with two safety layers:
1. First, `motion_lock` acquires the lock
2. Then, `require_closed_loop` checks the motor is in closed loop
3. Finally, the actual move command runs

**`@wraps(method)`** preserves the original function's name and docstring. Without it, `absolute_move.__name__` would return `"wrapper"` instead of `"absolute_move"`, which confuses debugging tools.

### Electrical Analogy
A decorator is like adding a **relay protection scheme** in front of a contactor:

```
[Motion Lock Relay] → [Closed-Loop Check Relay] → [Motor Contactor]
```

The contactor (original function) only energizes if all upstream relays allow it.

---

### `TUNING_CONSTANT_NAMES` vs `CONTINUOUS_VARIABLE_NAMES`

```python
TUNING_CONSTANT_NAMES = ["VEL", "ACC", "DEC", "JERK", "SLIKP", ...]  # 15 items
CONTINUOUS_VARIABLE_NAMES = ["PE", "FPOS", "FVEL", "FACC"]             # 4 items
```

**Why are they separated?** Because they represent fundamentally different kinds of data from the servo controller:

| Category | Tuning Constants | Continuous Variables |
|----------|-----------------|---------------------|
| **Nature** | Configuration parameters | Real-time sensor readings |
| **Change rate** | Set once, rarely change | Change every control loop cycle |
| **Examples** | Max velocity, PID gains, jerk | Position error, actual position, actual velocity |
| **When to read** | At startup or after tuning | Continuously during data collection |
| **Analogy** | The **settings on a VFD** (accel time, decel time, gains) | The **readings on a power meter** (V, I, PF) |

The CSE graduate separated them because they are **read at different times, for different purposes**, and are stored in different Pydantic models ([`TuningConstants`](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Models/__init__.py#L4-L44) and [`ContinousVariables`](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Models/__init__.py#L47-L55)). This makes the code **self-documenting** — anyone reading it immediately understands the difference.

---

### Abstract Base Class (`ABC`) and `@abstractmethod`

```python
class AxisComponent(ABC):
    @abstractmethod
    def enable(self): ...

    @abstractmethod
    def disable(self): ...

    @abstractmethod
    def motor_state(self): ...

    @abstractmethod
    def read_tuning_constants(self): ...

    @abstractmethod
    def read_continuous_variables(self): ...
```

**What is this?** An **Abstract Base Class** (ABC) is a **blueprint/contract**. It says: "Any class that wants to be an `AxisComponent` MUST implement these 5 methods."

**Why?** Because there are TWO kinds of axis components in this project:
1. [`AxisController`](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Controller/__init__.py#L101) — controls a **single axis**
2. [`AxisGroup`](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Controller/__init__.py#L286) — controls a **group of axes**

Both must support `enable()`, `disable()`, `motor_state()`, etc. The ABC guarantees this. If you create a new class inheriting from `AxisComponent` but forget to implement `enable()`, Python will **raise an error immediately** — not at runtime when the motor is moving.

The `...` (ellipsis) after each method means "no implementation here" — subclasses must provide it.

### Electrical Analogy
An ABC is like the **IEC standard for motor starters**: it defines that every starter must have START, STOP, and STATUS functions. The actual implementation can be a DOL starter, a star-delta starter, or a VFD — but they all must have those functions.

---

### Class Attributes vs Instance Attributes

```python
class AxisController(AxisComponent):
    enabled: bool                                    # ← Type annotation (documentation)
    _loop_state: LoopState = LoopState.CLOSED_LOOP   # ← Class-level default
```

These two lines serve different purposes:

| Line | Purpose |
|------|---------|
| `enabled: bool` | **Type hint only** — tells the reader and IDE "this object will have a `bool` attribute called `enabled`". Doesn't set any value. |
| `_loop_state: LoopState = LoopState.CLOSED_LOOP` | **Default value** — if no one explicitly sets `_loop_state`, it defaults to `CLOSED_LOOP`. The `_` prefix means "private — don't access from outside the class." |

The actual values are set in `__init__`:
```python
def __init__(self, connection, axis, logger=logger):
    self.enabled = False                          # ← Sets the actual value
    self.loop_state = LoopState.CLOSED_LOOP       # ← Uses the setter (see below)
```

---

### `@property` and `@loop_state.setter`

```python
@property
def loop_state(self) -> LoopState:
    # Reads the actual hardware state
    buf = f"?MFLAGS({self.axis.value}).#OPEN\r"
    result = sp.Transaction(...)
    return LoopState.OPEN_LOOP if int(result) == 1 else LoopState.CLOSED_LOOP

@loop_state.setter
def loop_state(self, loop_state: LoopState) -> None:
    # Writes to the hardware
    bit_value = 1 if loop_state == LoopState.OPEN_LOOP else 0
    buf = f"MFLAGS({self.axis.value}).#OPEN={bit_value}\r"
    sp.Command(...)
```

**What is `@property`?** It makes a method **look like a simple variable** when you access it:

```python
# Without @property — calling a method:
state = controller.get_loop_state()

# With @property — looks like reading a variable, but actually runs code:
state = controller.loop_state       # ← Calls the @property method
controller.loop_state = LoopState.OPEN_LOOP  # ← Calls the @setter method
```

**Why?** Because reading the loop state isn't just returning a stored value — it actually **queries the hardware** via an ACS Transaction. The `@property` decorator hides this complexity. The user of the class doesn't need to know that a hardware query happens — they just read `.loop_state` and get the answer.

The `@setter` is the counterpart: when you assign to `.loop_state`, it actually **sends a command to the hardware** to change the loop state.

### Electrical Analogy
A `@property` is like a **smart sensor with a register interface**. When you "read register 40001" on a Modbus device, it looks like reading a memory location, but internally the sensor takes a measurement, processes it, and returns the value.

---

### Return Type Annotations: `-> TuningConstants:`

```python
def read_tuning_constants(self) -> TuningConstants:
```

The `-> TuningConstants` tells you: "This function **returns a `TuningConstants` object**."

It's pure documentation — Python doesn't enforce it at runtime. But it enables:
1. **IDE autocomplete** — after calling this method, your IDE knows the result has `.VEL`, `.ACC`, `.JERK` etc.
2. **Static type checking** — tools like `mypy` can catch bugs before you run the code
3. **Self-documenting code** — you instantly know what the function produces

Without it: `def read_tuning_constants(self):` — what does this return? A dict? A list? A number? You'd have to read the implementation.

---

### `__init__` in `AxisGroup`

```python
class AxisGroup(AxisComponent):
    def __init__(self, members: list[AxisComponent]):
        self.members = members
```

`__init__` is the **constructor** — it runs when you create a new object. This one says: "To create an `AxisGroup`, give me a list of `AxisComponent` objects."

```python
group = AxisGroup([axis0_controller, axis1_controller, axis2_controller])
```

Now `group.members` holds all three controllers. When you call `group.enable()`, it loops through all members and enables each one:

```python
def enable(self) -> None:
    for member in self.members:
        member.enable()
```

The clever part: `members` is typed as `list[AxisComponent]` — not `list[AxisController]`. This means a group can contain other groups! (This is the **Composite pattern**.)

```python
# An AxisGroup can contain individual axes OR other groups:
sub_group = AxisGroup([axis0, axis1])
main_group = AxisGroup([sub_group, axis2])  # ← Groups within groups!
main_group.enable()  # Enables ALL axes recursively
```

### Electrical Analogy
This is like a **main breaker panel** containing **sub-panels**: flipping the main breaker disables everything, or you can flip individual sub-breakers.

---

## Summary: The CSE Mindset

| CSE Pattern | Purpose | Electrical Analogy |
|-------------|---------|-------------------|
| `__init__.py` code | Clean imports | Terminal strip at junction box entry |
| `Enum` / `IntEnum` | Constrain values to valid options | Selector switch with labeled positions |
| `NewType` | Label types for documentation | Wire labeling |
| Singleton (`__new__`) | Only one instance allowed | Interlocking relay |
| `__enter__`/`__exit__` | Guaranteed cleanup | Automatic circuit breaker |
| `__del__` | Last-resort cleanup | Fire suppression system |
| `TypeVar("T")` | Generic type placeholder | Universal connector |
| `@decorator` | Wrap function with extra behavior | Protection relay in front of contactor |
| `@wraps` | Preserve wrapped function's identity | Relay nameplate passthrough |
| `ABC` + `@abstractmethod` | Enforce a contract/blueprint | IEC standard for motor starters |
| `@property` / `@setter` | Method that looks like a variable | Smart sensor register interface |
| `-> ReturnType` | Document what function returns | Terminal block label |
| Constants lists | Separate data by nature | VFD settings vs. power meter readings |
| Composite (`AxisGroup`) | Tree of components | Main breaker → sub-panels |

---

## Recommended Study Path

Based on the questions you asked, here is a structured learning path. Start from the top and work your way down:

### Phase 1: Python Fundamentals (1-2 weeks)
- **Course:** [Python for Everybody](https://www.py4e.com/) by Dr. Chuck (University of Michigan) — free
- Focus on: classes, objects, `__init__`, inheritance, `self`

### Phase 2: Intermediate Python (2-3 weeks)
- **Course:** [Real Python — Object-Oriented Programming](https://realpython.com/python3-object-oriented-programming/)
- Topics to study:
  - Classes and `__init__`
  - Inheritance and method overriding
  - `@property` and setters
  - `with` statement (context managers: `__enter__`/`__exit__`)
  - Decorators (`@` syntax)
  - Enums

### Phase 3: Python Type Hints (1 week)
- **Resource:** [mypy documentation — Type hints cheat sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
- Topics: `NewType`, `TypeVar`, `-> ReturnType`, `list[str]`, `Optional`

### Phase 4: Design Patterns (2-3 weeks)
- **Book:** *Head First Design Patterns* (easy to follow, visual)
- **Free alternative:** [Refactoring Guru — Design Patterns](https://refactoring.guru/design-patterns)
- Focus on: **Singleton**, **Composite**, **Facade**, **Template Method** (all used in this project)

### Phase 5: Python-Specific Patterns (1-2 weeks)
- **Resource:** [Real Python — Design Patterns in Python](https://realpython.com/tutorials/best-practices/)
- Topics:
  - Abstract Base Classes (ABC)
  - Decorators (advanced)
  - Context Managers
  - Threading and Locks

### Quick Reference Topics List

| Topic | Where It Appears in This Project |
|-------|--------------------------------|
| Classes and `__init__` | Every file |
| Enums | [Configs/\_\_init\_\_.py](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Configs/__init__.py) |
| `NewType` and type hints | [Connector/\_\_init\_\_.py](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Connector/__init__.py) |
| Singleton pattern | [Connector/\_\_init\_\_.py](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Connector/__init__.py) |
| Context managers (`with`) | [Connector/\_\_init\_\_.py](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Connector/__init__.py) |
| Decorators (`@`) | [Controller/\_\_init\_\_.py](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Controller/__init__.py) |
| ABC and `@abstractmethod` | [Controller/\_\_init\_\_.py](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Controller/__init__.py) |
| `@property` and `@setter` | [Controller/\_\_init\_\_.py](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Controller/__init__.py) |
| `TypeVar` and generics | [Controller/\_\_init\_\_.py](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Controller/__init__.py) |
| Pydantic models | [Models/\_\_init\_\_.py](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Models/__init__.py) |
| Threading (Lock) | [Controller/\_\_init\_\_.py](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Controller/__init__.py) |
| Composite pattern | [AxisGroup](file:///Users/malithjkd1/Documents/PdM_PBA/pbasystems/gantry-data-collector/src/gantry_data_collector/Controller/__init__.py#L286-L319) |

> [!TIP]
> You don't need to learn everything at once. Start with **Phase 1 and 2** — that covers 80% of what you see in this project. The rest (Type Hints, Design Patterns) are refinements that make code more professional and less error-prone.
