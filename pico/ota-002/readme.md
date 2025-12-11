# Raspberry Pi Pico W - OTA Environmental Monitor

This document provides setup instructions and development guidelines for the Pico W MicroPython project.

---

## 1. Project Setup

This project uses `mpremote` to interact with the Pico W. It is highly recommended to use a Python virtual environment to manage dependencies.

1.  **Create the Virtual Environment**
    Use Python 3.12 (or your preferred Python 3 version) to create an environment named `pico_env`:
    ```bash
    python3.12 -m venv pico_env
    ```

2.  **Activate the Environment**
    On macOS/Linux:
    ```bash
    source pico_env/bin/activate
    ```
    *You will see `(pico_env)` at the beginning of your terminal prompt.*

3.  **Install Dependencies**
    Install `mpremote` into your active environment:
    ```bash
    pip install mpremote
    ```

---

## 2. Basic `mpremote` Usage

With the Pico connected via USB, you can use the following commands from your terminal. The leading colon (`:`) specifies a path on the Pico's filesystem.

*   **List files on the Pico:**
    ```bash
    mpremote ls
    ```

*   **Copy a local file to the Pico:**
    ```bash
    mpremote cp your_script.py :
    ```

*   **Remove a file from the Pico:**
    ```bash
    mpremote rm :file_to_delete.py
    ```

*   **Rename a file on the Pico:**
    ```bash
    mpremote fs mv :old_name.py :new_name.py
    ```

*   **Reset the Pico:**
    ```bash
    mpremote reset
    ```

*   **Enter the REPL:**
    ```bash
    mpremote repl
    ```

---

## 3. The `main.py` Lockout Problem

The `main.py` script runs automatically on boot. A script with an infinite loop, an unhandled error, or one that blocks execution can **lock you out** of the REPL, making it impossible to debug or upload new code.

### Best Practices to Avoid Lockout

*   **Initial Boot Delay:** Add a `time.sleep(3)` at the start of `main.py` to give you a window to interrupt it with `Ctrl+C`.

*   **Use `uasyncio` for Concurrency:** For tasks that need to run concurrently (like blinking an LED while checking a sensor), use the `uasyncio` library.
    *   **Avoid `time.sleep()`:** In an `async` function, never use `time.sleep()`. It is a "blocking" call that freezes the entire system.
    *   **Use `await uasyncio.sleep()`:** This is the non-blocking alternative. It pauses the current task and allows the scheduler to run other tasks (like listening for `Ctrl+C`), preventing a lockout.
    *   **Example:**
        ```python
        import uasyncio
        import time

        async def background_task():
            while True:
                print("Background task is running...")
                await uasyncio.sleep(5) # Non-blocking delay

        async def main():
            print("Starting tasks...")
            uasyncio.create_task(background_task())
            # The main loop can do other things or sleep
            while True:
                await uasyncio.sleep(60)

        # Run the event loop
        uasyncio.run(main())
        ```

*   **Error Handling:** Wrap your main logic in a `try...except` block to catch errors and prevent boot loops.

*   **Develop in other files:** Write and test your logic in other files (e.g., `controller.py`) and keep `main.py` as a simple entry point.

### Recovery from Lockout

If you get locked out, do the following:

1.  Connect the Pico.
2.  Immediately run one of the following commands in your terminal. This is often faster than using a GUI like Thonny.

    *   **Rename `main.py` (Safe Method):**
        ```bash
        mpremote fs mv :main.py :main.py.bak
        ```

    *   **Delete `main.py`:**
        ```bash
        mpremote rm :main.py
        ```
3.  Reset the device to apply the change:
    ```bash
    mpremote reset
    ```
4.  If all else fails, re-flash the MicroPython firmware by holding the `BOOTSEL` button while plugging in the Pico and dragging the `.uf2` file to the drive that appears. **This will erase all files on the device.**


## 2. Symptoms of Lockout

*   The REPL in the development environment (e.g., Thonny) remains unresponsive, blank, or displays only a continuous stream of the problematic script's output.
*   The `Ctrl+C` command, intended to interrupt execution, becomes ineffective.
*   The Pico W may appear to be frozen, continuously restarting, or behaving erratically without providing a usable interface.
*   Accessing the device's file system (to modify or delete `main.py`) becomes impossible or extremely difficult.

