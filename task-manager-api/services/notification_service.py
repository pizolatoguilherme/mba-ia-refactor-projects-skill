import logging
import smtplib

from utils.time import utcnow

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, smtp_host, smtp_port, smtp_user, smtp_password):
        self.notifications = []
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password

    def send_email(self, to, subject, body):
        if not self.smtp_user or not self.smtp_password:
            logger.warning('SMTP não configurado; email para %s não enviado', to)
            return False
        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=5)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            message = f"Subject: {subject}\n\n{body}"
            server.sendmail(self.smtp_user, to, message)
            server.quit()
            logger.info('Email enviado para %s', to)
            return True
        except Exception:
            logger.exception('Erro ao enviar email para %s', to)
            return False

    def notify_task_assigned(self, user, task):
        subject = f"Nova task atribuída: {task.title}"
        body = (
            f"Olá {user.name},\n\nA task '{task.title}' foi atribuída a você.\n\n"
            f"Prioridade: {task.priority}\nStatus: {task.status}"
        )
        self.send_email(user.email, subject, body)
        self.notifications.append({
            'type': 'task_assigned',
            'user_id': user.id,
            'task_id': task.id,
            'timestamp': utcnow(),
        })

    def notify_task_overdue(self, user, task):
        subject = f"Task atrasada: {task.title}"
        body = f"Olá {user.name},\n\nA task '{task.title}' está atrasada!\n\nData limite: {task.due_date}"
        self.send_email(user.email, subject, body)

    def get_notifications(self, user_id):
        return [n for n in self.notifications if n['user_id'] == user_id]
