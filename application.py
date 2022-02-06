from flask import Flask, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from web3 import Web3
from apscheduler.schedulers.background import BackgroundScheduler

import atexit
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
db = SQLAlchemy(app)
db.create_all()
CORS(app)
scheduler = BackgroundScheduler()

main_net = 'https://rpc.s0.t.hmny.io'
test_net = "https://api.s0.b.hmny.io"
w3 = Web3(Web3.HTTPProvider(test_net))

TreeJson = open("abi/Tree.json")
TreeABI = json.load(TreeJson)["abi"]
TreeAddress = json.load(TreeJson)["networks"]["2"]["address"]
TreeContract = w3.eth.contract(address=TreeAddress, abi=TreeABI)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(42), unique=True, nullable=False)

    def __repr__(self):
        return '<User %r>' % self.address



def allAddresses(): 
    addresses=[]
    for user in User.query.all():
        addresses.append(user.address)
    return addresses

def checkTreesOnDB(address):
    pass
    
def checkAddress(address):
    #Checkeos de que la address sea valida
    if len(address) != 42:
        return False
    else:
        return True

def checkUser(address):
    exists = db.session.query(User.id).filter_by(address=address).first() is not None
    if exists == False:
        return "Address not in DB"
        #newUser = User(address=address)
        #db.session.add(newUser)
        #db.session.commit()
    else:
        trees = checkTreesOnDB(address)
    return trees

def treesOf(address):
    if checkAddress(address) == False:
        return "Non Valid Address"
    return checkUser(address)

def handle_event(event):
    print(event)

def log_loop():
    event_filter = TreeContract.events.Transfer.createFilter(fromBlock="latest", argument_filters={'arg1':10})
    for event in event_filter.get_new_entries():
        handle_event(event)

scheduler.add_job(func=log_loop, trigger="interval", seconds=5)
scheduler.start()

@app.route("/status", methods=['GET'])
async def getStatus():
    return {"Success": "API Working"}

@app.route("/treesOf/<address>", methods=['GET'])
async def getTreesOf(address):
    return treesOf(address)

atexit.register(lambda: scheduler.shutdown())
app.run(host='0.0.0.0')