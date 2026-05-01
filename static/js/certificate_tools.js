(function () {
    function showToastLikeMessage(button, message) {
        const originalText = button.innerText;

        button.innerText = message;
        button.disabled = true;

        setTimeout(function () {
            button.innerText = originalText;
            button.disabled = false;
        }, 1400);
    }

    function fallbackCopyText(text, button) {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";

        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();

        try {
            document.execCommand("copy");
            showToastLikeMessage(button, "Copied");
        } catch (error) {
            showToastLikeMessage(button, "Copy Failed");
        }

        document.body.removeChild(textarea);
    }

    document.addEventListener("click", function (event) {
        const button = event.target.closest("[data-copy-text]");

        if (!button) {
            return;
        }

        const text = button.getAttribute("data-copy-text") || "";

        if (!text) {
            showToastLikeMessage(button, "No Value");
            return;
        }

        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard
                .writeText(text)
                .then(function () {
                    showToastLikeMessage(button, "Copied");
                })
                .catch(function () {
                    fallbackCopyText(text, button);
                });
        } else {
            fallbackCopyText(text, button);
        }
    });
})();