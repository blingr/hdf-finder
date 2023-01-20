from pymongo import MongoClient
from flask import Flask, request, jsonify
from flask_cors import CORS
import jsonschema
import json

app = Flask(__name__)
client = MongoClient("mongodb://localhost:27017/")
db = client["wpf"]
students_collection = db["students"]
wpf_collection = db["wpf"]

CORS(app)


def validate(data, schema):
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        print(e)


class Wpf:
    def __init__(self, name, lehrer, klassen):
        self.name = name
        self.lehrer = lehrer
        self.klassen = klassen

    def save(self):
        wpf_collection.insert_one(self)

    def to_dict(self):
        return {"Name": self.name, "Klassen": self.klassen, "Lehrer": self.lehrer}


class Schüler:
    def __init__(self, Name, Klasse, NameWPF, LehrerWPF, Besucht, Gespeichert):
        self.Name = Name
        self.Klasse = Klasse
        self.NameWPF = NameWPF
        self.LehrerWPF = LehrerWPF
        self.Besucht = Besucht
        self.Gespeichert = Gespeichert

        if wpf_collection.find_one({"Name": NameWPF}):
            wpf = wpf_collection.find_one({"Name": NameWPF})
            wpf_obj = Wpf(wpf["Name"], wpf["Lehrer"], wpf["Klassen"])
            if not wpf_obj.lehrer == LehrerWPF or not wpf_obj.klassen == Klasse or LehrerWPF not in wpf_obj.lehrer or \
                    Klasse not in wpf_obj.klassen:
                if wpf and not isinstance(wpf["Lehrer"], list):
                    result = wpf_collection.update_one(
                        {"Name": NameWPF},
                        {"$set": {"Lehrer": [wpf["Lehrer"], LehrerWPF]}}
                    )
                elif wpf and isinstance(wpf["Lehrer"], list) and LehrerWPF not in wpf["Lehrer"]:
                    result = wpf_collection.update_one(
                        {"Name": NameWPF},
                        {"$push": {"Lehrer": LehrerWPF}}
                    )
                if wpf and not isinstance(wpf["Klassen"], list):
                    result = wpf_collection.update_one(
                        {"Name": NameWPF},
                        {"$set": {"Klassen": [wpf["Klassen"], Klasse]}}
                    )
                elif wpf and isinstance(wpf["Klassen"], list) and Klasse not in wpf["Klassen"]:
                    result = wpf_collection.update_one(
                        {"Name": NameWPF},
                        {"$push": {"Klassen": Klasse}}
                    )
        else:
            wpf = Wpf(NameWPF, LehrerWPF, Klasse).to_dict()
            Wpf.save(wpf)

    def to_dict(self):
        return {"Name": self.Name, "Klassen": self.Klasse}

    def save(self):
        students_collection.insert_one(self.__dict__)

    @staticmethod
    def find_by_name(name):
        student_doc = students_collection.find_one({"Name": name})
        student_obj = Schüler(student_doc["Name"], student_doc["Klasse"], student_doc["NameWPF"],
                              student_doc["LehrerWPF"], student_doc["Besucht"], student_doc["Gespeichert"])

        return student_obj

    @staticmethod
    def find_All():
        students = students_collection.find()
        for student in students:
            # Convert the student document to a Schüler object
            student_object = Schüler(**student)
            return (
                "{student_object.Name} has chosen class {student_object.Erstwahl.Klasse} with teacher {student_object.Erstwahl.Lehrer}")

    @staticmethod
    def update(name, new_schüler):
        # Update the Schüler object in the MongoDB collection
        update_result = students_collection.update_one({"Name": name}, {"$set": new_schüler})
        if update_result.modified_count == 1:
            return True
        else:
            return False

    @staticmethod
    def find_students_by_class(klasse):
        students_by_class = students_collection.find({"Klasse": klasse})

        return students_by_class

    @staticmethod
    def delete(name):
        # Delete the Schüler object from the MongoDB collection
        delete_result = students_collection.delete_one({"Name": name})
        if delete_result.deleted_count == 1:
            return True
        else:
            return False


