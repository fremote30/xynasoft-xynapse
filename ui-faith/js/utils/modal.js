// =====================================
// MODAL UTILITIES
// =====================================

window.openModal = function (
  modalId
) {

  const modal =
    document.getElementById(
      modalId
    );

  if (modal) {

    modal.style.display =
      "flex";
  }
};

window.closeModal = function (
  modalId
) {

  const modal =
    document.getElementById(
      modalId
    );

  if (modal) {

    modal.style.display =
      "none";
  }
};