# src/utils/debug_logger.py

import logging
import os
import sys
import inspect
import datetime
from pathlib import Path

class DebugLogger:
    """
    Flexible debugging utility that can log to file, console, or both.
    Supports filtering by class or method name.
    Uses the format: [log time]: [Class.method]: debug message
    """
    _instance = None  # Singleton instance
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DebugLogger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Default configuration
        self._initialized = True
        self._enabled = False
        self._log_to_file = False
        self._log_to_console = True
        self._log_file_path = None
        self._logger = None
        self._class_filters = []
        self._method_filters = []
        self._debug_all = False
   
    def configure(self, enabled=True, log_to_file=True, log_to_console=True, 
                log_file_path=None, debug_all=False, debug_level=logging.DEBUG):
        """Configure the debug logger settings."""
        self._enabled = enabled
        self._log_to_file = log_to_file
        self._log_to_console = log_to_console
        self._debug_all = debug_all
        
        # Set up log file path
        if log_file_path:
            self._log_file_path = Path(log_file_path)
        else:
            # Default log file in user's home directory
            log_dir = Path.home() / ".task_organizer" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self._log_file_path = log_dir / f"debug_{timestamp}.log"
        
        # Configure logger
        self._logger = logging.getLogger('TaskOrganizerDebug')
        self._logger.setLevel(debug_level)
        self._logger.handlers = []  # Clear any existing handlers
        
        # Create a formatter that matches the requested format: [log time]: [Class.method]: message
        formatter = logging.Formatter('%(asctime)s: %(message)s')
        
        # Add console handler if requested
        if self._log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)
        
        # Add file handler if requested
        if self._log_to_file:
            # NEW: Make sure parent directory exists
            self._log_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(self._log_file_path)
            file_handler.setFormatter(formatter)
            # NEW: Set to immediately flush after each log
            file_handler.setLevel(debug_level)
            self._logger.addHandler(file_handler)
        
        # NEW: Disable propagation to prevent duplicate logs
        self._logger.propagate = False
        
        # NEW: Report where logs will go
        print(f"Debug logging enabled: console={self._log_to_console}, file={self._log_to_file}")
        if self._log_to_file:
            print(f"Debug log file: {self._log_file_path}")
            
        # Log configuration details
        self.log("Debug logger configured")
        self.log(f"Log to file: {self._log_to_file}, Path: {self._log_file_path}")
        self.log(f"Log to console: {self._log_to_console}")
        self.log(f"Debug all: {self._debug_all}")
        
        # NEW: Force flush all handlers
        for handler in self._logger.handlers:
            handler.flush()     
        
    def add_class_filter(self, class_name):
        """Add a class name to filter debug messages."""
        if class_name not in self._class_filters:
            self._class_filters.append(class_name)
            self.log(f"Added class filter: {class_name}")
    
    def add_method_filter(self, method_name):
        """Add a method name to filter debug messages."""
        if method_name not in self._method_filters:
            self._method_filters.append(method_name)
            self.log(f"Added method filter: {method_name}")
    
    def clear_filters(self):
        """Clear all class and method filters."""
        self._class_filters = []
        self._method_filters = []
        self.log("All filters cleared")
    
    def should_log(self, class_name=None, method_name=None):
        """Determine if a message should be logged based on filters."""
        # If debugging is disabled, don't log
        if not self._enabled:
            return False
        
        # If debug all is enabled, always log
        if self._debug_all:
            return True
        
        # If no filters are set, log everything
        if not self._class_filters and not self._method_filters:
            return True
        
        # Check if the class or method is in our filters
        if class_name and class_name in self._class_filters:
            return True
        
        if method_name and method_name in self._method_filters:
            return True
        
        # Neither class nor method matched filters
        return False
    
    def _get_caller_info(self):
        """Get information about the caller."""
        stack = inspect.stack()
        # Look for the first frame that isn't in this file
        for frame in stack[2:]:  # Skip this method and the log method
            module = inspect.getmodule(frame[0])
            if module and module.__name__ != __name__:
                # Get frame info
                function = frame.function
                
                # Try to determine class name if method is within a class
                class_name = None
                try:
                    if 'self' in frame[0].f_locals:
                        class_name = frame[0].f_locals['self'].__class__.__name__
                except:
                    pass
                
                return {
                    'function': function,
                    'class': class_name
                }
        
        return None
    
    def log(self, message, level=logging.DEBUG):
        """Log a debug message if it passes the filters."""
        if not self._enabled or not self._logger:
            return
        
        caller_info = self._get_caller_info()
        
        # Skip debug.py's own logs
        if caller_info and caller_info.get('function') in ['log', 'debug', 'info', 'warning', 'error', 'critical']:
            self._logger.log(level, message)
            return
        
        # Check if we should log this message based on caller info
        if caller_info and not self.should_log(caller_info.get('class'), caller_info.get('function')):
            return
        
        # Format the message with caller info in the specified format: [Class.method]: message
        formatted_message = message
        if caller_info:
            class_name = caller_info.get('class', '')
            method_name = caller_info.get('function', '')
            
            if class_name:
                prefix = f"[{class_name}.{method_name}]: "
            else:
                prefix = f"[{method_name}]: "
                
            formatted_message = f"{prefix}{message}"
        
        # Log the message
        self._logger.log(level, formatted_message)
    
    def debug(self, message):
        """Log a debug level message."""
        self.log(message, logging.DEBUG)
    
    def info(self, message):
        """Log an info level message."""
        self.log(message, logging.INFO)
    
    def warning(self, message):
        """Log a warning level message."""
        self.log(message, logging.WARNING)
    
    def error(self, message):
        """Log an error level message."""
        self.log(message, logging.ERROR)
    
    def critical(self, message):
        """Log a critical level message."""
        self.log(message, logging.CRITICAL)
    
    def disable(self):
        """Disable the debugger."""
        self._enabled = False
    
    def enable(self):
        """Enable the debugger."""
        self._enabled = True
    
    @property
    def log_file_path(self):
        """Get the current log file path."""
        return self._log_file_path
    
    def set_debug_all(self, debug_all=True):
        """Set whether to debug all classes/methods or use filters."""
        self._debug_all = debug_all
        self.log(f"Debug all set to: {debug_all}")

# Create a singleton instance
debug_logger = DebugLogger()

# Convenience function to access the logger
def get_debug_logger():
    return debug_logger