# -*- encoding: utf-8 -*-

import sys
import os
import pwd
import logging
import smtplib
import socket

from email.mime.text import MIMEText

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
        self.allbuffer = []

        # Buffer is an array that contains formatted messages
        self.buffer = []

    def emit(self, record):
        msg = self.format(record)

        if(record.levelno >= self.flush_level):
            self.buffer.append(msg)

        # Add to all buffer in any case
        self.allbuffer.append(msg)

    def generate_mail(self):
        """Generate the email as MIMEText
        """

        # Script info
        msg = "Script info : \r\n"
        msg = msg + "%-9s: %s" % ('Script', SOURCE) + "\r\n"
        msg = msg + "%-9s: %s" % ('User', USER) + "\r\n"
        msg = msg + "%-9s: %s" % ('Host', HOST) + "\r\n"
        msg = msg + "%-9s: %s" % ('PID', PID) + "\r\n"

        # Current trace
        msg = msg + "\r\nCurrent trace : \r\n"
        for record in self.buffer:
            msg = msg + record + "\r\n"

        # Now add stack trace
        msg = msg + "\r\nFull trace : \r\n"
        for record in self.allbuffer:
            msg = msg + record + "\r\n"

        # Dump ENV
        msg = msg + "\r\nEnvironment:" + "\r\n"
        for name, value in os.environ.items():
            msg = msg + "%-10s = %s\r\n" % (name, value)

        real_msg = MIMEText(msg, _charset='utf-8')

        real_msg['Subject'] = self.buffer[0]
        real_msg['To'] = ','.join(self.toaddrs)
        real_msg['From'] = self.fromaddr

        return real_msg

    def flush(self):
        if len(self.buffer) > 0:
            try:
                port = self.mailport
                if not port:
                    port = smtplib.SMTP_PORT

                smtp = smtplib.SMTP(self.mailhost, port)
                msg = self.generate_mail()

                smtp.sendmail(self.fromaddr, self.toaddrs, msg.__str__())
                smtp.quit()
            except Exception as exception:
                self.handleError(None)  # no particular record

        self.buffer = []
        self.allbuffer = []
