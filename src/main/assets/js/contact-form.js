async function submitForm() {
    const isDev = window.location.hostname.includes('develop');
    const baseURL = `https://${isDev ? 'form.develop.cullancarey.com' : 'form.cullancarey.com'}/`;

    const submitButton = document.querySelector('.btn-primary');
    const formAlert = document.getElementById('form-alert');
    const formSuccess = document.getElementById('form-success');

    resetAlerts(formAlert, formSuccess);
    disableButton(submitButton, "Sending...");

    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim();
    const message = document.getElementById("message").value.trim();
    const botCheck = document.getElementById("bot_check");
    const recaptchaResponse = document.querySelector('textarea[name="g-recaptcha-response"]').value;

    if (!name || !email || !message || !recaptchaResponse) {
        showAlert(formAlert, "Please fill out all required fields.");
        return resetButton(submitButton);
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showAlert(formAlert, "Please enter a valid email address.");
        return resetButton(submitButton);
    }

    if (message.length > 2000) {
        showAlert(formAlert, "Message too long (max 2000 characters).");
        return resetButton(submitButton);
    }

    const payload = {
        CustomerName: name,
        CustomerEmail: email,
        MessageDetails: message,
        "g-recaptcha-response": recaptchaResponse,
    };

    if (botCheck.checked) payload.BotCheck = botCheck.value;

    try {
        const response = await fetchWithTimeout(baseURL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await parseResponse(response);
        if (response.ok) {
            showAlert(formSuccess, data.message || "Thank you for your message!");
            document.querySelector("form").reset();
            if (typeof grecaptcha !== "undefined") grecaptcha.reset();
        } else {
            showAlert(formAlert, data.error || "Something went wrong. Please email cullancareyconsulting@gmail.com.");
        }
    } catch (err) {
        console.error(err);
        showAlert(formAlert, "A network error occurred. Please try again later.");
    } finally {
        resetButton(submitButton);
    }
}

function resetAlerts(...elements) {
    elements.forEach(el => {
        el.style.display = 'none';
        el.textContent = '';
    });
}

function disableButton(btn, text) {
    btn.disabled = true;
    btn.textContent = text;
}

function resetButton(btn) {
    btn.disabled = false;
    btn.textContent = "Submit";
}

function showAlert(el, message) {
    el.textContent = message;
    el.style.display = 'block';
    el.scrollIntoView({ behavior: 'smooth' });
}

async function fetchWithTimeout(resource, options = {}, timeout = 10000) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    try {
        const res = await fetch(resource, { ...options, signal: controller.signal });
        return res;
    } finally {
        clearTimeout(id);
    }
}

async function parseResponse(response) {
    try {
        return await response.json();
    } catch {
        const text = await response.text();
        return { error: text };
    }
}