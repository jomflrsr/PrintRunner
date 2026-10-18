"""PrintRunner order estimate interactions, powered by PyScript."""

from pyscript import document, when

BW_PRICE = 2
COLOR_PRICE = 5
DELIVERY_FEE = 10
MAX_FILE_SIZE = 15 * 1024 * 1024


def peso(amount):
    return f"₱{amount:,}"


def estimate():
    print_type = document.querySelector("#print-type").value
    page_input = document.querySelector("#page-count")
    try:
        pages = int(page_input.value)
    except (TypeError, ValueError):
        pages = 1

    pages = max(1, min(pages, 500))
    page_input.value = str(pages)
    copies_input = document.querySelector("#copy-count")
    try:
        copies = int(copies_input.value)
    except (TypeError, ValueError):
        copies = 1
    copies = max(1, min(copies, 50))
    copies_input.value = str(copies)
    unit_price = COLOR_PRICE if print_type == "color" else BW_PRICE
    label = "color" if print_type == "color" else "B&W"
    subtotal = pages * copies * unit_price
    total = subtotal + DELIVERY_FEE

    document.querySelector("#estimate-total").textContent = peso(total)
    document.querySelector("#estimate-detail").textContent = (
        f"{pages} pages × {copies} {'copy' if copies == 1 else 'copies'} + delivery"
    )
    document.querySelector("#order-summary").hidden = True
    return pages, copies, label, total


@when("input", "#page-count")
@when("change", "#print-type")
@when("input", "#copy-count")
@when("input", "#location-detail")
@when("input", "#customer-name")
@when("input", "#customer-contact")
@when("change", "#dropoff")
def update_estimate(event=None):
    estimate()
    document.querySelector("#order-summary").hidden = True
    document.querySelector("#form-feedback").textContent = (
        "Your estimate updates as you make changes."
    )


@when("change", "#file-upload")
def show_selected_file(event):
    selected = document.querySelector("#file-upload").files
    file_input = document.querySelector("#file-upload")
    document.querySelector("#order-summary").hidden = True
    if selected.length and selected.item(0).size > MAX_FILE_SIZE:
        file_input.value = ""
        document.querySelector("#file-name").textContent = "Choose a file from your device"
        document.querySelector("#form-feedback").textContent = "That file is over the 15 MB limit. Choose a smaller file."
        return
    if selected.length:
        allowed = (".pdf", ".doc", ".docx", ".ppt", ".pptx", ".jpg", ".jpeg", ".png")
        if not selected.item(0).name.lower().endswith(allowed):
            file_input.value = ""
            document.querySelector("#file-name").textContent = "Choose a file from your device"
            document.querySelector("#form-feedback").textContent = "Choose a PDF, Office document, or image file."
            return
    file_name = selected.item(0).name if selected.length else "Choose a file from your device"
    document.querySelector("#file-name").textContent = file_name
    document.querySelector("#form-feedback").textContent = (
        "File selected. It will be uploaded when you place the order."
        if selected.length else "Your estimate updates as you make changes."
    )


@when("click", "#plus-pages")
def add_page(event):
    pages = int(document.querySelector("#page-count").value or 1)
    document.querySelector("#page-count").value = str(min(500, pages + 1))
    estimate()


@when("click", "#minus-pages")
def remove_page(event):
    pages = int(document.querySelector("#page-count").value or 1)
    document.querySelector("#page-count").value = str(max(1, pages - 1))
    estimate()


@when("click", "#menu-toggle")
def toggle_menu(event):
    button = document.querySelector("#menu-toggle")
    nav = document.querySelector("#nav-links")
    is_open = button.getAttribute("aria-expanded") == "true"
    button.setAttribute("aria-expanded", "false" if is_open else "true")
    nav.classList.toggle("nav-open")


@when("click", ".nav-links a")
def close_menu(event):
    document.querySelector("#menu-toggle").setAttribute("aria-expanded", "false")
    document.querySelector("#nav-links").classList.remove("nav-open")


estimate()
