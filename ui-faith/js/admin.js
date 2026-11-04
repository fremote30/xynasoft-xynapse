// =====================================
// ADMIN.JS
// =====================================

async function loadPastorApplications() {

    try {

        const token =
            localStorage.getItem(
                "access_token"
            );

        const response =
            await fetch(
                "/api/v1/users/pastor-applications",
                {
                    headers: {
                        Authorization:
                            `Bearer ${token}`
                    }
                }
            );

        if (!response.ok) {
            throw new Error(
                "Failed to load applications"
            );
        }

        const applications =
            await response.json();

        const container =
            document.getElementById(
                "pastorApplications"
            );

        if (!container) return;

        if (!applications.length) {

            container.innerHTML = `
                <div class="feature-card">
                    <h3>No Pending Applications</h3>
                    <p>
                        All pastor requests
                        have been reviewed.
                    </p>
                </div>
            `;

            return;
        }

        container.innerHTML =
            applications.map(app => `
                <div class="feature-card">

                    <h3>${app.name}</h3>

                    <p>${app.email}</p>

                    <p>
                        Applied:
                        ${new Date(
                            app.applied_at
                        ).toLocaleDateString()}
                    </p>

                    <div
                        style="
                            display:flex;
                            gap:10px;
                            margin-top:15px;
                        "
                    >

                        <button
                            class="btn-primary"
                            onclick="approvePastor(${app.id})"
                        >
                            Approve
                        </button>

                        <button
                            class="btn-secondary"
                            onclick="rejectPastor(${app.id})"
                        >
                            Reject
                        </button>

                    </div>

                </div>
            `).join("");

    } catch (err) {

        console.error(err);

        const container =
            document.getElementById(
                "pastorApplications"
            );

        if (container) {

            container.innerHTML = `
                <div class="feature-card">
                    <h3>Error</h3>
                    <p>
                        Failed to load
                        applications.
                    </p>
                </div>
            `;
        }
    }
}


async function approvePastor(
  userId
) {

  try {

    const token =
      localStorage.getItem(
        "access_token"
      );

    const response =
      await fetch(
        `/api/v1/pastors/approve/${userId}`,
        {
          method: "POST",

          headers: {
            Authorization:
              `Bearer ${token}`
          }
        }
      );

    if (!response.ok) {

      throw new Error(
        "Approval failed"
      );
    }

    showToast(
      "✅ Pastor approved",
      "success"
    );

    loadPastorApplications();

  } catch (err) {

    console.error(err);

    showToast(
      "Approval failed",
      "error"
    );
  }
}



async function rejectPastor(
  userId
) {

  try {

    const token =
      localStorage.getItem(
        "access_token"
      );

    const response =
      await fetch(
        `/api/v1/pastors/reject/${userId}`,
        {
          method: "POST",

          headers: {
            Authorization:
              `Bearer ${token}`
          }
        }
      );

    if (!response.ok) {

      throw new Error(
        "Rejection failed"
      );
    }

    showToast(
      "Application rejected",
      "success"
    );

    loadPastorApplications();

  } catch (err) {

    console.error(err);

    showToast(
      "Rejection failed",
      "error"
    );
  }
}