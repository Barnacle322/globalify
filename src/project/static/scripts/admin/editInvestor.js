function enableButton() {
    document.getElementById("saveButton").disabled = false;
}

async function updateInvestor() {
    const first_name = document.getElementById("first_name").value;
    const last_name = document.getElementById("last_name").value;
    const firm_name = document.getElementById("firm_name").value;
    const about = document.getElementById("about").value;
    const website = document.getElementById("website").value;
    const linkedin = document.getElementById("linkedin").value;
    const twitter = document.getElementById("twitter").value;
    const email = document.getElementById("email").value;
    const phone_number = document.getElementById("phone_number").value;
    const n_investments = document.getElementById("n_investments").value;
    const n_exits = document.getElementById("n_exits").value;
    const min_investment = document.getElementById("min_investment").value;
    const max_investment = document.getElementById("max_investment").value;
    const location = document.getElementById("location").value;
    const selectedRounds = Array.from(document.querySelectorAll('input[name="selected_rounds"]:checked')).map((input) =>
        parseInt(input.value, 10),
    );
    const selectedIndustries = Array.from(document.querySelectorAll('input[name="selected_industries"]:checked')).map(
        (input) => parseInt(input.value, 10),
    );
    const user_email = document.getElementById("searchInput").value;
    const csrfToken = document.getElementById("csrf_token").value;

    const dataString = JSON.stringify({
        first_name: first_name,
        last_name: last_name,
        firm_name: firm_name,
        about: about,
        website: website,
        linkedin: linkedin,
        twitter: twitter,
        email: email,
        phone_number: phone_number,
        n_investments: n_investments,
        n_exits: n_exits,
        min_investment: min_investment,
        max_investment: max_investment,
        location: location,
        round: selectedRounds,
        industry: selectedIndustries,
        user_email: user_email,
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

document.getElementById("searchInput").addEventListener("input", function () {
    var searchInput = this.value;
    if (searchInput.length > 1) {
        fetch(`/admin/search_users/${searchInput}`)
            .then((response) => response.json())
            .then((data) => {
                var userList = document.getElementById("userList");
                userList.innerHTML = "";
                data.users.forEach((email) => {
                    var li = document.createElement("li");
                    li.textContent = email;
                    li.style.cursor = "pointer";
                    li.addEventListener("click", function () {
                        document.getElementById("searchInput").value = this.textContent;
                        userList.innerHTML = "";
                    });
                    userList.appendChild(li);
                });
            })
            .catch((error) => console.error("Error searching users:", error));
    } else {
        document.getElementById("userList").innerHTML = "";
    }
});
