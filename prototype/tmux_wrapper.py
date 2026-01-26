import json
import subprocess
import sys
import time

def run_tmux_command(command):
    """Run a tmux command using subprocess."""
    try:
        result = subprocess.run(['tmux'] + command.split(), check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e.stderr.strip()}"

def create_tmux_session(config):
    """Create and configure a tmux session based on the JSON config."""
    session_name = config.get('session_name', 'default_session')
    
    # Check if session already exists
    existing_sessions_result = run_tmux_command('list-sessions -F "#{session_name}"')
    if "ERROR:" in existing_sessions_result:
        if "error connecting" in existing_sessions_result or "no server running" in existing_sessions_result:
            print(f"No tmux server running. Creating new session '{session_name}'...")
        else:
            print(f"Error checking sessions: {existing_sessions_result}")
            sys.exit(1)
        existing_sessions = []
    else:
        existing_sessions = existing_sessions_result.splitlines()
    
    if session_name in existing_sessions:
        print(f"Session '{session_name}' already exists. Attaching...")
        subprocess.run(['tmux', 'attach', '-t', session_name])
        return

    # Create new detached session
    run_tmux_command(f'new-session -d -s {session_name}')

    # Process each window
    for window in config.get('windows', []):
        window_name = window.get('window_name', 'main')
        
        # Create the window
        run_tmux_command(f'new-window -t {session_name} -n {window_name}')
        
        # Set layout if specified (e.g., 'even-horizontal' for vertical split)
        layout = window.get('layout', None)
        if layout:
            run_tmux_command(f'select-layout -t {session_name}:{window_name} {layout}')
        
        panes = window.get('panes', [])
        num_panes = len(panes)
        
        # Split panes if more than one
        for i in range(1, num_panes):
            # Assuming vertical split for side-by-side; adjust if needed (use -v for horizontal)
            run_tmux_command(f'split-window -h -t {session_name}:{window_name}')
        
        # Configure each pane
        for idx, pane in enumerate(panes):
            commands = pane.get('commands', [])
            # Select the pane
            run_tmux_command(f'select-pane -t {session_name}:{window_name}.{idx}')
            # Send commands to the pane
            for cmd in commands:
                run_tmux_command(f'send-keys -t {session_name}:{window_name}.{idx} "{cmd}" C-m')
                time.sleep(0.1)  # Small delay to ensure commands execute in order

    # Attach to the session
    subprocess.run(['tmux', 'attach', '-t', session_name])

def main():
    if len(sys.argv) < 2:
        print("Usage: python tmux_wrapper.py <path_to_config.json>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Config file '{config_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Invalid JSON in '{config_path}'.")
        sys.exit(1)
    
    create_tmux_session(config)

if __name__ == "__main__":
    main()
