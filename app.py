import os
import ssl
from flask import Flask, request
from celery import Celery
from dotenv import load_dotenv
from datetime import datetime
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import stat

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Configure Celery
app.config['CELERY_BROKER_URL'] = 'amqp://localhost//'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Celery task to send email
@celery.task
def send_email(to_email):
    from_email = os.getenv('EMAIL_USER')
    from_password = os.getenv('EMAIL_PASSWORD')
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT'))

    subject = 'Official Email from Flask Application'
    body = 'This is a test email sent from the Flask application.'

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        logging.info(f'Connecting to SMTP server {smtp_server}:{smtp_port}')
       
        # Using SMTP_SSL for secure connection
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Start TLS explicitly
            server.ehlo()
            logging.info('Logging in to SMTP server')
            server.login(from_email, from_password)
            logging.info('Sending email')
            text = msg.as_string()
            server.sendmail(from_email, to_email, text)
            logging.info('Email sent successfully')
    except Exception as e:
        logging.error(f'Failed to send email: {e}')

# Flask routes
@app.route('/')
def index():
    return 'Welcome to the messaging system. Use /endpoint?sendmail=email or /endpoint?talktome.'

@app.route('/endpoint', methods=['GET'])
def endpoint():
    if 'sendmail' in request.args:
        send_email.apply_async(args=[request.args.get('sendmail')])
        return 'Email queued.'
    elif 'talktome' in request.args:
        log_path = '/var/log/messaging_system.log'
        # Ensure the log file exists and set permissions
        if not os.path.exists(log_path):
            with open(log_path, 'w') as log_file:
                log_file.write('')
            os.chmod(log_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

        with open(log_path, 'a') as log_file:
            log_file.write(f'{datetime.now()}\n')
        return 'Logged the current time.'
    else:
        return 'Invalid request.'

# Main entry point
if __name__ == '__main__':
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain('localhost.pem', 'localhost.key')
    app.run(ssl_context=ssl_context, debug=True)
