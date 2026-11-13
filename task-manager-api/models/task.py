from sqlalchemy import func
from sqlalchemy.orm import joinedload

from config.settings import CLOSED_STATUSES
from database import db
from utils.time import utcnow


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='pending')
    priority = db.Column(db.Integer, default=3)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', backref='tasks')
    category = db.relationship('Category', backref='tasks')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'tags': self.tags.split(',') if self.tags else [],
        }

    def is_overdue(self, now=None):
        now = now or utcnow()
        return bool(self.due_date and self.due_date < now and self.status not in CLOSED_STATUSES)

    @classmethod
    def find_by_id(cls, task_id):
        return db.session.get(cls, task_id)

    @classmethod
    def find_all_with_relations(cls):
        return cls.query.options(joinedload(cls.user), joinedload(cls.category)).all()

    @classmethod
    def search(cls, query=None, status=None, priority=None, user_id=None):
        q = cls.query
        if query:
            q = q.filter(db.or_(cls.title.like(f'%{query}%'), cls.description.like(f'%{query}%')))
        if status:
            q = q.filter(cls.status == status)
        if priority:
            q = q.filter(cls.priority == priority)
        if user_id:
            q = q.filter(cls.user_id == user_id)
        return q.all()

    @classmethod
    def count_by_status(cls):
        rows = db.session.query(cls.status, func.count(cls.id)).group_by(cls.status).all()
        return dict(rows)

    @classmethod
    def count_by_priority(cls):
        rows = db.session.query(cls.priority, func.count(cls.id)).group_by(cls.priority).all()
        return dict(rows)

    @classmethod
    def find_overdue(cls, now=None):
        now = now or utcnow()
        return cls.query.filter(
            cls.due_date.isnot(None),
            cls.due_date < now,
            cls.status.notin_(CLOSED_STATUSES),
        ).all()

    @classmethod
    def count_by_user(cls):
        rows = db.session.query(cls.user_id, func.count(cls.id)).group_by(cls.user_id).all()
        return dict(rows)

    @classmethod
    def count_completed_by_user(cls):
        rows = (
            db.session.query(cls.user_id, func.count(cls.id))
            .filter(cls.status == 'done')
            .group_by(cls.user_id)
            .all()
        )
        return dict(rows)
