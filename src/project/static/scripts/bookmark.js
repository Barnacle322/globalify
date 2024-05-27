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
            var svg = document.getElementById(`bookmark-svg-investor-${investorId}`);
            if (data[0].bookmarked) {
                svg.style.fill = "#FFC9FC";
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
            var svg = document.getElementById(`bookmark-svg-firm-${firmId}`);
            if (data[0].bookmarked) {
                svg.style.fill = "#FFC9FC";
            } else {
                svg.style.fill = "none";
            }
        }
    } catch (error) {
        console.error(error);
    }
}
