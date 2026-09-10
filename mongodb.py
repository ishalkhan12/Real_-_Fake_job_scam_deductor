from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

db = client["jobshield"]

users = db["users"]
jobs = db["jobs"]
reports = db["reports"]


suspicious_keywords = [
    "registration fee",
    "payment required",
    "earn instantly",
    "quick money",
    "guaranteed income",
    "investment required",
    "pay first",
    "unlimited income",
    "become rich quickly",
    "double your money"
]