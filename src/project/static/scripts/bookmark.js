async function toggleInvestorBookmark(investorId) {
    const csrfToken = document.getElementById("csrf_token").value;
    try {
        const response = await fetch(`/investor/${investorId}/bookmark`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
        });
        if (response.ok) {
            const data = await response.json();
            var svg = document.getElementById(`bookmark-svg-${investorId}`);
            if (data[0].bookmarked) {
                console.log("Here");
                svg.style.fill = "#FF4500";
            } else {
                svg.style.fill = "none";
            }
        }
    } catch (error) {
        console.error(error);
    }
}

async function toggleInvestmentFirmBookmark(firmId) {
    const csrfToken = document.getElementById("csrf_token").value;
    try {
        const response = await fetch(`/investment-firm/${firmId}/bookmark`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
        });
        if (response.ok) {
            const data = await response.json();
            var svg = document.getElementById(`bookmark-svg-${investorId}`);
            if (data[0].bookmarked) {
                console.log("Here");
                svg.style.fill = "#FF4500";
            } else {
                svg.style.fill = "none";
            }
        }
    } catch (error) {
        console.error(error);
    }
}
