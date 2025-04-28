async function submitForm() {
    const baseURL = window.location.hostname.includes('develop') ? 'https://form.develop.cullancarey.com/' : 'https://form.cullancarey.com/';
    const submitButton = document.querySelector('.btn-primary');
    console.log(baseURL);

    submitButton.disabled = true;
    submitButton.textContent = "Sending...";

    const name = document.getElementById("name").value;
    const email = document.getElementById("email").value;
    const message = document.getElementById("message").value;
    const bot_check = document.getElementById("bot_check");
    const recaptchaResponse = document.querySelector('textarea[name="g-recaptcha-response"]').value;

    if (!name || !email || !message || !recaptchaResponse) {
        alert("Please fill out all the required fields.");
        submitButton.disabled = false;
        submitButton.textContent = "Submit";
        return;
    }

    const payload = {
        CustomerName: name,
        CustomerEmail: email,
        MessageDetails: message,
        "g-recaptcha-response": recaptchaResponse
    };

    if (bot_check.checked) {
        payload.BotCheck = bot_check.value;
    }

    try {
        const response = await fetch(baseURL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {  // response.ok means 200-299
            alert((data.message || 'Thank you for your message!'));
        } else {
            alert((data.error || 'Something went wrong. Please contact cullan@cullancarey.com.'));
        }
    } catch (error) {
        console.error("There was a problem with the fetch operation:", error);
        alert("A network error occurred. Please try again later.");
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Submit";
    }
}