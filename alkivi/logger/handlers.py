# -*- encoding: utf-8 -*-

import logging
import os
import pwd
import smtplib
import socket
import sys

from collections import OrderedDict

try:
    from email.message import EmailMessage
    USE_MIME = False
except ImportError:  # pragma: no cover
    from email.mime.text import MIMEText
    USE_MIME = True

# Globals used to send extra information using emails
SOURCE = sys.argv[0]
SOURCEDIR = os.path.realpath(SOURCE)
PID = os.getpid()
USER = pwd.getpwuid(os.getuid()).pw_name
HOST = socket.gethostname()


class AlkiviEmailHandler(logging.Handler):
    """Custom class that will handle email sending

    When log level reach a certains level and receive flush :
    - flush the logger with the current message
    - send the full trace of the current logger (all level)
    """
    def __init__(self, mailhost, fromaddr, toaddrs, level):
        logging.Handler.__init__(self)
        self.mailhost = mailhost
        self.mailport = None
        self.fromaddr = fromaddr
        self.toaddrs = toaddrs
        self.flush_level = level

        # Init another buffer which will store everything
        self.complete_buffer = []

        # Buffer is an array that contains formatted messages
        self.current_buffer = []

    def emit(self, record):
        msg = self.format(record)

        if(record.levelno >= self.flush_level):
            self.current_buffer.append(msg)

        # Add to all buffer in any case
        self.complete_buffer.append(msg)

    def generate_mail(self):
        """Generate the email as MIMEText
        """

        # Script info
        msg = "Script info : \r\n"
        msg = msg + "%-9s: %s" % ('Script', SOURCEDIR) + "\r\n"
        msg = msg + "%-9s: %s" % ('User', USER) + "\r\n"
        msg = msg + "%-9s: %s" % ('Host', HOST) + "\r\n"
        msg = msg + "%-9s: %s" % ('PID', PID) + "\r\n"

        # Current trace
        msg = msg + "\r\nCurrent trace : \r\n"
        for record in self.current_buffer:
            msg = msg + record + "\r\n"

        # Now add stack trace
        msg = msg + "\r\nFull trace : \r\n"
        for record in self.complete_buffer:
            msg = msg + record + "\r\n"

        # Dump ENV
        msg = msg + "\r\nEnvironment:" + "\r\n"
        environ = OrderedDict(sorted(os.environ.items()))
        for name, value in environ.items():
            msg = msg + "%-10s = %s\r\n" % (name, value)

        if USE_MIME:
            real_msg = MIMEText(msg, _charset='utf-8')

            real_msg['Subject'] = self.get_subject()
            real_msg['To'] = ','.join(self.toaddrs)
            real_msg['From'] = self.fromaddr

        else:
            real_msg = EmailMessage()

            real_msg['Subject'] = self.get_subject()
            real_msg['To'] = ','.join(self.toaddrs)
            real_msg['From'] = self.fromaddr

            real_msg.set_content(msg)

        return real_msg

    def get_subject(self):
        """Generate the subject."""
        level = logging.getLevelName(self.flush_level)
        message = self.current_buffer[0].split("\n")[0]
        message = message.split(']')[-1]
        return '{0} : {1}{2}'.format(level, SOURCE, message)

    def flush(self):
        if len(self.current_buffer) > 0:
            try:
                port = self.mailport
                if not port:
                    port = smtplib.SMTP_PORT

                smtp = smtplib.SMTP(self.mailhost, port)
                msg = self.generate_mail()

                if USE_MIME:
                    smtp.sendmail(self.fromaddr, self.toaddrs, msg.__str__())
                else:
                    smtp.send_message(msg)
                smtp.quit()
            except Exception:
                self.handleError(None)  # no particular record

        self.current_buffer = []
        self.complete_buffer = []
