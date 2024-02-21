function startResendTimer(countdown) {
    var timerElement = document.getElementById("resendTimer");
    var resendButton = document.getElementById("resendButton");

    if (countdown <= 0) {
        timerElement.style.display = "none";
        resendButton.innerText = "Resend Verification Email";
        resendButton.style.display = "inline-block";
        return;
    }

    timerElement.innerText = "Resend available in " + countdown + " seconds";
    timerElement.style.display = "inline-block";
    resendButton.style.display = "none";

    var interval = setInterval(function () {
        countdown--;
        
        if (countdown <= 0) {
            clearInterval(interval);
            timerElement.style.display = "none";
            resendButton.style.display = "inline-block";
        } else {
            timerElement.innerText = "Resend available in " + countdown + " seconds";
        }
    }, 1000);
}

function fetchCreatedAtAndUpdateTimer() {
    var userId = document.getElementById("user_id").value;
    fetch("/update-timer?user_id=" + userId, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        },
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        console.log(data)
        var createdAt = new Date(data.created_at);
        console.log(createdAt)
        var currentTime = new Date();
        var elapsedTimeInSeconds = Math.floor((currentTime - createdAt) / 1000);
        console.log(elapsedTimeInSeconds)
        var remainingTime = Math.max(0, 60 - elapsedTimeInSeconds);
        console.log(remainingTime)
        startResendTimer(remainingTime);
    })
    .catch(error => {
        console.error('There was a problem with the fetch operation:', error);
    });
}

fetchCreatedAtAndUpdateTimer();
