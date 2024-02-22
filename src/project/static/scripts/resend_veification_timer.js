function startResendTimer(countdown) {
    let timerElement = document.getElementById("resendTimer");
    let resendButton = document.getElementById("resendButton");

    function updateUI(isCountdown) {
        if (isCountdown) {
            timerElement.innerText = `Send another in ${countdown} seconds`;
            timerElement.style.display = "inline-block";
            resendButton.style.display = "none";
        } else {
            timerElement.style.display = "none";
            resendButton.innerText = "Resend Verification Email";
            resendButton.style.display = "inline-block";
        }
    }

    if (countdown <= 0) {
        updateUI(false);
        return;
    }

    updateUI(true);

    let interval = setInterval(function () {
        countdown--;

        if (countdown <= 0) {
            clearInterval(interval);
            updateUI(false);
        } else {
            timerElement.innerText = `Send another in ${countdown} seconds`;
        }
    }, 1000);
}

function fetchCreatedAtAndUpdateTimer() {
    let userId = document.getElementById("user_id").value;
    fetch(`/fetch-time/${userId}`)
        .then((response) => {
            if (!response.ok) {
                throw new Error(`Network response was not ok, status: ${response.status}`);
            }
            return response.json();
        })
        .then((data) => {
            startResendTimer(data.time_left);
        })
        .catch((error) => {
            console.error(`Error in fetchCreatedAtAndUpdateTimer: ${error.message}`);
        });
}

fetchCreatedAtAndUpdateTimer();
