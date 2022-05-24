from flask import Flask, request, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_api import status
import jwt
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ukol.sqlite'
SECRET_KEY = "kocka"
JWT_SECRET = "pes"


db = SQLAlchemy(app)

def token_required(f):
    """Autorizační middleware, definovaný pomocí dekorátoru."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("x-access-token", None)
        if not token:
            return jsonify({"message": "Autorizacni token nenalezen!"}), 401

        try:
            jwt.decode(token, JWT_SECRET, algorithms="HS256")
        except jwt.DecodeError:
            return jsonify({"message": "Autorizacni token neni validni!"}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Autorizacni token expiroval!"}), 401

        return f(*args, **kwargs)

    return decorated

@app.route("/auth", methods=["GET"])
def authorize():
    """Tento endpoint vygeneruje JWT token, používaný pro práci."""
    
    user_key = request.headers.get('x-user-key', None)
    
    if user_key == SECRET_KEY:
        payload = {
            "user": "api",
            "exp": datetime.now() + timedelta(minutes=60),
        }
        encoded = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

        return jsonify({"token": encoded})
    else:
        payload = {"message": "Klic neni spravny."}
        return jsonify(payload), 403

class Ukol(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jmeno = db.Column(db.String(50))
    popis = db.Column(db.Text)
    splneno = db.Column(db.Boolean, default=True)

"""Vytvoření nového úkolu a jeho zápis do databáze."""
@app.route('/ukol', methods=['POST'])
@token_required
def vytvor_ukol():
    data = request.get_json()

    novy_ukol = Ukol(jmeno=data['jmeno'], popis=data['popis'], splneno=False)

    db.session.add(novy_ukol)
    db.session.commit()

    return make_response(jsonify("Novy ukol byl vytvoren, smele do jeho vykonani!"), 200)

"""Výpis úkolů vložených do databáze, filtrace dle stavu."""
@app.route('/', methods=['GET'])
def vypis_ukoly():
    filtry = {
        "VSE": "vse",
        "SPLNENO": "splneno",
        "NESPLNENO": "nesplneno"
    }

    filtr = request.args.get('filtr', None)

    if filtr == filtry["VSE"]:
        query = Ukol.query.all()

    elif filtr == filtry["SPLNENO"]:
        query = Ukol.query.filter_by(splneno=True).all()

    elif filtr == filtry["NESPLNENO"]:
        query = Ukol.query.filter_by(splneno=False).all()

    else:
        return make_response(jsonify("Zadny takovy filtr neexistuje! Vyber z nasledujcich [vse, splneno, nespleno]"), 404)

    vypis = []

    for ukol in query:
        vypis_ukol = {}
        vypis_ukol['id'] = ukol.id
        vypis_ukol['jmeno'] = ukol.jmeno
        vypis_ukol['popis'] = ukol.popis
        vypis_ukol['splneno'] = ukol.splneno
        vypis.append(vypis_ukol)

    vysledek = jsonify(
        {
            "Polozky":
             vypis
        }
    )

    return vysledek, status.HTTP_201_CREATED

"""Endpoint pro úpravu již vložených úkolů, změna jejich názvu, popisu, stavu."""
@app.route('/ukol/<id>', methods=['PUT'])
@token_required
def uprav_ukol(id):
    data = request.get_json()

    jmeno = data.get('jmeno', None)
    popis = data.get('popis', None)
    splneno = data.get('splneno', None)

    ukol = Ukol.query.filter_by(id=id).first()

    if not ukol:
        return make_response(jsonify("Ukol se zvolenym ID nebyl nalezen, takze pravdepodobne neexistuje."), 404)

    ukol.jmeno = jmeno
    ukol.popis = popis
    ukol.splneno = splneno

    db.session.commit()

    return make_response(jsonify("Zvoleny ukol byl upraven!"), 200)

"""Endpoint pro vymazání úkolu."""
@app.route("/ukol/<id>", methods=["DELETE"])
@token_required
def vymaz_ukol(id):
    ukol = Ukol.query.filter_by(id=id).first()

    if not ukol:
        return make_response(jsonify("Ukol se zvolenym ID nebyl nalezen, takze nebylo mozne ho smazat."), 404)

    db.session.delete(ukol)
    db.session.commit()

    return make_response(jsonify("Ukol byl uspesne smazan."), 200)

if __name__ == '__main__':
    app.run(debug=True, port="80", host="0.0.0.0")