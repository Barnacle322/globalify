function enableButton() {
    document.getElementById("saveButton").disabled = false;
}

async function updateInvestmentFirm() {
    const name = document.getElementById("name").value;
    const about = document.getElementById("about").value;
    const website = document.getElementById("website").value;
    const email = document.getElementById("email").value;
    const phone_number = document.getElementById("phone_number").value;
    const n_investments = document.getElementById("n_investments").value;
    const n_exits = document.getElementById("n_exits").value;
    const n_employees = document.getElementById("n_employees").value;
    const min_investment = document.getElementById("min_investment").value;
    const max_investment = document.getElementById("max_investment").value;
    const location = document.getElementById("location").value;

    const csrfToken = document.getElementById("csrf_token").value;

    const dataString = JSON.stringify({
        name: name,
        about: about,
        website: website,
        email: email,
        phone_number: phone_number,
        n_investments: n_investments,
        n_exits: n_exits,
        n_employees: n_employees,
        min_investment: min_investment,
        max_investment: max_investment,
        location: location,
    });
    try {
        const response = await fetch("", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: dataString,
        });
        if (response.redirected) {
            window.location.href = response.url;
        }
    } catch (error) {
        console.error("Error:", error);
    }
}

async function deleteInvestmentFirm(id) {
    const csrfToken = document.getElementById("csrf_token").value;

    if (!confirm("Are you sure you want to delete this investment firm?")) {
        return;
    }

    const response = await fetch(`/admin/dashboard/investment-firm/${id}/delete`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
        },
    });
    if (response.ok) {
        window.location.reload();
    }
}
