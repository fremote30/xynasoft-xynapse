// =====================================
// NETWORK.JS
// STEP 1S — PROFILE + NETWORK ENGINE
// =====================================

(() => {

  // =====================================
  // SHORTCUT
  // =====================================
  const $ = (id) =>
    document.getElementById(id);

  // =====================================
  // LOAD USER INFO
  // =====================================
  async function loadUserInfo() {

    try {

      const user =
        await getCurrentUser();

      if (!user) return;

      window.currentUser =
        user;

      if ($("userName")) {

        $("userName").textContent =
          user.name;
      }

    } catch (e) {

      console.error(
        "User load error:",
        e
      );
    }
  }

  // =====================================
  // MEMBER FEED
  // =====================================
  async function loadMemberFeed() {

    try {

      const res =
        await apiFetch(
          "/api/v1/pastors/feed"
        );

      if (!res.ok) {

        throw new Error(
          "Failed to load member feed"
        );
      }

      const data =
        await res.json();

      const container =
        $("memberFeed");

      if (!container) return;

      // =====================================
      // EMPTY FEED
      // =====================================
      if (!data.length) {

        container.innerHTML = `

          <div class="feature-card">

            <h3>
              Your feed is empty
            </h3>

            <p>
              Follow pastors from the
              Network page to personalize
              your feed.
            </p>

            <button
              class="btn-primary"
              onclick="navigate('network')"
            >
              Explore Network
            </button>

          </div>

        `;

        return;
      }

      // =====================================
      // RENDER FEED
      // =====================================
      container.innerHTML =
        data.map(s => `

          <div
            class="
              feature-card
              sermon-feed-card
            "
          >

            <h3>
              ${s.title}
            </h3>

            <small>

              By ${s.pastor_name}
              •

              ${formatDate(
                s.created_at
              )}

            </small>

            <p>

              ${(s.content || "")
                .substring(0, 200)}...

            </p>

            <button
              class="btn-secondary"

              onclick="
                openSermon(${s.id})
              "
            >
              Read Sermon
            </button>

          </div>

        `).join("");

    } catch (err) {

      console.error(
        "Feed error:",
        err
      );

      const container =
        $("memberFeed");

      if (container) {

        container.innerHTML = `

          <div class="feature-card">

            <h3>
              Unable to load feed
            </h3>

            <p>
              Please try again later.
            </p>

          </div>

        `;
      }
    }
  }

  // =====================================
  // NETWORK PAGE
  // =====================================
  async function loadNetworkPage() {

    try {

      await loadTopSermons();

      await loadAIInsights();

      await loadPastors();

      // =====================================
      // SUMMARY
      // =====================================
      const summaryRes =
        await apiFetch(
          "/api/v1/dashboard/summary"
        );

      if (summaryRes.ok) {

        const summary =
          await summaryRes.json();

        if ($("sermonCount")) {

          $("sermonCount").innerText =
            summary.total_sermons ?? 0;
        }

        if ($("memberCount")) {

          $("memberCount").innerText =
            summary.total_members ?? 0;
        }
      }

      // =====================================
      // PRAYER WALL
      // =====================================
      const prayerRes =
        await apiFetch(
          "/api/v1/dashboard/recent-prayers"
        );

      if (prayerRes.ok) {

        const prayers =
          await prayerRes.json();

        if ($("prayerWall")) {

          $("prayerWall").innerHTML =

            prayers.length

              ? prayers.map(p => `

                <div class="prayer-item">

                  <strong>
                    ${p.user_name}
                  </strong>

                  <small>
                    ${formatDate(
                      p.created_at
                    )}
                  </small>

                  <p>
                    ${p.message}
                  </p>

                </div>

              `).join("")

              : `
                <p>
                  No prayer activity yet
                </p>
              `;
        }
      }

    } catch (err) {

      console.error(
        "Network page error:",
        err
      );

      showToast?.(
        "Failed to load network page",
        "error"
      );
    }
  }

  // =====================================
  // LOAD PASTORS
  // =====================================
  async function loadPastors() {

    try {

      const res =
        await apiFetch(
          "/api/v1/pastors"
        );

      if (!res.ok) {

        throw new Error(
          "Failed to load pastors"
        );
      }

      const pastors =
        await res.json();

      const container =
        $("pastorGrid");

      if (!container) return;

      // =====================================
      // EMPTY
      // =====================================
      if (!pastors.length) {

        container.innerHTML = `

          <div class="feature-card">

            <h3>
              No pastors yet
            </h3>

            <p>
              Pastors will appear here.
            </p>

          </div>

        `;

        return;
      }

      // =====================================
      // RENDER
      // =====================================
      container.innerHTML =
        pastors.map(pastor => `

          <div
            class="
              feature-card
              pastor-card
              clickable
            "

            onclick="
              openPastorProfile(
                ${pastor.id}
              )
            "
          >

            <div class="icon">
              ⛪
            </div>

            <h3>
              ${pastor.name}
            </h3>

            <p>
              ${pastor.followers}
              followers
            </p>

            <button

              class="
                ${pastor.is_following
                  ? "btn-secondary"
                  : "btn-primary"}
              "

              onclick="
                ${
                  pastor.is_following

                    ? `unfollowPastor(${pastor.id})`

                    : `followPastor(${pastor.id})`
                }
              "
            >

              ${
                pastor.is_following

                  ? "Following"

                  : "Follow"
              }

            </button>

          </div>

        `).join("");

    } catch (err) {

      console.error(
        "Pastor load error:",
        err
      );
    }
  }

  // =====================================
  // PROFILE PAGE
  // =====================================
  async function loadProfilePage() {

    try {

      const res =
        await apiFetch(
          "/api/v1/pastor-profile/me"
        );

      if (!res.ok) {

        throw new Error(
          "Failed to load profile"
        );
      }

      const profile =
        await res.json();

      if ($("profileBio")) {

        $("profileBio").value =
          profile.bio || "";
      }

      if ($("churchName")) {

        $("churchName").value =
          profile.church_name || "";
      }

      if ($("ministryFocus")) {

        $("ministryFocus").value =
          profile.ministry_focus || "";
      }

      if ($("profileLocation")) {

        $("profileLocation").value =
          profile.location || "";
      }

      if ($("profileWebsite")) {

        $("profileWebsite").value =
          profile.website || "";
      }

    } catch (err) {

      console.error(
        "Profile page error:",
        err
      );

      showToast?.(
        "Failed to load profile",
        "error"
      );
    }
  }

  // =====================================
  // SAVE PROFILE
  // =====================================
  async function saveProfile() {

    try {

      const saveRes =
        await apiFetch(
          "/api/v1/pastor-profile/me",
          {
            method: "PUT",

            body: JSON.stringify({

              bio:
                $("profileBio")?.value,

              church_name:
                $("churchName")?.value,

              ministry_focus:
                $("ministryFocus")?.value,

              location:
                $("profileLocation")?.value,

              website:
                $("profileWebsite")?.value
            })
          }
        );

      const data =
        await saveRes.json();

      if (!saveRes.ok) {

        throw new Error(
          data.detail ||
          "Save failed"
        );
      }

      showToast?.(
        "Profile updated successfully",
        "success"
      );

    } catch (err) {

      console.error(
        "Profile save error:",
        err
      );

      showToast?.(
        err.message ||
        "Save failed",
        "error"
      );
    }
  }

  // =====================================
  // PASTOR PROFILE PAGE
  // =====================================
  async function loadPastorProfilePage() {

    try {

      const pastorId =
        localStorage.getItem(
          "selected_pastor_id"
        );

      if (!pastorId) {
        return;
      }

      const res =
        await apiFetch(
          `/api/v1/pastor-profile/${pastorId}`
        );

      if (!res.ok) {

        throw new Error(
          "Failed to load profile"
        );
      }

      const profile =
        await res.json();

      if ($("pastorName")) {

        $("pastorName").textContent =
          profile.name || "Pastor";
      }

      if ($("pastorBio")) {

        $("pastorBio").textContent =
          profile.bio || "Ministry profile";
      }

      if ($("churchNameView")) {

        $("churchNameView").textContent =
          profile.church_name || "—";
      }

      if ($("ministryFocusView")) {

        $("ministryFocusView").textContent =
          profile.ministry_focus || "—";
      }

      if ($("locationView")) {

        $("locationView").textContent =
          profile.location || "—";
      }

      if ($("followersView")) {

        $("followersView").textContent =
          profile.followers || 0;
      }

      // =====================================
      // SERMONS
      // =====================================
      const sermonsContainer =
        $("pastorSermons");

      if (sermonsContainer) {

        sermonsContainer.innerHTML =

          profile.sermons?.length

            ? profile.sermons.map(s => `

              <div
                class="
                  feature-card
                  clickable
                "

                onclick="
                  openSermon(${s.id})
                "
              >

                <h3>
                  ${s.title}
                </h3>

                <small>
                  ${formatDate(
                    s.created_at
                  )}
                </small>

              </div>

            `).join("")

            : `
              <p>
                No sermons yet
              </p>
            `;
      }

    } catch (err) {

      console.error(
        "Pastor profile error:",
        err
      );

      showToast?.(
        "Failed to load profile",
        "error"
      );
    }
  }

  // =====================================
  // OPEN PASTOR PROFILE
  // =====================================
  window.openPastorProfile =
    function (pastorId) {

    localStorage.setItem(
      "selected_pastor_id",
      pastorId
    );

    navigate(
      "pastor-profile"
    );
  };

  // =====================================
  // GLOBAL EXPORTS
  // =====================================

  window.loadUserInfo =
    loadUserInfo;

  window.loadNetworkPage =
    loadNetworkPage;

  window.loadPastors =
    loadPastors;

  window.loadMemberFeed =
    loadMemberFeed;

  window.loadProfilePage =
    loadProfilePage;

  window.saveProfile =
    saveProfile;

  window.loadPastorProfilePage =
    loadPastorProfilePage;

})();