import logging
import sys
from logging.handlers import RotatingFileHandler
import os
from crm.core.settings import get_settings

settings = get_settings()
DEBUG_MODE = settings.DEBUG
print(f"The DEBUG MODE is : {DEBUG_MODE}")

# Compute project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Logs folder at the project root
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True) 

# Configure the logger
def setup_logger(name, log_file, level=logging.INFO):
    """
    Description: Setup a logger with both file handler and console handler with rotation support
    
    args:
        name (str): Name of the logger instance
        log_file (str): Path to the log file for file handler
        level: Logging level, defaults to logging.INFO
    
    returns:
        logging.Logger: Configured logger instance with file and console handlers
    """
    logger = logging.getLogger(name)
    
    logger.setLevel(level)

    # Determine the log level based on DEBUG_MODE
    handle_level = logging.INFO if DEBUG_MODE else logging.ERROR

    # Create file handler
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
    file_handler.setLevel(handle_level)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(handle_level)

    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Create loggers for different modules
logger = setup_logger('crm', os.path.join(log_dir, 'crm.log'))

# Usage
def log_info(message):
    """
    Description: Log an info message using the configured crm logger
    
    args:
        message (str): Message to log at info level
    
    returns:
        None: Logs message to both file and console
    """
    logger.info(message)

