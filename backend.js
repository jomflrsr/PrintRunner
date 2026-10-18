"use strict";

let csrfToken = "";

async function requestCsrf() {
  const response = await fetch("/api/csrf", { credentials: "same-origin" });
  const data = await response.json();
  csrfToken = data.token;
  return csrfToken;
}

async function api(url, options = {}) {
  if (!csrfToken) await requestCsrf();
  const headers = new Headers(options.headers || {});
  headers.set("X-CSRF-Token", csrfToken);
  const response = await fetch(url, { ...options, headers, credentials: "same-origin" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Something went wrong. Please try again.");
  return data;
}

const orderForm = document.querySelector("#order-form");
if (orderForm) {
  orderForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!orderForm.reportValidity()) return;
    const feedback = document.querySelector("#form-feedback");
    const button = orderForm.querySelector('[type="submit"]');
    button.disabled = true;
    feedback.textContent = "Sending your order securely…";
    try {
      const order = await api("/api/orders", { method: "POST", body: new FormData(orderForm) });
      const form = new FormData(orderForm);
      const pages = Number(form.get("page-count"));
      const copies = Number(form.get("copy-count"));
      const label = form.get("print-type") === "color" ? "color" : "B&W";
      const upload = form.get("file-upload");
      document.querySelector("#summary-customer").textContent = form.get("customer-name");
      document.querySelector("#summary-contact").textContent = form.get("customer-contact");
      document.querySelector("#summary-file").textContent = upload?.name || "No file attached";
      document.querySelector("#summary-print").textContent = `${pages} ${label} pages × ${copies} ${copies === 1 ? "copy" : "copies"}`;
      document.querySelector("#summary-dropoff").textContent = `${form.get("dropoff")} · ${form.get("location-detail")}`;
      document.querySelector("#summary-total").textContent = `₱${Number(order.total).toLocaleString("en-PH")} · ${order.id}`;
      document.querySelector("#order-summary").hidden = false;
      feedback.textContent = order.message;
      orderForm.reset();
      document.querySelector("#file-name").textContent = "Choose a file from your device";
    } catch (error) {
      feedback.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
}

const applicationForm = document.querySelector("#application-form");
if (applicationForm) {
  applicationForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!applicationForm.reportValidity()) return;
    const feedback = document.querySelector("#application-feedback");
    const button = applicationForm.querySelector('[type="submit"]');
    button.disabled = true;
    feedback.textContent = "Sending your application…";
    const form = new FormData(applicationForm);
    try {
      const result = await api("/api/applications", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.get("applicant-name"), email: form.get("applicant-email"),
          phone: form.get("applicant-phone"), availability: form.get("availability"),
          reason: form.get("why-join"),
        }),
      });
      feedback.textContent = result.message;
      applicationForm.reset();
    } catch (error) {
      feedback.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
}

requestCsrf().catch(() => {});
