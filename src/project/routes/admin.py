from flask import Blueprint, redirect, render_template, request, url_for

from ..models import Industry, Investor, Round, db

admin = Blueprint("admin", __name__)


@admin.get("/")
def index():
    return render_template("admin/investors/index.html")


@admin.get("/investors/")
def get_all_investors():
    investors = Investor.get_all()
    return render_template("admin/investors/investors.html", investors=investors)


@admin.route("/investors/add", methods=["GET", "POST"])
def add_investor():
    if request.method == "POST":
            data = request.form
            investor_data = {
                "first_name": data.get("first_name"),
                "last_name": data.get("last_name"),
                "firm_name": data.get("firm_name"),
                "about": data.get("about"),
                "position": data.get("position"),
                "website": data.get("website"),
                "linkedin": data.get("linkedin"),
                "twitter": data.get("twitter"),
                "email": data.get("email"),
                "phone_number": data.get("phone_number"),
                "n_investments": int(data.get("n_investments", 0)),
                "n_exits": int(data.get("n_exits", 0)),
                "min_investment": int(data.get("min_investment", 0)),
                "max_investment": int(data.get("max_investment", 0)),
                "location": data.get("location")
            }

            try:
                selected_round_ids = request.form.getlist("rounds")
                selected_industry_ids = request.form.getlist("industries")

                selected_rounds = [Round.get_by_id(int(round_id)) for round_id in selected_round_ids]
                selected_industries = [Industry.get_by_id(int(industry_id)) for industry_id in selected_industry_ids]

                new_investor = Investor(
                    **investor_data,
                    rounds=selected_rounds,
                    industries=selected_industries,
                )

                db.session.add(new_investor)
                db.session.commit()
                return redirect(url_for("admin.get_all_investors"))
            except Exception as e:
                db.session.rollback()
                return render_template("admin/investors/add_investor.html", error=str(e), **investor_data)

    rounds = Round.get_all()
    industries = Industry.get_all()
    return render_template("admin/investors/add_investor.html", rounds=rounds, industries=industries)


@admin.route("/investors/edit/<int:investor_id>", methods=["GET", "POST"])
def edit_investor(investor_id):
    investor = Investor.query.get_or_404(investor_id)

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        firm_name = request.form.get("firm_name")
        about = request.form.get("about")
        position = request.form.get("position")
        website = request.form.get("website")
        linkedin = request.form.get("linkedin")
        twitter = request.form.get("twitter")
        email = request.form.get("email")
        phone_number = request.form.get("phone_number")
        n_investments = int(request.form.get("n_investments", 0) or 0)
        n_exits = int(request.form.get("n_exits", 0) or 0)
        min_investment = int(request.form.get("min_investment", 0) or 0)
        max_investment = int(request.form.get("max_investment", 0) or 0)
        location = request.form.get("location")
        selected_round_ids = request.form.getlist("rounds")
        selected_industry_ids = request.form.getlist("industries")

        selected_rounds = [Round.get_by_id(int(round_id)) for round_id in selected_round_ids]
        selected_industries = [Industry.get_by_id(int(industry_id)) for industry_id in selected_industry_ids]

        investor.first_name = first_name
        investor.last_name = last_name
        investor.firm_name = firm_name
        investor.about = about
        investor.position = position
        investor.website = website
        investor.linkedin = linkedin
        investor.twitter = twitter
        investor.email = email
        investor.phone_number = phone_number
        investor.n_investments = n_investments
        investor.n_exits = n_exits
        investor.min_investment = min_investment
        investor.max_investment = max_investment
        investor.location = location
        investor.rounds = selected_rounds
        investor.industries = selected_industries

        db.session.commit()

        return redirect(url_for("admin.get_all_investors"))

    rounds = Round.get_all()
    industries = Industry.get_all()
    return render_template("admin/investors/edit_investor.html", investor=investor, rounds=rounds, industries=industries)


@admin.route("/investors/delete/<int:investor_id>", methods=["POST"])
def delete_investor(investor_id):
    investor = Investor.query.get_or_404(investor_id)

    db.session.delete(investor)
    db.session.commit()

    return redirect(url_for("admin.get_all_investors"))
