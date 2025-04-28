import time
import multiprocessing
import os
import signal
import sys
import random  # Add this for the random delay

# Environment variable configuration with defaults
def get_env_int(name, default):
    """Get an integer from environment variable or use default."""
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        print(f"Warning: Invalid value for {name}: '{value}'. Using default: {default}", file=sys.stderr)
        return default

def get_env_float(name, default):
    """Get a float from environment variable or use default."""
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        print(f"Warning: Invalid value for {name}: '{value}'. Using default: {default}", file=sys.stderr)
        return default

def cpu_worker():
    """Target function for CPU stress processes. Runs an infinite loop."""
    # pylint: disable=empty-docstring, missing-function-docstring
    while True:
        try:
            # Perform some CPU-intensive work (e.g., math operations)
            # Using pass creates a very tight loop, maximizing CPU usage quickly.
            pass
        except KeyboardInterrupt:
            # Allow graceful exit if Ctrl+C is pressed directly in the worker
            break

def allocate_memory_chunk(size_mb):
    """Allocates a specified amount of memory chunk and returns it."""
    print(f"Attempting to allocate a chunk of {size_mb:.2f} MB...")
    if size_mb <= 0:
        return None
    try:
        # Allocate memory as a bytearray
        chunk_bytes = int(size_mb * 1024 * 1024)
        if chunk_bytes == 0: # Avoid allocating zero bytes
             return None
        data = bytearray(chunk_bytes)
        # print(f"Successfully allocated chunk of {size_mb:.2f} MB.")
        return data # Return the allocated data to keep it in memory
    except MemoryError:
        print(f"ERROR: Failed to allocate chunk of {size_mb:.2f} MB. Insufficient memory.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during memory chunk allocation: {e}", file=sys.stderr)
        return None

def release_memory(chunk_list):
    """Releases the allocated memory chunks."""
    if chunk_list:
        print(f"Releasing {len(chunk_list)} memory chunks...")
        # Clear the list and let garbage collection handle individual chunks
        chunk_list.clear()
        # Optionally force garbage collection, though usually not needed
        # import gc
        # gc.collect()
        print("Memory chunks released.")
    else:
        print("No memory chunks allocated in the previous phase or allocation failed.")

def terminate_processes(processes):
    """Attempts to terminate a list of processes gracefully."""
    print(f"Stopping {len(processes)} CPU stress processes...")
    # Request termination
    for p in processes:
        if p.is_alive():
            try:
                # On Windows, terminate() calls TerminateProcess
                # On Unix, it sends SIGTERM
                p.terminate()
            except Exception as e:
                print(f"Warning: Could not terminate process {p.pid}: {e}", file=sys.stderr)

    # Wait for processes to terminate with a timeout
    start_time = time.time()
    cleanup_timeout = 5 # seconds
    remaining_processes = [p for p in processes if p.is_alive()]
    while remaining_processes and (time.time() - start_time) < cleanup_timeout:
        print(f"Waiting for {len(remaining_processes)} processes to terminate...")
        time.sleep(0.5)
        for p in remaining_processes:
             # Check if process exited, join removes it from system resources
             p.join(timeout=0.1)
        remaining_processes = [p for p in processes if p.is_alive()]


    # Force kill any remaining processes
    force_killed = 0
    for p in remaining_processes:
         if p.is_alive():
             try:
                 print(f"Process {p.pid} did not terminate gracefully, killing.")
                 p.kill() # Force kill (SIGKILL on Unix)
                 p.join(timeout=1) # Wait briefly after kill
                 force_killed += 1
             except Exception as e:
                 print(f"Warning: Could not kill process {p.pid}: {e}", file=sys.stderr)

    if force_killed > 0:
        print(f"Force killed {force_killed} processes.")
    print("CPU stress processes stopped.")


