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

MarketplaceJson = json.load(open("abi/Marketplace.json"))
MarketplaceABI = MarketplaceJson["abi"]
MarketplaceAddress = MarketplaceJson["networks"]["2"]["address"]
MarketplaceContract = w3.eth.contract(address=MarketplaceAddress, abi=MarketplaceABI)

class Tree(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner = db.Column(db.String(42), unique=False, nullable=False)

    def __repr__(self):
        return '<Tree %r>' % self.id

class Offer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner = db.Column(db.String(42), unique=False, nullable=False)
    itemId = db.Column(db.Integer)
    originalAmount = db.Column(db.Integer)
    currentAmount = db.Column(db.Integer)
    price = db.Column(db.Integer)
    status = db.Column(db.String(10), unique=False, nullable=False)


    def __repr__(self):
        return '<Offer %r>' % self.id


db.create_all()



def addTreeData(treeId, newOwner):
    newTree = Tree(id=treeId, owner=newOwner)
    db.session.add(newTree)
    db.session.commit()

def addOfferData(offerId, owner, itemId, originalAmount, currentAmount, price, status):
    newOffer = Offer(id=offerId, owner=owner, itemId=itemId, originalAmount=originalAmount, currentAmount=currentAmount ,price=price, status=status)
    db.session.add(newOffer)
    db.session.commit()

def updateTreeData(treeId, newOwner):
    Tree.query.filter_by(id=treeId).update(dict(owner=newOwner))
    db.session.commit()

def updateOfferData(offerId, newOwner, newItemId, NewOriginalAmount, NewCurrentAmount, newPrice, newStatus):
    Offer.query.filter_by(id=offerId).update(dict(owner=newOwner))
    Offer.query.filter_by(id=offerId).update(dict(itemId=newItemId))
    Offer.query.filter_by(id=offerId).update(dict(originalAmount=NewOriginalAmount))
    Offer.query.filter_by(id=offerId).update(dict(currentAmount=NewCurrentAmount))
    Offer.query.filter_by(id=offerId).update(dict(price=newPrice))
    Offer.query.filter_by(id=offerId).update(dict(status=newStatus))
    db.session.commit()

def allTreesOnDB():
    trees=[]
    for tree in Tree.query.all():
        trees.append([tree.id, tree.owner])
    return trees

def allOffersOnDB():
    offers=[]
    for offer in Offer.query.all():
        offers.append([offer.id, offer.owner])
    return offers

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

def getOffersOf(address):
    result = {}
    if checkAddress(address) == False:
        return "Non Valid Address"
    offers = db.session.query(Offer.id, Offer.owner, Offer.itemId, Offer.originalAmount, Offer.currentAmount, Offer.price, Offer.status).filter_by(owner=address)
    for offer in offers:
        result[offer[0]] = {"owner": offer[1], "itemId": offer[2], "originalAmount": offer[3], "currentAmount": offer[4], "price": offer[5], "status": offer[6]}
    return result
    
def getOpenOffers():
    result = {}
    offers = db.session.query(Offer.id, Offer.owner, Offer.itemId, Offer.originalAmount, Offer.currentAmount, Offer.price, Offer.status).filter_by(status="Open")
    for offer in offers:
        result[offer[0]] = {"owner": offer[1], "itemId": offer[2], "originalAmount": offer[3], "currentAmount": offer[4], "price": offer[5], "status": offer[6]}
    return result

def updateAllTreesData():
    treesQuantity = TreeContract.functions.treesQuantity().call()
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

def updateAllOffersData():
    offersQuantity = MarketplaceContract.functions.offersQuantity().call()
    for i in range(offersQuantity):
        try:
            newOfferOwner = MarketplaceContract.functions.offerOwner(i).call()
            newOfferItemId = MarketplaceContract.functions.offerItemId(i).call()
            newOfferOriginalAmount = MarketplaceContract.functions.offerOriginalAmount(i).call()
            newOfferCurrentAmount = MarketplaceContract.functions.offerCurrentAmount(i).call()
            newOfferPrice = MarketplaceContract.functions.offerPrice(i).call()
            newOfferStatus = MarketplaceContract.functions.offerStatus(i).call()
        except:
            break
        exists = db.session.query(Offer.id).filter_by(id=i).first() is not None
        if exists == False:
            addOfferData(i, newOfferOwner, newOfferItemId, newOfferOriginalAmount, newOfferCurrentAmount, newOfferPrice, newOfferStatus)
        else:
            updateOfferData(i, newOfferOwner, newOfferItemId, newOfferOriginalAmount, newOfferCurrentAmount, newOfferPrice, newOfferStatus)

def handle_transfer(event):
    print(event)
    treeId = event["args"]["tokenId"]
    newOwner = event["args"]["to"]
    exists = db.session.query(Tree.id).filter_by(id=treeId).first() is not None
    if exists == False:
        addTreeData(treeId, newOwner)
    else:
        updateTreeData(treeId, newOwner)
    print("event Handled, TreeId: ",treeId)
        
def transferEvent():
    latestBlock = w3.eth.block_number
    #print(latestBlock)
    event_filter = TreeContract.events.Transfer.createFilter(fromBlock=latestBlock)
    for event in event_filter.get_all_entries():
        handle_transfer(event)

@app.route("/status", methods=['GET'])
async def getStatus():
    return {"Success": "API Working"}

@app.route("/updateTrees", methods=['GET'])
async def updatetreeData():
    updateAllTreesData()
    return {"Success": "Data updated"}

@app.route("/updateOffers", methods=['GET'])
async def updateofferData():
    updateAllOffersData()
    return {"Success": "Data updated"}

@app.route("/treesOf/<address>", methods=['GET'])
async def treesOf(address):
    return getTreesOf(address)

@app.route("/offersOf/<address>", methods=['GET'])
async def offersOf(address):
    return getOffersOf(address)

@app.route("/openOffers", methods=['GET'])
async def openOffers():
    return getOpenOffers()

scheduler.add_job(func=transferEvent, trigger="interval", seconds=2)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())
app.run(host='0.0.0.0')