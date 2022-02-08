from flask import Flask, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from web3 import Web3
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

import atexit
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tree.db'
db = SQLAlchemy(app)
CORS(app)
scheduler = BackgroundScheduler()

main_net = 'https://rpc.s0.t.hmny.io'
test_net = "https://api.s0.b.hmny.io"
w3 = Web3(Web3.HTTPProvider(test_net))

TreeJson = json.load(open("abi/Tree.json"))
TreeABI = TreeJson["abi"]
TreeAddress = TreeJson["networks"]["2"]["address"]
TreeContract = w3.eth.contract(address=TreeAddress, abi=TreeABI)

class Tree(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner = db.Column(db.String(42), unique=False, nullable=False)

    def __repr__(self):
        return '<Tree %r>' % self.id
db.create_all()



def addTreeData(treeId, newOwner):
    newTree = Tree(id=treeId, owner=newOwner)
    db.session.add(newTree)
    db.session.commit()

def updateTreeData(treeId, newOwner):
    Tree.query.filter_by(id=treeId).update(dict(owner=newOwner))
    db.session.commit()

def allTreesOnDB():
    trees=[]
    for tree in Tree.query.all():
        trees.append([tree.id, tree.owner])
    return trees

def checkAddress(address):
    #Checkeos de que la address sea valida
    if len(address) != 42:
        return False
    else:
        return True

def getTreesOf(address):
    result = {}
    if checkAddress(address) == False:
        return "Non Valid Address"
    trees = db.session.query(Tree.id).filter_by(owner=address)
    for tree in trees:
        result[tree[0]] = address
    return result
    

def updateAllTreesData():
    #treesQuantity = TreeContract.functions.treesQuantity().call()
    treesQuantity=100
    for i in range(treesQuantity):
        try:
            newOwner = TreeContract.functions.ownerOf(i).call()
        except:
            break
        exists = db.session.query(Tree.id).filter_by(id=i).first() is not None
        if exists == False:
            addTreeData(i, newOwner)
        else:
            currentOwner = db.session.query(Tree.owner).filter_by(id=i).first()[0]
            if newOwner != currentOwner:
                updateTreeData(i, newOwner)

def handle_event(event):
    print(event)
    treeId = event["args"]["tokenId"]
    newOwner = event["args"]["to"]
    exists = db.session.query(Tree.id).filter_by(id=treeId).first() is not None
    if exists == False:
        addTreeData(treeId, newOwner)
    else:
        updateTreeData(treeId, newOwner)
        
def transferEvent():
    latestBlock = w3.eth.block_number
    #print(latestBlock)
    event_filter = TreeContract.events.Transfer.createFilter(fromBlock=latestBlock)
    for event in event_filter.get_all_entries():
        handle_event(event)

@app.route("/status", methods=['GET'])
async def getStatus():
    return {"Success": "API Working"}

@app.route("/update", methods=['GET'])
async def updateData():
    updateAllTreesData()
    return {"Success": "Data updated"}

@app.route("/treesOf/<address>", methods=['GET'])
async def treesOf(address):
    return getTreesOf(address)

scheduler.add_job(func=transferEvent, trigger="interval", seconds=2)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())
app.run(host='0.0.0.0')