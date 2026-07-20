from flask import Flask, render_template, request


app = Flask(__name__)


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

        return render_template("success.html", name=name)

    return render_template("index.html", form_data={})


if __name__ == "__main__":
    app.run(debug=True)
