from .. import db


class User(db.Model):
    __tablename__ = 'users'

    id_user          = db.Column(db.Integer, primary_key=True)
    first_name       = db.Column(db.String(100))
    last_name        = db.Column(db.String(100))
    email            = db.Column(db.String(200), unique=True, nullable=False)
    password         = db.Column(db.String(200))          # legacy hex hash
    password_hash    = db.Column(db.String(200))          # bcrypt hash (app users)
    phone            = db.Column(db.String(50))
    gender           = db.Column(db.String(10))
    role             = db.Column(db.String(50))
    created_at       = db.Column(db.Date)
    status           = db.Column(db.String(20))
    username         = db.Column(db.String(50), unique=True)
    department       = db.Column(db.String(100))
    avatar_initials  = db.Column(db.String(5))

    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()
