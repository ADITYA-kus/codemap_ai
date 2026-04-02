"""Simple progress spinner for terminal output."""

import sys
import time
from threading import Thread
from typing import Optional


class ProgressSpinner:
    """A simple terminal progress spinner with rotating animation.
    
    Shows a rotating spinner animation while a long-running operation is in progress.
    Useful for giving users feedback that the program is still working.
    
    Example:
        spinner = ProgressSpinner("Analyzing repository...")
        spinner.start()
        time.sleep(5)  # Long operation
        spinner.stop()
    """
    
    FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    # Fallback for terminals that don't support Unicode
    FRAMES_ASCII = ['|', '/', '-', '\\']
    
    def __init__(self, message: str = "Processing..."):
        """Initialize the spinner.
        
        Args:
            message: Text to display next to the spinner
        """
        self.message = message
        self.running = False
        self.thread: Optional[Thread] = None
        self.frame_index = 0
        self._use_unicode = True
        
    def _animate(self) -> None:
        """Animation loop for the spinner."""
        frames = self.FRAMES if self._use_unicode else self.FRAMES_ASCII
        
        while self.running:
            frame = frames[self.frame_index % len(frames)]
            # Use \r to return to start of line, overwrite previous output
            sys.stderr.write(f"\r{frame} {self.message}")
            sys.stderr.flush()
            
            self.frame_index += 1
            time.sleep(0.1)  # Smooth animation at ~10 FPS
    
    def start(self) -> None:
        """Start the spinner animation."""
        if not self.running:
            self.running = True
            self.frame_index = 0
            self.thread = Thread(target=self._animate, daemon=True)
            self.thread.start()
    
    def stop(self) -> None:
        """Stop the spinner and clear the line."""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=1)
            # Clear the spinner line
            sys.stderr.write("\r" + " " * (len(self.message) + 4) + "\r")
            sys.stderr.flush()
    
    def update(self, message: str) -> None:
        """Update the message displayed with the spinner.
        
        Args:
            message: New message text
        """
        self.message = message
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
