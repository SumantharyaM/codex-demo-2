import logging
import os

import mysql.connector
from flask import Flask, jsonify, render_template, request
from mysql.connector import Error


app = Flask(__name__)
app.logger.setLevel(logging.INFO)

DATABASE_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "database": os.getenv("MYSQL_DATABASE", "grandpal"),
    "user": os.getenv("MYSQL_USER", "grandpal"),
    "password": os.getenv("MYSQL_PASSWORD"),
}

db_connection = None


def connect_to_database():
    """Open a MySQL connection without preventing the site from starting."""
    global db_connection

    try:
        if db_connection and db_connection.is_connected():
            return db_connection

        if not DATABASE_CONFIG["password"]:
            app.logger.error("MYSQL_PASSWORD is not configured; database features are unavailable.")
            return None

        db_connection = mysql.connector.connect(**DATABASE_CONFIG)
        app.logger.info("Connected to the GrandPal MySQL database.")
        return db_connection
    except Error:
        app.logger.exception("Unable to connect to the GrandPal MySQL database.")
        db_connection = None
        return None


# Establish the database connection as the application starts. If MySQL is
# temporarily unavailable, form submissions retry the connection and show a
# friendly message rather than taking the website down.
connect_to_database()


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        city = request.form.get("city", "").strip()

        if not all((name, email, phone, city)):
            return render_template(
                "index.html",
                error="Please complete every field so we can get in touch.",
                form_data=request.form,
            )

        connection = connect_to_database()
        if not connection:
            return render_template(
                "index.html",
                error="We could not save your registration right now. Please try again shortly.",
                form_data=request.form,
            )

        cursor = None
        try:
            cursor = connection.cursor(prepared=True)
            cursor.execute(
                "INSERT INTO users (name, email, phone, city) VALUES (%s, %s, %s, %s)",
                (name, email, phone, city),
            )
            connection.commit()
        except Error:
            app.logger.exception("Unable to save GrandPal registration.")
            connection.rollback()
            return render_template(
                "index.html",
                error="We could not save your registration right now. Please try again shortly.",
                form_data=request.form,
            )
        finally:
            if cursor:
                cursor.close()

        return render_template("success.html", name=name)

    return render_template("index.html", form_data={})


@app.route("/api/users", methods=["POST"])
def add_user_api():
    """Add a user through the REST API using the site's MySQL connection."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(status="error", message="A JSON request body is required."), 400

    fields = ("name", "email", "phone", "city")
    user = {field: str(data.get(field, "")).strip() for field in fields}
    missing_fields = [field for field in fields if not user[field]]
    if missing_fields:
        return (
            jsonify(
                status="error",
                message=f"Required fields missing: {', '.join(missing_fields)}",
            ),
            400,
        )

    connection = connect_to_database()
    if not connection:
        return jsonify(status="error", message="Database unavailable."), 503

    cursor = None
    try:
        cursor = connection.cursor(prepared=True)
        cursor.execute(
            "INSERT INTO users (name, email, phone, city) VALUES (%s, %s, %s, %s)",
            tuple(user[field] for field in fields),
        )
        connection.commit()
    except Error:
        app.logger.exception("Unable to add user through the API.")
        connection.rollback()
        return jsonify(status="error", message="Unable to add user."), 500
    finally:
        if cursor:
            cursor.close()

    return jsonify(status="success", message="User added successfully"), 201


@app.route("/api/users", methods=["GET"])
def get_users_api():
    """Return every stored user as JSON."""
    connection = connect_to_database()
    if not connection:
        return jsonify(status="error", message="Database unavailable."), 503

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, name, email, phone, city FROM users ORDER BY id")
        users = cursor.fetchall()
    except Error:
        app.logger.exception("Unable to retrieve users through the API.")
        return jsonify(status="error", message="Unable to retrieve users."), 500
    finally:
        if cursor:
            cursor.close()

    return jsonify(users)


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user_api(user_id):
    """Delete a user by primary-key id."""
    connection = connect_to_database()
    if not connection:
        return jsonify(status="error", message="Database unavailable."), 503

    cursor = None
    try:
        cursor = connection.cursor(prepared=True)
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        connection.commit()
        if not cursor.rowcount:
            return jsonify(status="error", message="User not found."), 404
    except Error:
        app.logger.exception("Unable to delete user through the API.")
        connection.rollback()
        return jsonify(status="error", message="Unable to delete user."), 500
    finally:
        if cursor:
            cursor.close()

    return jsonify(status="success", message="User deleted successfully")


if __name__ == "__main__":
    app.run(debug=True)
