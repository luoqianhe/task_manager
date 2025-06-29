# src/utils/debug_init.py

from utils.debug_logger import get_debug_logger
import argparse

def init_debugger(args=None):
    """
    Initialize the debugger based on command line arguments
    or passed arguments.
    """
    # Get the logger
    logger = get_debug_logger()
    
    if args is None:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Task Organizer Debug Configuration')
        parser.add_argument('--debug', action='store_true', help='Enable debugging')
        parser.add_argument('--debug-file', action='store_true', help='Log to file')
        parser.add_argument('--debug-console', action='store_true', help='Log to console')
        parser.add_argument('--debug-all', action='store_true', help='Debug all classes/methods')
        parser.add_argument('--debug-file-path', type=str, help='Path to log file')
        parser.add_argument('--debug-class', action='append', help='Class to debug')
        parser.add_argument('--debug-method', action='append', help='Method to debug')
        
        try:
            args = parser.parse_args()
        except SystemExit:
            # In case of argument parsing errors, still return a configured logger
            logger.configure(enabled=False, log_to_console=False, log_to_file=False)
            return logger
    
    # Configure based on arguments
    if hasattr(args, 'debug') and args.debug:
        # Determine output modes
        log_to_file = args.debug_file if hasattr(args, 'debug_file') else False
        log_to_console = args.debug_console if hasattr(args, 'debug_console') else True
        
        # Configure the logger
        logger.configure(
            enabled=True,
            log_to_file=log_to_file,
            log_to_console=log_to_console,
            log_file_path=args.debug_file_path if hasattr(args, 'debug_file_path') else None,
            debug_all=args.debug_all if hasattr(args, 'debug_all') else False
        )
        
        # Add filters if any
        if hasattr(args, 'debug_class') and args.debug_class:
            for class_name in args.debug_class:
                logger.add_class_filter(class_name)
                
        if hasattr(args, 'debug_method') and args.debug_method:
            for method_name in args.debug_method:
                logger.add_method_filter(method_name)
                
        # Set logger's internal state directly for consistency
        logger._enabled = True
        logger._log_to_file = log_to_file
        logger._log_to_console = log_to_console
        logger._debug_all = args.debug_all if hasattr(args, 'debug_all') else False
        
        # Log initialization
        logger.debug("Debug logger initialized with enabled=True")
        logger.debug(f"Log to file: {log_to_file}, Log to console: {log_to_console}")
    else:
        # Default configuration when --debug is not specified
        logger.configure(enabled=False)
        logger._enabled = False
        logger._log_to_file = False
        logger._log_to_console = False
        logger._debug_all = False
    
    return logger

# Helper function to configure debugger from settings
def configure_from_settings(settings_manager):
    """Initialize the debugger based on application settings"""
    debug_enabled = settings_manager.get_setting("debug_enabled", False)
    
    # Create arguments object
    args = argparse.Namespace()
    args.debug = debug_enabled
    args.debug_file = debug_enabled
    args.debug_console = debug_enabled
    args.debug_all = True  # Debug all classes/methods by default
    args.debug_file_path = None  # Use default path
    
    # Initialize the debugger
    logger = init_debugger(args)
    
    return logger

# If run directly, initialize the debugger
if __name__ == "__main__":
    debug = init_debugger()
    debug.debug("Debug initialization test")