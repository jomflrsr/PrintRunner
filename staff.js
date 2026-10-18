"use strict";

const loginPanel = document.querySelector("#staff-login-panel");
const board = document.querySelector("#service-board");
const loginForm = document.querySelector("#staff-login-form");
const loginFeedback = document.querySelector("#login-feedback");

function escapeText(element, value) {
  element.textContent = String(value ?? "");
  return element;
}

async function fetchOrders() {
  const response = await fetch("/api/staff/orders", { credentials: "same-origin" });
  const data = await response.json();
  if (response.status === 401) throw new Error("Your staff session has ended. Please sign in again.");
  if (!response.ok) throw new Error(data.error || "Could not load the order board.");
  return data.orders;
}

function addText(parent, tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  escapeText(element, text);
  parent.append(element);
  return element;
}

async function renderOrders() {
  const list = document.querySelector("#orders-list");
  list.replaceChildren();
  try {
    const orders = await fetchOrders();
    const counts = { New: 0, "In progress": 0, Completed: 0 };
    orders.forEach((order) => { counts[order.status] = (counts[order.status] || 0) + 1; });
    document.querySelector("#open-count").textContent = String(counts.New || 0);
    document.querySelector("#progress-count").textContent = String(counts["In progress"] || 0);
    document.querySelector("#complete-count").textContent = String(counts.Completed || 0);
    if (!orders.length) {
      const empty = document.createElement("div");
      empty.className = "empty-orders";
      addText(empty, "span", "", "▤");
      addText(empty, "b", "", "No orders yet");
      addText(empty, "p", "", "New customer orders will appear here.");
      const link = addText(empty, "a", "", "Go to order form ↗");
      link.href = "index.html#order";
      list.append(empty);
      return;
    }
    orders.forEach((order) => {
      const card = document.createElement("article");
      card.className = "order-card";
      const details = document.createElement("div");
      details.className = "order-card-main";
      addText(details, "span", "order-id", `${order.id} · ${order.created}`);
      addText(details, "h3", "", order.customer);
      addText(details, "p", "", `${order.print} · ${order.file}`);
      addText(details, "p", "order-destination", `⌖ ${order.dropoff}`);
      const contact = addText(details, "a", "order-contact", `☎ ${order.contact}`);
      contact.href = `tel:${String(order.contact).replace(/[^+\d]/g, "")}`;
      if (order.has_file) {
        const file = addText(details, "a", "order-contact", "↓ Download print file");
        file.href = `/api/staff/orders/${encodeURIComponent(order.id)}/file`;
      }

      const action = document.createElement("div");
      action.className = "order-card-side";
      addText(action, "strong", "", `₱${Number(order.total).toLocaleString("en-PH")}`);
      addText(action, "span", `order-status status-${order.status.toLowerCase().replaceAll(" ", "-")}`, order.status);
      const next = document.createElement("button");
      next.type = "button";
      next.className = "status-button";
      next.dataset.orderId = order.id;
      next.dataset.nextStatus = order.status === "New" ? "In progress" : "Completed";
      next.textContent = order.status === "New" ? "Start delivery →" : order.status === "In progress" ? "Mark delivered ✓" : "Completed";
      next.disabled = order.status === "Completed";
      action.append(next);
      card.append(details, action);
      list.append(card);
    });
  } catch (error) {
    addText(list, "p", "form-feedback", error.message);
    if (error.message.includes("session has ended")) showLogin();
  }
}

function showLogin() {
  board.hidden = true;
  loginPanel.hidden = false;
}

async function syncSession() {
  try {
    const response = await fetch("/api/staff/session", { credentials: "same-origin" });
    const data = await response.json();
    if (data.authenticated) {
      loginPanel.hidden = true;
      board.hidden = false;
      await renderOrders();
    }
  } catch { /* the sign-in form remains available */ }
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!loginForm.reportValidity()) return;
  const button = loginForm.querySelector('[type="submit"]');
  button.disabled = true;
  loginFeedback.textContent = "Signing in…";
  try {
    const result = await api("/api/staff/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: document.querySelector("#staff-user").value.trim(),
        password: document.querySelector("#staff-password").value,
      }),
    });
    csrfToken = result.csrf;
    loginPanel.hidden = true;
    board.hidden = false;
    loginForm.reset();
    await renderOrders();
  } catch (error) {
    loginFeedback.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#staff-logout").addEventListener("click", async () => {
  try { await api("/api/staff/logout", { method: "POST" }); } catch { /* clear local view either way */ }
  showLogin();
});

document.querySelector("#refresh-orders").addEventListener("click", renderOrders);
document.querySelector("#orders-list").addEventListener("click", async (event) => {
  const button = event.target.closest(".status-button");
  if (!button || button.disabled) return;
  button.disabled = true;
  try {
    await api(`/api/staff/orders/${encodeURIComponent(button.dataset.orderId)}/status`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: button.dataset.nextStatus }),
    });
    await renderOrders();
  } catch (error) {
    button.textContent = error.message;
    button.disabled = false;
  }
});

syncSession();
