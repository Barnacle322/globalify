function toggleInvestorBookmark(investorId) {
    const csrfToken = document.getElementById("csrf_token").value;
    try {
        const response = fetch(`/investor/${investorId}/bookmark`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
        });
        if (response.ok) {
            const bookmarkIcon = document.getElementById(`bookmark-icon-${investorId}`);
            bookmarkIcon.classList.toggle("fas");
            bookmarkIcon.classList.toggle("far");
        }
    } catch (error) {
        console.error(error);
    }
}
