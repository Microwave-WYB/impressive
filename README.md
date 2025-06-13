# Impressive

A Python DSL for functional programming patterns, exception handling, and control flow.

**Impressive** = **Imperative** + **Expressive** - Working with imperative APIs using expressions.

## Installation

```bash
pip install impressive
```

## Overview

Python lacks many expressions that other languages have. Error raising and handling must be done with statements, match is only available as statements, and many control flow constructs require multi-line code blocks. This makes it difficult to write concise, expression-based code, especially when working with imperative frameworks like GTK or Qt.

Impressive provides an expression-focused DSL that brings functional programming patterns to Python. It includes tools for exception handling, side effects, conditional logic, and function application - all as expressions that can be used inline, making it easy to work with callback-heavy imperative frameworks.

## Features

### Exception Handling

Handle exceptions functionally with `attempt` and `catcher`:

```python
from impressive import attempt

# Basic exception handling
result = attempt(lambda: 1 / 0).catch(ZeroDivisionError).fallback(-1).unwrap()
# Returns: -1

# Exception recovery with custom handler
result = attempt(lambda: int("abc")).catch(ValueError).recover(
    ValueError, lambda e: 0
).unwrap()
# Returns: 0

# Cleanup operations
attempt(lambda: risky_operation()).catch(Exception).cleanup(
    lambda: print("Cleanup executed")
).fallback("failed").unwrap()
```

### Side Effects

Execute side effects while returning values using `tap`:

```python
from impressive import tap

# Instead of: (print(event), process(event))[-1]
result = lambda event: tap(print(event), ret=process(event))

# Multiple side effects
value = tap(
    print("Processing..."),
    log.info("Started processing"),
    ret=compute_result()
)

# Register GUI callbacks
button.connect("clicked", lambda *_: tap(
    print("Button clicked"),
    update_status("processing"),
    handle_click()
))
```

### Function Application

Apply functions to values with `apply`:

```python
from impressive import apply

# Apply function to a factory result
items = []
result = apply(items.append)(lambda: 42)  # Appends 42 to items

# Apply to multiple items
apply(print).foreach(lambda: [1, 2, 3])  # Prints each number

# Unpack arguments
apply.unpack_to(print)(lambda: (1, 2, 3))  # Prints: 1 2 3
```

### Conditional Logic

Pattern matching with `switch` and `case`:

```python
from impressive import switch, case

# Exhaustive matching - all cases must be handled
number = 2
result = switch(number)[
    case(number < 0) >> (lambda: "Negative"),
    case(number == 0) >> (lambda: "Zero"),
    case(number > 0) >> (lambda: "Positive"),
]
# Returns: "Positive"

# With default value fallback
number = -1
result = switch(number)(
    case(number == 0) >> (lambda: "Zero"),
    case(number > 0) >> (lambda: "Positive"),
    default="Negative",
)
# Returns: "Negative"

# With default factory for computed defaults
result = switch(number)(
    case(number == 0) >> (lambda: "Zero"),
    case(number > 0) >> (lambda: "Positive"),
    default_factory=(lambda: "Negative"),
)
# Returns: "Negative"
```

## API Reference

### `attempt(fn)`

Creates an attempt instance for exception handling.

**Methods:**
- `.catch(*exceptions)` - Catch specific exceptions
- `.map(fn)` - Transform the result
- `.unwrap()` - Execute and get result

### `catcher(fn, *exceptions)`

Exception handler with recovery options.

**Methods:**
- `.fallback(value)` - Return default value on exception
- `.recover(exc_type, handler)` - Handle specific exception with function
- `.cleanup(fn)` - Execute cleanup code regardless of success/failure
- `.unwrap()` - Execute and get result

### `tap(*side_effects, ret=value)`

Execute side effects and return a value.

### `apply(fn)`

Apply a function to a factory result.

**Methods:**
- `.foreach(factory)` - Apply to each item in iterable
- `.unpack_to(fn)` - Static method to unpack arguments

### `switch(value)`

Pattern matching construct.

**Usage:**
- `switch(value)(cases..., default=value)` - With optional default
- `switch(value)[cases_tuple]` - Exhaustive matching

### `case(condition)`

Create a case for switch statements.

**Usage:**
- `case(condition) >> factory` - Creates a case

## Requirements

- Python >= 3.10
- typing-extensions >= 4.14.0

## License

MIT License