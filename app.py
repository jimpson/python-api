from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_swagger import swagger
from flask_swagger_ui import get_swaggerui_blueprint
from query import db, Rooms, Temperatures, appQuery
from sqlalchemy import func, text
import os

# Load environment variables and .env contents
load_dotenv()

app = Flask(__name__)
url = os.getenv("DATABASE_URL")
host = os.getenv("DATABASE_HOST")
user = os.getenv("DATABASE_USER")
password = os.getenv("DATABASE_PASSWORD")
port = os.getenv("DATABASE_PORT")
dbname = os.getenv("DATABASE_NAME")

# Configure environment for SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://%s:%s@%s:%s/%s" % (user, password, host, port, dbname)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)
with app.app_context():
    db.create_all()

# Setup Swagger/SwaggerUI
SWAGGER_URL = '/api/docs'
API_URL = 'http://localhost:5000/swagger'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={  
        'app_name': "Room Temperature API"
    },
)

app.register_blueprint(swaggerui_blueprint)

# Begin API routes
@app.route("/swagger")
def spec():
    swag = swagger(app)
    swag["info"]["version"] = "1.0"
    swag["info"]["title"] = "Room Temperature API"
    return jsonify(swag)

def get_room_term(room_id, term):
    terms = {"week": 7, "month": 30}
    with db.engine.connect() as con:
        name_stmt = text(appQuery.ROOM_NAME)
        name_stmt = name_stmt.bindparams(x=room_id)
        name = con.execute(name_stmt).fetchall()[0][0]
        dates_stmt = text(appQuery.ROOM_TERM)
        dates_stmt = dates_stmt.bindparams(x=room_id, y=terms[term])
        dates_temperatures = con.execute(dates_stmt).fetchall()
        data_list = []
        for row in dates_temperatures:
            data_list.append({'date': row[0].strftime('%Y-%m-%d'), 'temperature': row[1]})
    average = sum(day[1] for day in dates_temperatures) / len(dates_temperatures)
    return {
        "name": name,
        "temperatures": data_list,
        "average": round(average, 2),
    }

@app.get("/")
def home():
    """
        Hello World Endpoint
        ---
        tags:
          - example
        responses:
          200:
            description: Hello World
        """
    return "Hello, world!"

@app.post("/api/room")
def create_room():
    """
        Creates a new room
        ---
        tags:
          - rooms
        parameters:
          - in: body
            name: body
            schema:
              id: Room
              required:
                - name
              properties:
                name:
                  type: string
                  description: name for room
        responses:
          201:
            description: Room created
        """
    data = request.get_json()
    name = data["name"]
    new_room = Rooms(name=name)
    db.session.add(new_room)
    db.session.commit()
    return {"id": new_room.id, "message": f"Room: {new_room.name}"}, 201

@app.post("/api/temperature")
def add_temp():
    """
        Creates a new temperature reading
        ---
        tags:
          - temperature
        parameters:
          - in: body
            name: body
            schema:
              id: Temperature
              required:
                - room
                - temperature
              properties:
                room:
                  type: integer
                  description: room id
                temperature:
                  type: integer
                  description: temperature reading in room
        responses:
          201:
            description: Temperature reading created
        """
    data = request.get_json()
    temperature = data["temperature"]
    room_id = data["room"]
    try:
        date = datetime.strptime(data["date"], "%m-%d-%Y %H:%M:%S")
    except KeyError:
        date = datetime.now(timezone.utc)
        
    new_temperature = Temperatures(room_id=room_id, temperature=temperature, date=date)
    db.session.add(new_temperature)
    db.session.commit()
           
    return {"message": "Temperature added."}, 201

@app.get("/api/average")
def get_global_avg():
    """
        Gets a global average temperature for all rooms
        ---
        tags:
          - rooms
        responses:
          200:
            description: Returns the global average temperature for all rooms
        """
    days = db.session.query(func.count(func.distinct(Temperatures.date)).label('days')).scalar()
    average = db.session.query(func.avg(Temperatures.temperature).label('average')).scalar()

    return {"average": round(average, 2), "days": days}

@app.get("/api/room/<int:room_id>")
def get_room_all(room_id):
    """
        Gets a specific room's average temperature 
        ---
        tags:
          - rooms
        parameters:
          - in: path
            name: room_id
            description: The id of the room being queried
          - in: query
            name: term
            description: The term used for filtering. Valid values are "week" and "month"
        responses:
          200:
            description: Temperature results filtered by term, if one is supplied
        """
    term = request.args.get("term")
    if term is not None:
        return get_room_term(room_id, term)
    else:
        name = db.session.query(Rooms.name).filter(Rooms.id == room_id).scalar()
        average = db.session.query(func.avg(Temperatures.temperature)).filter(Temperatures.room_id == room_id).scalar()
        days = db.session.query(func.count(func.distinct(Temperatures.date))).filter(Temperatures.room_id == room_id).scalar()
                
        if average == None:
            average = 0
        else:
            average = round(average, 2)
        return {"name": name, "average": average, "days": days}
    
app.run()