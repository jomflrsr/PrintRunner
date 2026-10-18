"""Demo interaction for the PrintRunner runner interest form."""

from pyscript import document, when


@when("submit", "#application-form")
def submit_application(event):
    event.preventDefault()
    name = document.querySelector("#applicant-name").value.strip()
    first_name = name.split(" ")[0] if name else "there"
    document.querySelector("#application-feedback").textContent = (
        f"Thanks, {first_name}! Your interest form is ready. This demo has not sent it anywhere."
    )