## 3. Root Cause

MicroPython's interpreter is single-threaded. If the `main.py` script aggressively uses the CPU without periodically allowing the interpreter to service other tasks (like handling serial input or managing the file system), the REPL loses its opportunity to respond. This creates a loop where the problematic `main.py` runs unimpeded, blocking any attempt to interact with it.

## 4. Impact on Development

*   **Significant Development Delays:** Recovering from a lockout can be time-consuming, often requiring disruptive steps.
*   **Increased Frustration:** The inability to easily debug or modify code severely impacts the developer experience.
*   **Hindered Debugging:** Crucial runtime inspection and error diagnosis are impossible without REPL access.
*   **Slowed Iteration Cycles:** The need for extreme caution with every `main.py` modification drastically slows down the development process.

## 5. Preventative Measures & Best Practices

To avoid lockouts and ensure a robust debugging environment, the following practices are essential for this project:

*   **Initial Boot Delay:**
    *   **Practice:** Always incorporate a short delay (e.g., 2-5 seconds) at the very beginning of `main.py` before any application logic starts.
    *   **Advantage:** This provides a critical window for a developer to connect via serial and issue a `Ctrl+C` interrupt, preventing the main application from taking over.

*   **Conditional Debug Mode:**
    *   **Practice:** Implement a check at the start of `main.py` for a specific, easily-controlled condition (e.g., the state of a physical button connected to a GPIO pin, or a specific file existing on the filesystem). If this condition is met, the script should enter a "debug mode."
    *   **Advantage:** Debug mode can bypass the main application code, keep the REPL fully accessible, and perhaps even offer a simple menu of debugging functions, allowing for safe interaction without re-flashing.

*   **Asynchronous Programming with `uasyncio`:**
    *   **Practice:** For any application involving concurrent tasks (network communication, sensor polling, UI updates), always utilize MicroPython's `uasyncio` library.
    *   **Advantage:** This ensures tasks yield control regularly, preventing any single task from monopolizing the CPU and keeping the REPL responsive, even when multiple operations are active. Blocking `while True` loops should always include an `await asyncio.sleep()`.

*   **Robust Error Handling:**
    *   **Practice:** Wrap critical sections of `main.py` with comprehensive `try...except` blocks.
    *   **Advantage:** Prevents unhandled errors from causing continuous reboots. In case of an exception, the script can print useful diagnostic information to the REPL and then enter a safe, non-blocking state (e.g., an indefinite sleep), preserving REPL access for investigation.

*   **Modular Code Structure:**
    *   **Practice:** Keep `main.py` as lean as possible. Defer most of the application's logic to separate `.py` modules that `main.py` imports and calls.
    *   **Advantage:** This simplifies `main.py`, reduces the likelihood of it containing lockout-inducing code directly, and makes individual components easier to test and debug in isolation.

## 6. Recovery Methods (if lockout occurs)

Should a lockout occur despite preventative measures, the following steps can be used to regain control:

1.  **Repeated `Ctrl+C`:** Try pressing `Ctrl+C` multiple times, rapidly, immediately after connecting to the Pico W or resetting it. This sometimes catches a brief window of opportunity.
2.  **Rename/Delete `main.py` via Thonny File Browser:** If the device momentarily connects, use Thonny's file browser (`View -> Files`) to quickly rename (e.g., to `main_OLD.py`) or delete the problematic `main.py` file. This prevents it from running on subsequent boots.
3.  **Upload a Dummy `main.py`:** Prepare a very simple, non-blocking `main.py` (e.g., an empty file or one with just a long `time.sleep()`). Rapidly upload this file to the Pico W to overwrite the problematic `main.py` before it can fully execute.
4.  **Re-flash MicroPython Firmware (Last Resort):** If all other methods fail, hold down the `BOOTSEL` button while plugging in the Pico W to your computer. This mounts it as a USB drive. Drag a fresh MicroPython `.uf2` firmware file onto this drive. This action will erase all user files, including `main.py`, restoring the device to a clean state.

---

By understanding these challenges and consistently applying these best practices, we can ensure a more efficient, less frustrating, and ultimately more productive development workflow for this Raspberry Pi Pico W project.