def run_stress_cycle(
    high_duration_sec, 
    low_duration_sec, 
    cpu_cores, 
    memory_mb, 
    steps=5, 
    low_phase_percent=0.1,
    ramp_up_duration=20.0,
    ramp_down_duration=20.0
):
    """Runs the cyclical stress test with gradual ramp-up and ramp-down.
    
    Args:
        high_duration_sec: Duration of high stress phase in seconds
        low_duration_sec: Duration of low stress phase in seconds
        cpu_cores: Maximum number of CPU cores to use
        memory_mb: Maximum memory to allocate in MB
        steps: Number of steps for ramp-up and ramp-down
        low_phase_percent: Percentage of resources to maintain during low phase (0.1 = 10%)
        ramp_up_duration: Duration of ramp up phase in seconds
        ramp_down_duration: Duration of ramp down phase in seconds
    """
    all_processes = []
    allocated_chunks = []
    original_sigint_handler = signal.getsignal(signal.SIGINT)

    # Calculate low phase resource targets
    low_phase_cores = max(1, int(cpu_cores * low_phase_percent))
    low_phase_memory_mb = memory_mb * low_phase_percent
    
    # Calculate durations for ramp-up, hold, and ramp-down
    # Ensure at least 1 second for each phase if possible, minimum step time 0.1s
    min_step_time = 0.1
    min_phase_duration = max(1.0, steps * min_step_time)

    if high_duration_sec < 3 * min_phase_duration:
        print(f"Warning: High duration ({high_duration_sec}s) is short for {steps} steps. Adjusting phase timings.", file=sys.stderr)
        # Prioritize ramp-up and ramp-down, minimize hold
        ramp_up_duration_local = max(min_phase_duration, high_duration_sec / 3)
        ramp_down_duration_local = max(min_phase_duration, high_duration_sec / 3)
        hold_duration = max(0, high_duration_sec - ramp_up_duration_local - ramp_down_duration_local)
    else:
        hold_duration = max(0, high_duration_sec - ramp_up_duration - ramp_down_duration)
        ramp_up_duration_local = ramp_up_duration
        ramp_down_duration_local = ramp_down_duration

    step_interval_up = ramp_up_duration_local / steps
    step_interval_down = ramp_down_duration_local / steps
    mem_chunk_mb = memory_mb / steps if steps > 0 else 0
    cores_per_step = cpu_cores / steps if steps > 0 else 0 # Can be fractional

    print(f"Phase Durations: Ramp Up={ramp_up_duration_local:.1f}s, Hold={hold_duration:.1f}s, Ramp Down={ramp_down_duration_local:.1f}s")
    print(f"Steps: {steps}, CPU/step: {cores_per_step:.2f}, Mem/step: {mem_chunk_mb:.2f}MB")


    def signal_handler(sig, frame):
        # ... (signal handler remains the same) ...
        print("\\nSIGINT received. Initiating cleanup...")
        # Restore original handler to prevent re-entry if cleanup hangs
        signal.signal(signal.SIGINT, original_sigint_handler)
        # Trigger cleanup by raising KeyboardInterrupt in the main loop
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, signal_handler)

    try:
        while True:
            # --- High Stress Phase ---
            print(f"\\n--- Starting HIGH stress phase ({high_duration_sec}s) ---")
            print(f"Target: CPU={cpu_cores} cores, Memory={memory_mb}MB over {steps} steps")

            current_target_cores = 0
            all_processes = [] # Keep track of all started processes
            allocated_chunks = [] # Keep track of allocated memory

            # --- Ramp Up ---
            print(f"Ramping up over {ramp_up_duration_local:.1f}s...")
            for step in range(steps):
                step_start_time = time.time()
                target_cores_this_step = int((step + 1) * cores_per_step)
                cores_to_add = target_cores_this_step - len(all_processes)

                # Start CPU processes for this step
                if cores_to_add > 0:
                    print(f"  Step {step+1}/{steps}: Starting {cores_to_add} CPU processes (target: {target_cores_this_step})...")
                    for _ in range(cores_to_add):
                        if len(all_processes) >= cpu_cores: # Safety check
                            break
                        try:
                            p = multiprocessing.Process(target=cpu_worker, daemon=True, name=f"CPU_Worker_{len(all_processes)}")
                            p.start()
                            all_processes.append(p)
                        except Exception as e:
                            print(f"ERROR: Failed to start CPU process: {e}", file=sys.stderr)
                            # Continue trying to add others if one fails

                # Allocate Memory chunk for this step
                if mem_chunk_mb > 0:
                    print(f"  Step {step+1}/{steps}: Allocating {mem_chunk_mb:.2f} MB memory chunk...")
                    chunk = allocate_memory_chunk(mem_chunk_mb)
                    if chunk:
                        allocated_chunks.append(chunk)
                    else:
                        print(f"  Warning: Failed to allocate memory chunk in step {step+1}.", file=sys.stderr)
                        # Continue even if memory allocation fails

                # Wait for the remainder of the step interval
                elapsed_time = time.time() - step_start_time
                sleep_time = max(0, step_interval_up - elapsed_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            print(f"Ramp up complete. Current load: {len(all_processes)} CPU processes, {len(allocated_chunks) * mem_chunk_mb:.2f} MB memory.")

            # --- Hold Phase ---
            if hold_duration > 0:
                print(f"Holding peak load for {hold_duration:.1f}s...")
                time.sleep(hold_duration)            # --- Ramp Down ---
            print(f"Ramping down over {ramp_down_duration_local:.1f}s...")
            # Determine how many cores and memory to keep for low phase
            target_low_cores = max(1, int(cpu_cores * low_phase_percent))
            target_low_memory_chunks = max(1, int(len(allocated_chunks) * low_phase_percent))
            
            print(f"Target for low phase: {target_low_cores} CPU cores, {target_low_memory_chunks} memory chunks")
            
            for step in range(steps):
                step_start_time = time.time()
                # Calculate how many cores to have after this step, but not less than low phase target
                target_cores_after_step = max(target_low_cores, 
                                             int(cpu_cores - (step + 1) * (cpu_cores - target_low_cores) / steps))
                cores_to_stop = len(all_processes) - target_cores_after_step

                # Stop CPU processes for this step
                if cores_to_stop > 0:
                    print(f"  Step {step+1}/{steps}: Stopping {cores_to_stop} CPU processes (target: {target_cores_after_step})...")
                    processes_to_terminate = []
                    for _ in range(cores_to_stop):
                        if len(all_processes) > target_low_cores:  # Don't go below low phase target
                            processes_to_terminate.append(all_processes.pop()) # Remove from the end
                    if processes_to_terminate:
                        terminate_processes(processes_to_terminate) # Terminate the removed ones

                # Release Memory chunk for this step
                if allocated_chunks and mem_chunk_mb > 0:
                    # Only release memory if we're still above our low phase target
                    if len(allocated_chunks) > target_low_memory_chunks:
                        print(f"  Step {step+1}/{steps}: Releasing memory chunk...")
                        # Release one chunk per step (simplest approach)
                        chunk_to_release = [allocated_chunks.pop()] # Wrap in list for release_memory
                        release_memory(chunk_to_release) # release_memory expects a list
                    else:
                        print(f"  Step {step+1}/{steps}: Keeping remaining {len(allocated_chunks)} memory chunks for low phase.")

                # Wait for the remainder of the step interval
                elapsed_time = time.time() - step_start_time
                sleep_time = max(0, step_interval_down - elapsed_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            print("Ramp down complete.")
            # Check current resource levels
            current_cpu_percent = len(all_processes) / cpu_cores * 100 if cpu_cores > 0 else 0
            current_mem_percent = len(allocated_chunks) / steps * 100 if steps > 0 else 0
            print(f"Current load: {len(all_processes)} CPU processes ({current_cpu_percent:.1f}%), {len(allocated_chunks)} memory chunks ({current_mem_percent:.1f}%)")


            # --- Low Stress Phase ---
            print(f"\\n--- Starting LOW stress phase ({low_duration_sec}s) ---")
            print(f"Maintaining {low_phase_percent*100:.0f}% load: ~{len(all_processes)} CPU processes, ~{len(allocated_chunks)} memory chunks")
            time.sleep(low_duration_sec)

    except KeyboardInterrupt:
        # ... (exception handling remains similar) ...
        print("\\nStress test interrupted by user (KeyboardInterrupt). Cleaning up...")
    except Exception as e:
        # ... (exception handling remains similar) ...
        print(f"\\nAn unexpected error occurred: {e}", file=sys.stderr)
        print("Attempting cleanup...")
    finally:
        # Final cleanup: Ensure all resources are released
        print("\\n--- Final Cleanup ---")
        if all_processes: # Use the list tracking all processes
            print("Terminating any remaining CPU processes...")
            terminate_processes(all_processes)
        if allocated_chunks: # Use the list tracking allocated chunks
            print("Releasing any remaining allocated memory...")
            release_memory(allocated_chunks) # release_memory clears the list

        # Restore original SIGINT handler
        signal.signal(signal.SIGINT, original_sigint_handler)
        print("Cleanup complete. Exiting.")


if __name__ == "__main__":
    # --- Configuration from environment variables or defaults ---
    # Read high stress duration (seconds) from environment or use default
    HIGH_STRESS_DURATION_SECONDS = get_env_int("HIGH_STRESS_DURATION", 120)
    
    # Read low stress duration (seconds) from environment or use default
    LOW_STRESS_DURATION_SECONDS = get_env_int("LOW_STRESS_DURATION", 300)
    
    # Read number of ramp steps from environment or use default
    RAMP_STEPS = get_env_int("RAMP_STEPS", 10)
    
    # Read ramp up/down durations (seconds) from environment or use defaults
    RAMP_UP_DURATION = get_env_float("RAMP_UP_DURATION", 20.0)
    RAMP_DOWN_DURATION = get_env_float("RAMP_DOWN_DURATION", 20.0)
    
    # Read low phase percentage from environment or use default (0.1 = 10%)
    LOW_PHASE_PERCENT = get_env_float("LOW_PHASE_PERCENT", 0.1)

    # Random startup delay to prevent synchronized cycles across replicas
    STARTUP_DELAY_MAX_SEC = get_env_float("STARTUP_RANDOM_DELAY_MAX_SEC", 30.0)
    
    # Determine number of CPU cores to use
    try:
        # Use all available cores by default
        total_cores = multiprocessing.cpu_count()
        # Read max CPU cores from environment or use all available
        CPU_CORES_TO_STRESS = get_env_int("MAX_CPU_CORES", total_cores)
    except NotImplementedError:
        print("Warning: Could not detect number of CPU cores. Defaulting to 1.", file=sys.stderr)
        CPU_CORES_TO_STRESS = 1

    # Memory to allocate in MB during high stress
    MEMORY_TO_ALLOCATE_MB = get_env_int("MAX_MEMORY_MB", 1024)

    # --- Start Script ---
    print("--- Cyclical CPU & Memory Stress Test (Gradual Steps) ---")
    print(f"Total High Stress Duration: {HIGH_STRESS_DURATION_SECONDS}s")
    print(f"Low Stress Duration:      {LOW_STRESS_DURATION_SECONDS}s")
    print(f"Ramp Steps:               {RAMP_STEPS}")
    print(f"Ramp Up Duration:         {RAMP_UP_DURATION}s")
    print(f"Ramp Down Duration:       {RAMP_DOWN_DURATION}s")
    print(f"Target CPU Cores:         {CPU_CORES_TO_STRESS} (out of {total_cores if 'total_cores' in locals() else 'N/A'} available)")
    print(f"Target Memory:            {MEMORY_TO_ALLOCATE_MB}MB")
    print(f"Low Phase Load:           {LOW_PHASE_PERCENT*100:.0f}% of peak")
    print(f"Max Random Startup Delay: {STARTUP_DELAY_MAX_SEC}s")
    print("----------------------------------------------------------")
    
    # Apply random startup delay if configured
    if STARTUP_DELAY_MAX_SEC > 0:
        delay = random.uniform(0, STARTUP_DELAY_MAX_SEC)
        print(f"Applying random startup delay of {delay:.2f}s to avoid synchronized cycles...")
        time.sleep(delay)
    
    print("Starting stress test cycle. Press Ctrl+C to stop.")
    # Ensure multiprocessing works correctly when frozen (e.g., with PyInstaller)
    multiprocessing.freeze_support()

    run_stress_cycle(
        HIGH_STRESS_DURATION_SECONDS,
        LOW_STRESS_DURATION_SECONDS,
        CPU_CORES_TO_STRESS,
        MEMORY_TO_ALLOCATE_MB,
        RAMP_STEPS, # Pass the number of steps
        LOW_PHASE_PERCENT, # Pass the low phase percentage
        RAMP_UP_DURATION,  # Pass ramp up duration from env
        RAMP_DOWN_DURATION # Pass ramp down duration from env
    )