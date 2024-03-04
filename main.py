from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase
from pytube import YouTube
import os

# You Tube API
current_directory = os.path.dirname(os.path.abspath(__file__))
directory = os.path.join(current_directory, 'static')

def download_audio(url, output_path):
    try:
        # Create a YouTube object
        yt = YouTube(url)

        # Get the highest resolution audio stream
        audio_stream = yt.streams.filter(only_audio=True).first()

        # Download the audio stream to the specified output path
        audio_stream.download(output_path)

        print("Download successful!")

    except Exception as e:
        print(f"Error: {e}")

# Example usage
output_directory = directory


app = Flask(__name__)
app.config["SECRET_KEY"] = "hhhhh"
socketio = SocketIO(app)


rooms = {}
global firstRound
firstRound = True

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        if code not in rooms:
            break
    return code


@app.route("/", methods=["POST", "GET"])
def home():
    print("Test")
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error = "Please enter a name", code=code, name=name)
        if join != False and not code:
            return render_template("home.html", error = "Please enter a room code", code = code, name=name)
        
        room = code
        if create != False:
            room = generate_unique_code(4)

            #get the song list
            files_in_directory = os.listdir(directory)
            if "Weihnachten.jpg" in files_in_directory:
                files_in_directory.remove("Weihnachten.jpg")
            files_in_directory.remove("css")

            rooms[room] = {"members":0,"message": [],"points":[],"names":[], "songs":files_in_directory}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist",code=code, name=name)

        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

   
    return render_template("home.html")

#Music Lobby  
@app.route('/songs')
def show_music():
    files_in_directory = os.listdir(directory)
    if "Weihnachten.jpg" in files_in_directory:
        files_in_directory.remove("Weihnachten.jpg")
    files_in_directory.remove("css")
    return render_template('showsong.html', songs = files_in_directory)

@app.route('/music', methods = ["GET", "POST"])
def add_music():
    if request.method == "POST":
        url = request.form["song_url"]
        download_audio(url, output_directory)
    return render_template('addsong.html')

@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    print(session.get("name"))
    if session.get("name") == "admin":
        #send({"name": "$", "message": "Der RundenAdmin ist im Game"}, to=room)
        return render_template("roomTest.html", code=room, admin=True)
    else:
        
        return render_template("roomTest.html", code=room)
    
@socketio.on("newRound")
def newRound():
    room = session.get("room")
    global firstRound
    firstRound = False
    print(rooms[room]["songs"])
    print(len(rooms[room]["songs"]))
    if len(rooms[room]["songs"]) <=0:
        punkte = rooms[room]["points"]
        send({"name": "$", "message": f"Runde ist zuende, das sind die Punkte: {punkte} "}, to=room)
        return
    
    Zufall = random.randint(0,len(rooms[room]["songs"])-1)
    print(Zufall)
    music_name = rooms[room]["songs"].pop(Zufall)
    music_url = url_for('static', filename= music_name)
    socketio.emit('newRound', music_url, to=room)
    send({"name": "$", "message": f"Folgendes Lied wird gespielt: {music_url}"}, to=request.sid)

@socketio.on("givePoints")
def givePoints(data):
    room = session.get("room")
    if room not in rooms or firstRound == True:
        send({"name": "$", "message": "Starte erst eine Neue Runde"}, to=request.sid)
        return
    
    if data["data"] not in rooms[room]["names"]:
        send({"name": "$", "message": "Dieser Spieler ist nicht in der Lobby"}, to=request.sid)
        return
    
    #give 10 points to the player that is in the data["data"] variable
    name = data["data"]
    for player in rooms[room]["points"]:
        if player[0] == name:
            player[1] +=10
            send({"name": "$", "message": f"{name} hat 10 Punkte bekommen"}, to=room)
            punkte=rooms[room]["points"]
            send({"name": "$", "message": f"neue Punktanzahl: {punkte}"}, to=room)
            return
        

    
@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return
    content = {
        "name": session.get("name"),
        "message": data["data"]

    }
    send(content, to=room)
    rooms[room]["message"].append(content)


@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] +=1
    if name != "admin":
        rooms[room]["points"].append([name,0])
        rooms[room]["names"].append(name)
        
    print(f"{name} joined the room {room}")
    

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -=1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    
    send({"name": name, "message": "has left the room"}, to=room)
if __name__ == "__main__":
    socketio.run(app,port = 8080, debug = True)