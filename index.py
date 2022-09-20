from crypt import methods
import json
import os
from dotenv import load_dotenv
from datetime import datetime
from flask import Flask, request
from flask_pymongo import PyMongo

load_dotenv()

app = Flask(__name__)
app.config["MONGO_URI"] = os.getenv('MONGO_URI')
mongo = PyMongo(app)


@app.route("/")
def hello():
    books = list(mongo.db.books.find({"category": "Fiction"}))
    print(books)
    return json.dumps(books, default=str)


@app.route("/books/name")
def findBook():
    req = request.get_json()
    bookName = req["name"]
    books = list(mongo.db.books.find({"name": {"$regex": f"(?i){bookName}"}}))
    return json.dumps(books, default=str)


@app.route("/books/name", methods=["DELETE"])
def deleteBook():
    req = request.get_json()
    bookName = req["name"]
    book = mongo.db.books.find_one({"name": bookName})

    if book == None:
        return json.dumps({"error": "Book not found"}, default=str)

    id = book["_id"]

    mongo.db.books.delete_one({"_id": id})

    return json.dumps({"success": "Book deleted succesfully"}, default=str)


@app.route("/books/price")
def returnRange():
    req = request.get_json()
    lower = int(req["lower"])
    higher = int(req["higher"])
    books = list(mongo.db.books.find({"rent": {"$gt": lower, "$lt": higher}}))
    return json.dumps(books, default=str)


@app.route("/books/find")
def findBooks():
    req = request.get_json()
    bookName = req["name"]
    category = req["category"]
    lower = int(req["lower"])
    higher = int(req["higher"])

    books = list(mongo.db.books.find({"name": {"$regex": f"(?i){bookName}"},
                                      "category": category,
                                      "rent": {"$gt": lower, "$lt": higher
                                               }}))
    print(books)
    return json.dumps(books, default=str)


@app.route("/books/issue", methods=["POST"])
def issueBook():
    req = request.get_json()
    bookName = req["bookName"]
    issuer = req["issuer"]
    date = datetime.strptime(req["date"], "%Y-%m-%dT%H:%M:%SZ")

    book = mongo.db.books.find_one({"name": {"$regex": f"(?i){bookName}"}})
    bookId = book["_id"]

    transaction = mongo.db.transactions.insert_one({
        "book": bookId,
        "issuer": issuer,
        "transactionType": "issue",
        "date": date,
        "currentlyIssued": True
    })

    return json.dumps({"_id": transaction.inserted_id}, default=str)


@app.route("/books/return", methods=["POST"])
def returnBook():
    req = request.get_json()
    bookName = req["bookName"]
    issuer = req["issuer"]
    date = datetime.strptime(req["date"], "%Y-%m-%dT%H:%M:%SZ")

    book = mongo.db.books.find_one({"name": {"$regex": f"(?i){bookName}"}})
    bookId = book["_id"]
    rent = int(book["rent"])

    issue = mongo.db.transactions.find_one_and_update({
        "book": bookId,
        "issuer": issuer,
        "currentlyIssued": True
    }, {"$set": {"currentlyIssued": False}})
    issueDate = issue["date"]
    difference = date - issueDate
    totalRent = difference.days * rent

    transaction = mongo.db.transactions.insert_one({
        "book": bookId,
        "issuer": issuer,
        "transactionType": "return",
        "date": date,
        "rentDue": totalRent,
    })

    return json.dumps({"_id": transaction.inserted_id}, default=str)


@app.route("/books/rent")
def calculateRent():
    req = request.get_json()
    bookName = req["name"]
    books = mongo.db.books.find_one({"name": {"$regex": f"(?i){bookName}"}})
    bookId = books["_id"]

    transactions = list(mongo.db.transactions.find(
        {"book": bookId, "transactionType": "return"}))
    totalRent = 0
    for transaction in transactions:
        totalRent += int(transaction["rentDue"])

    return json.dumps({"totalRent": totalRent}, default=str)


@app.route("/books/issuers")
def showIssuers():
    req = request.get_json()
    bookName = req["name"]

    book = mongo.db.books.find_one({"name": bookName})
    bookId = book["_id"]

    transactions = mongo.db.transactions.count_documents(
        {"book": bookId, "transactionType": "issue"})

    books = list(mongo.db.transactions.find(
        {"book": bookId, "currentlyIssued": True}))

    issuers = []
    for book in books:
        issuers.append(book["issuer"])

    return json.dumps({"issuerCount": transactions, "currentIssuers": issuers}, default=str)


@app.route("/books/info")
def showInfo():
    req = request.get_json()
    issuer = req["issuer"]

    transactions = list(mongo.db.transactions.find(
        {"issuer": {"$regex": f"(?i){issuer}"}, "transactionType": "issue"}))

    books = []

    for transaction in transactions:
        bookId = transaction["book"]
        book = mongo.db.books.find_one({"_id": bookId})
        bookName = book["name"]
        books.append(bookName)

    return json.dumps(books, default=str)


@app.route("/books/date")
def showbyDate():
    req = request.get_json()
    start = datetime.strptime(req["start"], "%Y-%m-%dT%H:%M:%SZ")
    end = datetime.strptime(req["end"], "%Y-%m-%dT%H:%M:%SZ")

    transactions = list(mongo.db.transactions.find(
        {"date": {"$gt": start, "$lt": end}}))

    data = []

    for transaction in transactions:
        bookId = transaction["book"]
        issuer = transaction["issuer"]

        book = mongo.db.books.find_one({"_id": bookId})
        bookName = book["name"]

        data.append({"book": bookName, "issuer": issuer})

    return json.dumps(data, default=str)


if __name__ == "__main__":
    app.run(debug=True)