@app.route("/", methods=["GET"])
def get_students():
    students = students_collection.find()
    students_list = []
    for student in students:
        student_doc = students_collection.find_one({"Name": student["Name"]})
        student_object = Schüler(student["Name"], student_doc["Klasse"], student_doc["NameWPF"],
                                 student_doc["LehrerWPF"], student_doc["Besucht"], student_doc["Gespeichert"])
        wpf_doc = wpf_collection.find_one({"Name": student_object.NameWPF})
        wpf_obj = Wpf(wpf_doc["Name"], wpf_doc["Lehrer"], wpf_doc["Klassen"])
        students_list.append(
            {
                "Name": student_object.Name,
                "Klasse": student_object.Klasse,
                "wpf": wpf_obj.__dict__,
                "Besucht": student_object.Besucht,
                "Gespeichert": student_object.Gespeichert,
            }
        )
    return jsonify(students_list)


@app.route("/students_class/<class_name>", methods=["GET"])
def get_students_by_class(class_name):
    students_list = Schüler.find_students_by_class(class_name)
    students_list2 = []
    for student in students_list:
        student_object = Schüler(student["Name"], student["Klasse"], student["NameWPF"],
                                 student["LehrerWPF"], student["Besucht"], student["Gespeichert"])
        wpf_doc = wpf_collection.find_one({"Name": student_object.NameWPF})
        wpf_obj = Wpf(wpf_doc["Name"], wpf_doc["Lehrer"], wpf_doc["Klassen"])
        print(wpf_obj);
        students_list2.append(
            {
                "Name": student_object.Name,
                "Klasse": student_object.Klasse,
                "wpf": wpf_obj.__dict__,
                "Besucht": student_object.Besucht,
                "Gespeichert": student_object.Gespeichert,
            }
        )
    return jsonify(students_list2)


@app.route("/students", methods=["POST"])
def add_student():
    name = request.json["Name"]
    Klasse = request.json["Klasse"]
    NameWPF = request.json["wpf_name"]
    LehrerWPF = request.json["wpf_lehrer"]
    Besucht = request.json["Besucht"]
    Gespeichert = request.json["Gespeichert"]

    if not name or not Klasse or not NameWPF or not LehrerWPF:
        return {"message": "name, Klasse, NameWPF or LehrerWPF is empty"}
    else:
        new_student = Schüler(name, Klasse, NameWPF, LehrerWPF, Besucht, Gespeichert)
        new_student.save()
        return {"message": "Student added successfully."}


@app.route("/students/<name>", methods=["GET"])
def get_student(name):
    student = Schüler.find_by_name(name)
    if student:
        wpf_doc = wpf_collection.find_one({"Name": student.NameWPF})
        wpf_obj = Wpf(wpf_doc["Name"], wpf_doc["Lehrer"], wpf_doc["Klassen"])
        return {
            "name": student.Name,
            "class": student.Klasse,
            "wpf": wpf_obj.__dict__,
            "attended": student.Besucht,
            "saved": student.Gespeichert
        }
    else:
        return {"message": "Student not found."}, 404


# deletes first object with the given name-definitely improvable
@app.route('/students/<string:name>', methods=['DELETE'])
def delete_student(name):
    print(name)
    if request.method == 'DELETE':
        Schüler.delete(name)
        return 'Deletion was a success', 204
    else:
        return 'you are not even trying', 405


@app.route("/students/<name>", methods=["PUT"])
def update_student(name):
    # Parse request body as JSON
    new_student_data = request.get_json()
    # Update student in MongoDB collection
    success = Schüler.update(name, new_student_data)
    if success:
        return "Student updated successfully", 200
    else:
        return "Error updating student", 500


if __name__ == "__main__":
    app.run()

# schüler = Schüler("Oli", "4BHIF", "BAP", "Grünmais", "2022-01-01T12:00:00", "2022-01-01")
# schüler.save()
