// =====================================
// TOAST SYSTEM
// =====================================

window.showToast = function (
  message,
  type = "success"
) {

  const toast =
    document.createElement("div");

  toast.className =
    `toast ${type}`;

  toast.innerText =
    message;

  document.body.appendChild(
    toast
  );

  setTimeout(() => {
    toast.classList.add("show");
  }, 50);

  setTimeout(() => {

    toast.classList.remove(
      "show"
    );

    setTimeout(() => {
      toast.remove();
    }, 300);

  }, 3000);
};