// =====================================
// LOADER UTILITIES
// =====================================

window.showLoader = function (
  element,
  message = "Loading..."
) {

  if (!element) return;

  element.innerHTML = `

    <div class="loading-state">

      <div class="loading-spinner"></div>

      <p>${message}</p>

    </div>

  `;
};

window.showErrorState = function (
  element,
  message = "Something went wrong"
) {

  if (!element) return;

  element.innerHTML = `

    <div class="error-state">

      <h3>${message}</h3>

    </div>

  `;
};