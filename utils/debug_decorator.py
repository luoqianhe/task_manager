# In src/utils/debug_decorator.py
from functools import wraps
from .debug_logger import get_debug_logger

def debug_method(func):
    """
    Decorator to automatically log method entry, exit and exceptions.
    Uses the format: [log time]: [Class.method]: message
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_debug_logger()
        
        # Force debug logger to be enabled, eliminate filtering
        logger._enabled = False
        logger._debug_all = False
        
        # More accurate class name detection
        class_name = args[0].__class__.__name__ if args and hasattr(args[0], '__class__') else None
        method_name = func.__name__
        
        # Add direct console output to verify decorator is running
        print(f"DEBUG DECORATOR: {class_name}.{method_name} called")
        
        # Always log regardless of filters
        logger.debug(f"ENTER ({', '.join([repr(a) for a in args[1:]] + [f'{k}={repr(v)}' for k, v in kwargs.items()])})")
        
        try:
            # Call the original function
            result = func(*args, **kwargs)
            
            # Log method exit with result
            if result is not None:
                logger.debug(f"EXIT -> {repr(result)}")
            else:
                logger.debug(f"EXIT")
                
            return result
            
        except Exception as e:
            # Log any exceptions
            logger.error(f"EXCEPTION: {type(e).__name__}: {str(e)}")
            raise  # Re-raise the exception
            
    return wrapper