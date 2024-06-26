from flask import Flask, render_template, request, jsonify
from flask import session, redirect, url_for
from flask_pymongo import PyMongo
from bson import ObjectId
import random
from math import pow
from flask_cors import CORS
from flask import request, redirect, url_for
import os
from flask import render_template


app = Flask(__name__)
CORS(app)
K_FACTOR = 32



# MongoDB connection string (update with your own if needed)
app.config["MONGO_URI"] = "mongodb+srv://ppgame793:CBrHkNaLAPln7GeK@hotornot.gubbic6.mongodb.net/voting_app?retryWrites=true&w=majority&appName=hotornot"
mongo = PyMongo(app)






def calculate_expected_outcome(rating_a, rating_b):
    # Calculate the expected outcome for candidate A
    return 1 / (1 + pow(10, (rating_b - rating_a) / 400))
    


@app.route('/')
def results():
    try:
        # Retrieve the top 3 candidates from the leaderboard
        top_candidates = list(mongo.db.votes.find().sort([("score", -1)]).limit(3))

        # Render the results.html template with the top 3 candidates
        return render_template('results.html', 
                               top_candidate=top_candidates[0],
                               second_candidate=top_candidates[1],
                               third_candidate=top_candidates[2])
    except Exception as e:
        return f"An error occurred: {e}"

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/add_person', methods=['POST'])
def add_person():
    # Get the name and photo file from the form
    name = request.form['name']
    photo_file = request.files['photo']

    # Save the photo to a folder (assuming 'static/images')
    photo_filename = os.path.join(app.config['static/images'], photo_file.filename)
    photo_file.save(photo_filename)

    # Add the person to the database
    mongo.db.votes.insert_one({"name": name, "count": 0, "score": 1000})

    return redirect(url_for('admin'))


def convert_to_json_compatible(data):
    if isinstance(data, ObjectId):
        return str(data)  # Convert ObjectId to string
    if isinstance(data, dict):
        return {k: convert_to_json_compatible(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convert_to_json_compatible(i) for i in data]
    return data

# Ensure initial candidates have a score of 100000
initial_votes = ["aashi airon","sanvi agrawal","nandini prasad","shrine","shreya sharma","vanshika garg","yutika sehgal","aarshiya kshatri","padmapriya sahu","kritika daga","apurva mahto","aakriti singh","aayushi singh","jhalak patel","pankhudi bajaj","mannat kaur","stuti dubey","priyali trivedi","avanika soni","mahi modi","aastha didwania","presha lamba","himanshi sahu","yukta jangde","lavisha choudhary","niyatee vijaywargiya","snigdha thakur","shreya mishra","soumyata solanki"]
for candidate in initial_votes:
    if not mongo.db.votes.find_one({"name": candidate}):
        mongo.db.votes.insert_one({"name": candidate, "count": 0, "score": 1000})
    else:
        # If the candidate exists but doesn't have a score, initialize it
        mongo.db.votes.update_one(
            {"name": candidate, "score": {"$exists": False}},
            {"$set": {"score": 1000}}
        )
  # Track the last pair to prevent repetition

# Global variable to track the last random pair
last_pair = []

@app.route('/get_random_pair', methods=['GET'])
def get_random_pair():
    global last_pair  # Declare to use the global variable
    all_candidates = list(mongo.db.votes.find())

    # Get a new random pair
    new_pair = random.sample(all_candidates, 2)

    # Regenerate until the new pair isn't the same as the last pair
    while set(candidate["_id"] for candidate in new_pair) == set(candidate["_id"] for candidate in last_pair):
        new_pair = random.sample(all_candidates, 2)

    # Store the new pair as the last pair
    last_pair = new_pair
    random_pair = new_pair

    return jsonify(convert_to_json_compatible(random_pair))


@app.route('/vote', methods=['POST'])
def vote():
    try:
        data = request.get_json()

        selected_id = data.get("selected_id")
        rejected_id = data.get("rejected_id")

        selected_candidate = mongo.db.votes.find_one({"_id": ObjectId(selected_id)})
        rejected_candidate = mongo.db.votes.find_one({"_id": ObjectId(rejected_id)})

        # Calculate expected outcomes
        expected_selected = calculate_expected_outcome(
            selected_candidate["score"], 
            rejected_candidate["score"]
        )
        expected_rejected = 1 - expected_selected  # Because one wins, other loses

        # Calculate score changes based on expected outcomes
        score_increment = K_FACTOR * (1 - expected_selected)  # Winner gets increment
        score_decrement = K_FACTOR * expected_selected  # Loser gets decrement

        mongo.db.votes.update_one(
            {"_id": ObjectId(selected_id)},
            {"$inc": {"count": 1}}
        )

        # Update the scores
        mongo.db.votes.update_one(
            {"_id": ObjectId(selected_id)},
            {"$inc": {"score": score_increment}}
        )

        mongo.db.votes.update_one(
            {"_id": ObjectId(rejected_id)},
            {"$inc": {"score": -score_decrement}}  # Decrement for rejected candidate
        )

        return jsonify({"status": "success"})

    except Exception as e:
        app.logger.error(f"Error in /vote endpoint: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500
@app.route('/disabled_will_be_back_soon')
def index():
    return render_template('index.html')

@app.route('/get_leaderboard', methods=['GET'])
def get_leaderboard():
    # Retrieve all candidates from the database
    all_candidates = list(mongo.db.votes.find())
    
    # Sort candidates by their Elo scores in descending order
    sorted_candidates = sorted(all_candidates, key=lambda x: (x["score"], x["count"]), reverse=True)

    # Move candidates with count 0 to the bottom of the leaderboard
    sorted_candidates.sort(key=lambda x: x['count'] == 0)

    # Convert to JSON-compatible format
    return jsonify(convert_to_json_compatible(sorted_candidates))


@app.route('/get_votes', methods=['GET'])
def get_votes():
    # Retrieve all documents from the "votes" collection
    votes = list(mongo.db.votes.find())
    # Convert MongoDB data to a JSON-compatible format
    votes_json = convert_to_json_compatible(votes)
    return jsonify(votes_json)

if __name__ == '__main__':
    app.run(debug=True)
