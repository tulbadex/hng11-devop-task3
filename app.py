from flask import Flask, request, send_file, abort, Response
from celery import Celery, Task
from flask_mail import Mail, Message
import logging
from datetime import datetime
import os
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
import subprocess
from logging.handlers import RotatingFileHandler

load_dotenv()

app = Flask(__name__)

# Configuration for Flask-Mail
app.config['MAIL_SERVER'] = os.getenv("SMTP_MAIL_SERVER")
app.config['MAIL_PORT'] = int(os.getenv("SMTP_MAIL_PORT"))
app.config['MAIL_USERNAME'] = os.getenv("SMTP_MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("SMTP_MAIL_PASSWORD")
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)

# Celery configuration
app.config['CELERY_BROKER_URL'] = os.getenv("RABBITMQ_ADDRESS")
app.config['CELERY_RESULT_BACKEND'] = os.getenv("CELERY_RESULT_BACKEND")

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)
    
log_dir = '/var/log/messaging_system.log'
os.makedirs(os.path.dirname(log_dir), exist_ok=True)

# Ensure the log file exists
if not os.path.exists(log_dir):
    with open(log_dir, 'w') as f:
        pass

# # Logger configuration
logging.basicConfig(filename=log_dir,level=logging.INFO)
handler = RotatingFileHandler(log_dir, maxBytes=1024*1024, backupCount=5)
handler.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# Apply the ProxyFix middleware
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

@celery.task
def send_async_email(recipient):
    msg = Message(
        subject='Welcome to Messaging System',
        sender='tulbadex@gmail.com',
        recipients=[recipient]
    )
    
    # Extract the user's name from the email if possible
    user_name = recipient.split('@')[0].capitalize()

    msg.body = f"""
    Hi {user_name},

    Welcome to the Messaging System!

    We are thrilled to have you here. This application demonstrates how to build a messaging system with RabbitMQ, Celery, and Python. 
    Using Celery, you can send tasks asynchronously, ensuring your application remains responsive.

    Thank you for joining us on this journey. We hope you find this application helpful and informative.

    Best regards,
    The Messaging System Team
    """

    with app.app_context():
        mail.send(msg)

def log_with_sudo(log_message):
    try:
        # Use subprocess to call sudo tee without password prompt
        process = subprocess.Popen(['sudo', 'tee', '-a', log_dir], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.communicate(input=f"{log_message}\n".encode())
    except Exception as e:
        print(f"Failed to write log: {e}")

@app.route('/')
def messaging():
    sendmail = request.args.get('sendmail')
    # talktome = request.args.get('talktome')
    
    if sendmail:
        recipient = sendmail.replace('mailto:', '') if sendmail.startswith('mailto:') else sendmail
        send_async_email.apply_async(args=[recipient])
        app.logger.info(f"Email queued for {recipient}")
        return f"Email has been queued for {recipient}"
    
    if 'talktome' in request.args:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        app.logger.info(f'Current time logged: {current_time}')
        # log_with_sudo(f'Current time logged: {current_time}')
        return f'Current time logged: {current_time}'
    
    return 'No action taken'

@app.route('/log')
def get_logs():
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    """ if os.path.exists(log_dir):
        with open(log_dir, 'r') as file:
            logs = file.read()
        logging.info(f'Logged access at: {current_time}')
        # return Response(logs, mimetype='text/plain')
        return send_file(logs, mimetype='text/plain')
    else:
        error_msg = f'Logged file not accessible at: {current_time}'
        logging.error(error_msg)
        # return error_msg, 404
        return abort(404, description=error_msg) """
    try:
        with open(log_dir, 'r') as f:
            log_content = f.read()
        app.logger.info(f"Log file accessed at {datetime.now()}")
        return send_file(log_content, mimetype='text/plain')
    except Exception as e:
        error_msg = f'Logged file not accessible at: {current_time}'
        app.logger.error(error_msg)
        return error_msg, 404
    

if __name__ == '__main__':
    app.run(debug=True, port=5000)