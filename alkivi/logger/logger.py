"""Alkivi Logger used in scripts

Define a logger that can handle mail syslog file and other stuff
See the scripts in sample for better explanation
"""
import logging
import logging.handlers
import logging.config
import sys
import os
import pwd
import socket
import pprint

from .handlers import AlkiviEmailHandler

# Globals used to send extra information using emails
SOURCE = sys.argv[0]
SOURCEDIR = os.path.realpath(SOURCE)
PID = os.getpid()
USER = pwd.getpwuid(os.getuid()).pw_name
HOST = socket.gethostname()


class Logger():
    """
        This class defines a custom Logger class.

        This main property is iteration which allow to perform loop iteration
        easily
    """
    def __init__(self, logger,
                 min_log_level_to_print=logging.INFO,
                 min_log_level_to_mail=logging.WARNING,
                 min_log_level_to_save=logging.INFO,
                 min_log_level_to_syslog=logging.WARNING,
                 filename=None,
                 emails=None):
        """
        Create a Logger object, that can be used to log.

        Will set several handlers according to what we want.
        """
        if filename is None:
            filename = '%s.log' % SOURCE
        if emails is None:
            emails = []

        # Default Attributes
        self.subject = "%s_%i" % (SOURCE, PID)
        self.filename = filename
        self.emails = emails
        self.prefix = []

        # Default level
        self.min_log_level_to_print = min_log_level_to_print
        self.min_log_level_to_save = min_log_level_to_save
        self.min_log_level_to_mail = min_log_level_to_mail
        self.min_log_level_to_syslog = min_log_level_to_syslog

        # Set and tracks all handlers
        self.handlers = []

        # Create object Dumper
        self.pretty_printer = pprint.PrettyPrinter(indent=4)

        # Init Root Logger
        self.root_logger = logging.getLogger()
        self.init_root_logger()

        # Init our logger
        self.logger = logger
        self.init_logger()

    def _log(self, priority, message, *args, **kwargs):
        """Generic log functions
        """
        for arg in args:
            message = message + "\n" + self.pretty_printer.pformat(arg)

        self.logger.log(priority, message)

    def debug(self, message, *args, **kwargs):
        """Debug level to use and abuse when coding
        """
        self._log(logging.DEBUG, message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        """More important level : default for print and save
        """
        self._log(logging.INFO, message, *args, **kwargs)

    def warn(self, message, *args, **kwargs):
        """Send email and syslog by default ...
        """
        self._log(logging.WARNING, message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        """Alias to warn
        """
        self._log(logging.WARNING, message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        """Should not happen ...
        """
        self._log(logging.ERROR, message, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        """Highest level
        """
        self._log(logging.CRITICAL, message, *args, **kwargs)

    def exception(self, message, *args, **kwargs):
        """Handle exception
        """
        self.logger.exception(message, *args, **kwargs)

    def init_root_logger(self):
        """Create configuration for the root logger."""
        # All logs are comming to this logger
        self.root_logger.setLevel(0)

        # Logging to console
        if self.min_log_level_to_print:
            level = self.min_log_level_to_print
            handler_class = logging.StreamHandler
            self._create_handler(handler_class, level)

        # Logging to file
        if self.min_log_level_to_save:
            level = self.min_log_level_to_save
            handler_class = logging.handlers.TimedRotatingFileHandler
            self._create_handler(handler_class, level)

        # Logging to syslog
        if self.min_log_level_to_syslog:
            level = self.min_log_level_to_syslog
            handler_class = logging.handlers.SysLogHandler
            self._create_handler(handler_class, level)

        # Logging to email
        if self.min_log_level_to_mail:
            level = self.min_log_level_to_mail
            handler_class = AlkiviEmailHandler
            self._create_handler(handler_class, level)

        return

    def init_logger(self):
        """Init app logger with format."""
        pass

    def new_loop_logger(self):
        """
        Add a prefix to the correct logger
        """
        # Add a prefix but dont refresh formatter
        # This will happen in new_iteration
        self.prefix.append('')

        # Flush data (i.e send email if needed)
        self.flush()
        return

    def del_loop_logger(self):
        """Delete the loop previsouly created and continues
        """
        # Pop a prefix
        self.prefix.pop()
        self.reset_formatter()

        # Flush data (i.e send email if needed)
        self.flush()
        return

    def new_iteration(self, prefix):
        """When inside a loop logger, created a new iteration
        """
        # Flush data for the current iteration
        self.flush()

        # Fix prefix
        self.prefix[-1] = prefix
        self.reset_formatter()

    def reset_formatter(self):
        """Rebuild formatter for all handlers."""
        for handler in self.handlers:
            formatter = self.get_formatter(handler)
            handler.setFormatter(formatter)

    def flush(self):
        """Flush data when dealing with iteration."""
        for handler in self.handlers:
            handler.flush()

    def _set_min_level(self, handler_class, level):
        """Generic method to setLevel for handlers."""
        if self._exist_handler(handler_class):
            if not level:
                self._delete_handler(handler_class)
            else:
                self._update_handler(handler_class, level=level)
        else:
            self._create_handler(handler_class, level)

    def set_min_level_to_print(self, level):
        """Allow to change print level after creation
        """
        self.min_log_level_to_print = level
        handler_class = logging.StreamHandler
        self._set_min_level(handler_class, level)

    def set_min_level_to_save(self, level):
        """Allow to change save level after creation
        """
        self.min_log_level_to_save = level
        handler_class = logging.handler_class.TimedRotatingFileHandler
        self._set_min_level(handler_class, level)

    def set_min_level_to_mail(self, level):
        """Allow to change mail level after creation
        """
        self.min_log_level_to_mail = level
        handler_class = AlkiviEmailHandler
        self._set_min_level(handler_class, level)

    def set_min_level_to_syslog(self, level):
        """Allow to change syslog level after creation
        """
        self.min_log_level_to_syslog = level
        handler_class = logging.handlers.SysLogHandler
        self._set_min_level(handler_class, level)

    def _get_handler(self, handler_class):
        """Return an existing class of handler."""
        element = None
        for handler in self.handlers:
            if isinstance(handler, handler_class):
                element = handler
                break
        return element

    def _exist_handler(self, handler_class):
        """Return True or False is the class exists."""
        return self._get_handler(handler_class) is not None

    def _delete_handler(self, handler_class):
        """Delete a specific handler from our logger."""
        to_remove = self._get_handler(handler_class)
        if not to_remove:
            logging.warning('Error we should have an element to remove')
        else:
            self.handlers.remove(to_remove)
            self.root_logger.removeHandler(to_remove)

    def _update_handler(self, handler_class, level):
        """Update the level of an handler."""
        handler = self._get_handler(handler_class)
        handler.setLevel(level)

    def _create_handler(self, handler_class, level):
        """Create an handler for at specific level."""
        if handler_class == logging.StreamHandler:
            handler = handler_class()
            handler.setLevel(level)
        elif handler_class == logging.handlers.SysLogHandler:
            handler = handler_class(address='/dev/log')
            handler.setLevel(level)
        elif handler_class == logging.handlers.TimedRotatingFileHandler:
            handler = handler_class(self.filename, when='midnight')
            handler.setLevel(level)
        elif handler_class == AlkiviEmailHandler:
            handler = handler_class(mailhost='127.0.0.1',
                                    fromaddr="%s@%s" % (USER, HOST),
                                    toaddrs=self.emails,
                                    level=self.min_log_level_to_mail)
            # Needed, we want all logs to go there
            handler.setLevel(0)

        formatter = self.get_formatter(handler)
        handler.setFormatter(formatter)
        self.handlers.append(handler)
        self.root_logger.addHandler(handler)

    def get_formatter(self, handler):
        """
        Return formatters according to handler.

        All handlers are the same format, except syslog.
        We omit time when syslogging.
        """
        if isinstance(handler, logging.handlers.SysLogHandler):
            formatter = '[%(levelname)-9s]'
        else:
            formatter = '[%(asctime)s] [%(levelname)-9s]'

        for p in self.prefix:
            formatter += ' [%s]' % (p)
        formatter = formatter + ' %(message)s'
        return logging.Formatter(formatter)
