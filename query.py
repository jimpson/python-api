from flask_sqlalchemy import SQLAlchemy
print ("one", "two")[0]
db = SQLAlchemy()

class appQuery:
    ROOM_NAME = "SELECT name FROM rooms WHERE id = :x"

    ROOM_TERM = """SELECT DATE(temperatures.date) as reading_date,
    AVG(temperatures.temperature)
    FROM temperatures
    WHERE temperatures.room_id = :x
    GROUP BY reading_date
    HAVING DATE(temperatures.date) > (SELECT MAX(DATE(temperatures.date))-:y FROM temperatures);"""
    
class Rooms(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

class Temperatures(db.Model):
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), primary_key=True)
    temperature = db.Column(db.Float)
    date = db.Column(db.DateTime)
    room = db.relationship('Rooms', backref='temperatures')