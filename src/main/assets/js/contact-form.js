async function submitForm() {
    const baseURL = window.location.hostname.includes('develop')
        ? 'https://form.develop.cullancarey.com/'
        : 'https://form.cullancarey.com/';

    const submitButton = document.querySelector('.btn-primary');
    const formAlert = document.getElementById('form-alert');
    const formSuccess = document.getElementById('form-success');

    // Reset alert areas
    formAlert.style.display = 'none';
    formSuccess.style.display = 'none';
    formAlert.textContent = '';
    formSuccess.textContent = '';

    submitButton.disabled = true;
    submitButton.textContent = "Sending...";

    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim();
    const message = document.getElementById("message").value.trim();
    const botCheck = document.getElementById("bot_check");
    const recaptchaResponse = document.querySelector('textarea[name="g-recaptcha-response"]').value;

    if (!name || !email || !message || !recaptchaResponse) {
        formAlert.textContent = "Please fill out all required fields.";
        formAlert.style.display = 'block';
        resetButton(submitButton);
        return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        formAlert.textContent = "Please enter a valid email address.";
        formAlert.style.display = 'block';
        resetButton(submitButton);
        return;
    }

    const payload = {
        CustomerName: name,
        CustomerEmail: email,
        MessageDetails: message,
        "g-recaptcha-response": recaptchaResponse
    };

    if (botCheck.checked) {
        payload.BotCheck = botCheck.value;
    }

    try {
        const response = await fetch(baseURL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        let data;
        try {
            data = await response.json();
        } catch {
            const text = await response.text();
            data = { error: text };
        }

        if (response.ok) {
            formSuccess.textContent = data.message || "Thank you for your message! Cullan will reach out to you soon.";
            formSuccess.style.display = 'block';
            document.querySelector("form").reset();
        } else {
            formAlert.textContent = data.error || "Something went wrong. Please email cullancareyconsulting@gmail.com.";
            formAlert.style.display = 'block';
        }
    } catch (err) {
        formAlert.textContent = "A network error occurred. Please try again later.";
        formAlert.style.display = 'block';
        console.error(err);
    } finally {
        resetButton(submitButton);
    }
}

function resetButton(submitButton) {
    submitButton.disabled = false;
    submitButton.textContent = "Submit";
}