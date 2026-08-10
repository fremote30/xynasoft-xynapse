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

  let allPastors = [];
  let activePastorFilter = "all"; 
  let pastorDisplayLimit = 3;
  let networkOverview = null;
  // =====================================
  // HELPER FUNCTION
  // =====================================
  function setValue(id, value) {
  const el = $(id);
  if (el) el.value = value ?? "";
}

function setChecked(id, value) {
  const el = $(id);
  if (el) el.checked = Boolean(value);
}
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
                window.openSermon(${s.id})
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

    // Prevent duplicate loads
  if (window.__loadingNetwork) {
    return;
  }

window.__loadingNetwork = true;
  try {

    // Reset directory pagination whenever
    // the Network page is opened.
    window.currentPastorSearch = "";
    window.pastorOffset = 0;
    window.pastorHasMore = false;
    initializeNetworkSearch();

    // Load independent Network sections in parallel.
    // One failed request will not prevent the others
    // from attempting to render.
    const results = await Promise.allSettled([
      loadNetworkOverview(),
      loadPastors(),
      typeof loadTopSermons === "function"
        ? loadTopSermons()
        : Promise.resolve(),
      typeof loadAIInsights === "function"
        ? loadAIInsights()
        : Promise.resolve()
    ]);

    results.forEach((result, index) => {

      if (result.status === "rejected") {

        const sections = [
          "community overview",
          "pastor directory",
          "top sermons",
          "AI insights"
        ];

        console.error(
          `Failed to load ${sections[index]}:`,
          result.reason
        );
      }
    });

  } catch (err) {

    console.error(
      "Network page error:",
      err
    );

    showToast?.(
      "Some Network content could not be loaded.",
      "error"
    );
  }finally {

   window.__loadingNetwork = false;

  }
}

// =====================================
// LOAD PASTORS
// =====================================
async function loadPastors() {

  try {

    const params = new URLSearchParams({
      limit: "20",
      offset: "0"
    });

    const res = await apiFetch(
      `/api/v1/pastors/?${params.toString()}`
    );

    if (!res.ok) {

      let message =
        "Failed to load pastors";

      try {

        const errorData =
          await res.json();

        message =
          errorData.detail ||
          message;

      } catch (_) {
        // Keep default message when
        // response is not JSON.
      }

      throw new Error(message);
    }

    const data =
      await res.json();

    allPastors =
      Array.isArray(data.items)
        ? data.items
        : [];

    window.pastorHasMore =
      Boolean(data.has_more);

    window.pastorOffset =
      Number(data.offset || 0) +
      Number(data.count || allPastors.length);

    window.pastorLimit =
      Number(data.limit || 20);

    window.currentPastorSearch = "";

    // The pastor endpoint now controls
    // only the searchable directory.
    renderPastorDirectory(
      allPastors
    );

  } catch (err) {

    console.error(
      "Pastor load error:",
      err
    );

    const container =
      $("pastorGrid");

    if (container) {

      container.innerHTML = `
        <div class="feature-card">

          <h3>
            Unable to load pastors
          </h3>

          <p>
            ${
              err.message ||
              "Please try again later."
            }
          </p>

          <button
            type="button"
            class="btn-secondary"
            onclick="window.loadPastors()"
          >
            Try Again
          </button>

        </div>
      `;
    }
  }
}

 // =====================================
  // HELPER FUNCTIONS
  // =====================================

function setTextSafe(id, value) {
  const el = $(id);

  if (!el) return;

  el.textContent =
    Number(value || 0).toLocaleString();
}

// =====================================
// FEATURED PASTOR
// =====================================
function renderFeaturedPastor() {

  const container =
    $("featuredPastor");

  if (!container) return;

  const featured =
    networkOverview?.featured_pastor;

  if (!featured) {

    container.innerHTML = `
      <div class="feature-card">

        <h3>
          Featured pastor coming soon
        </h3>

        <p>
          A featured ministry leader will
          appear here as the XynaFaith
          community grows.
        </p>

      </div>
    `;

    return;
  }

  const location =
    featured.location ||
    [
      featured.city,
      featured.state,
      featured.country
    ]
      .filter(Boolean)
      .join(", ") ||
    "Global Ministry";

  const coverStyle =
    featured.cover_image
      ? `
        style="
          background-image:
            linear-gradient(
              rgba(15,23,42,.35),
              rgba(15,23,42,.35)
            ),
            url('${featured.cover_image}')
        "
      `
      : "";

  const avatarStyle =
    featured.profile_image
      ? `
        style="
          background-image:
            url('${featured.profile_image}')
        "
      `
      : "";

  const initial =
    String(
      featured.name ||
      "Pastor"
    )
      .charAt(0)
      .toUpperCase();

  container.innerHTML = `
    <article class="featured-pastor-card">

      <div
        class="featured-pastor-cover"
        ${coverStyle}
      ></div>

      <div class="featured-pastor-content">

        <div
          class="featured-pastor-avatar"
          ${avatarStyle}
        >
          ${
            featured.profile_image
              ? ""
              : initial
          }
        </div>

        <div class="featured-pastor-info">

          <span class="eyebrow">
            ⭐ Featured Pastor
          </span>

          <h3>
            ${featured.name || "Pastor"}
          </h3>

          <p>
            ${
              featured.church_name ||
              "XynaFaith Ministry"
            }
          </p>

          <div class="featured-pastor-meta">

            <span>
              📍 ${location}
            </span>

            ${
              featured.denomination
                ? `
                  <span>
                    ✝ ${featured.denomination}
                  </span>
                `
                : ""
            }

            ${
              featured.ministry_focus
                ? `
                  <span>
                    🙏 ${featured.ministry_focus}
                  </span>
                `
                : ""
            }

          </div>

          <div class="featured-pastor-meta">

            <span>
              👥 ${Number(
                featured.followers || 0
              ).toLocaleString()}
              followers
            </span>

            <span>
              📖 ${Number(
                featured.sermon_count || 0
              ).toLocaleString()}
              sermons
            </span>

          </div>

        </div>

        <div class="featured-pastor-actions">

          <button
            type="button"
            class="btn-primary"
            onclick="
              openPastorProfile(
                ${featured.id}
              )
            "
          >
            View Profile
          </button>

          <button
            type="button"
            class="${
              featured.is_following
                ? "btn-secondary"
                : "btn-primary"
            }"
            onclick="
              ${
                    featured.is_following
                  ? `unfollowPastor(${featured.id}, this)`
                  : `followPastor(${featured.id}, this)`
              }
            "
          >
            ${
              featured.is_following
                ? "Following"
                : "Follow"
            }
          </button>

        </div>

      </div>

    </article>
  `;
}

function renderPastorDirectory(pastors) {
  const container = $("pastorGrid");

  if (!container) return;

      if (!pastors.length) {

      const hasActiveSearch =
        Boolean(
          window.currentPastorSearch ||
          activePastorFilter !== "all"
        );

      container.innerHTML = `
        <div class="feature-card">

          <h3>
            ${
              hasActiveSearch
                ? "No pastors matched your search"
                : "No pastors are available yet"
            }
          </h3>

          <p>
            ${
              hasActiveSearch
                ? `
                  Try another name, denomination,
                  country, church, or ministry focus.
                `
                : `
                  Pastor profiles will appear here
                  as ministry leaders join XynaFaith.
                `
            }
          </p>

          ${
            hasActiveSearch
              ? `
                <button
                  type="button"
                  class="btn-secondary"
                  onclick="clearPastorDirectorySearch()"
                >
                  Clear Search
                </button>
              `
              : ""
          }

        </div>
      `;

      return;
    }

  container.innerHTML = `
  ${pastors.map(pastorCardHTML).join("")}

  ${
    window.pastorHasMore
      ? `
        <div class="load-more-wrap pastor-load-more">
          <button class="btn-secondary" onclick="loadMorePastors()">
            Load More Pastors
          </button>
        </div>
      `
      : ""
  }
`;
}

function pastorCardHTML(pastor) {
  const location =
    pastor.location ||
    [pastor.city, pastor.state, pastor.country].filter(Boolean).join(", ") ||
    "Global Ministry";

  const coverStyle = pastor.cover_image
    ? `style="background-image: linear-gradient(rgba(15,23,42,.25), rgba(15,23,42,.25)), url('${pastor.cover_image}')"`
    : "";

  const avatarStyle = pastor.profile_image
    ? `style="background-image: url('${pastor.profile_image}')"`
    : "";

  const churchLogoStyle = pastor.church_logo
    ? `style="background-image: url('${pastor.church_logo}')"`
    : "";

  return `
    <article class="pastor-card-v3">

      <div class="pastor-card-v3-cover" ${coverStyle}></div>

      <div class="pastor-card-v3-body">

        <div class="pastor-card-v3-avatar" ${avatarStyle}>
          ${pastor.profile_image ? "" : (pastor.name || "P").charAt(0).toUpperCase()}
        </div>

        <div class="pastor-card-v3-header">
          <div>
            <h3>${pastor.name || "Pastor"}</h3>
            <p>${pastor.church_name || "XynaFaith Ministry"}</p>
          </div>

          ${
            pastor.is_verified
              ? `<span class="pastor-card-verify">✓</span>`
              : `<span class="pastor-card-verify muted">Pastor</span>`
          }
        </div>

        <div class="pastor-card-v3-meta">
          <span>📍 ${location}</span>
          ${pastor.denomination ? `<span>✝ ${pastor.denomination}</span>` : ""}
          ${pastor.ministry_focus ? `<span>🙏 ${pastor.ministry_focus}</span>` : ""}
        </div>

        <p class="pastor-card-v3-bio">
          ${
            pastor.bio
              ? `${pastor.bio.substring(0, 120)}${pastor.bio.length > 120 ? "..." : ""}`
              : "Serving the XynaFaith community through ministry, prayer, and the Word."
          }
        </p>

        ${
          pastor.church_name
            ? `
              <div class="pastor-card-v3-church">
                <div class="pastor-card-v3-logo" ${churchLogoStyle}>
                  ${pastor.church_logo ? "" : "⛪"}
                </div>
                <div>
                  <strong>${pastor.church_name}</strong>
                  <span>${location}</span>
                </div>
              </div>
            `
            : ""
        }

        <div class="pastor-card-v3-stats">
          <div>
            <strong>${pastor.followers || 0}</strong>
            <span>Followers</span>
          </div>

          <div>
            <strong>${pastor.sermon_count || 0}</strong>
            <span>Sermons</span>
          </div>

          <div>
            <strong>${pastor.years_in_ministry || 0}</strong>
            <span>Years</span>
          </div>
        </div>

        <div class="pastor-card-v3-actions">
          <button
            class="btn-secondary"
            onclick="event.stopPropagation(); openPastorProfile(${pastor.id})"
          >
            View Profile
          </button>

          <button
            class="${pastor.is_following ? "btn-secondary" : "btn-primary"}"
            onclick="event.stopPropagation(); ${
                    pastor.is_following
                      ? `unfollowPastor(${pastor.id}, this)`
                      : `followPastor(${pastor.id}, this)`
                  }"
            }"
          >
            ${pastor.is_following ? "Following" : "Follow"}
          </button>
        </div>

      </div>

    </article>
  `;
}
  // =====================================
  // PROFILE PAGE
  // =====================================
async function loadProfilePage() {
  try {
    const res = await apiFetch("/api/v1/pastor-profile/me");

    if (!res.ok) {
      throw new Error("Failed to load profile");
    }

    const profile = await res.json();
    window.currentPastorProfile = profile;

    setValue("profileBio", profile.bio);
    setValue("missionStatement", profile.mission_statement);
    setValue("churchName", profile.church_name);
    setValue("churchLogo", profile.church_logo);
    setValue("churchSize", profile.church_size);
    setValue("ministryFocus", profile.ministry_focus);
    setValue("specialties", profile.specialties);
    setValue("denomination", profile.denomination);
    setValue("yearsInMinistry", profile.years_in_ministry);
    setValue("ordinationYear", profile.ordination_year);

    setValue("profileLocation", profile.location);
    setValue("profileCity", profile.city);
    setValue("profileState", profile.state);
    setValue("profileCountry", profile.country);
    setValue("timeZone", profile.time_zone);

    setValue("profileWebsite", profile.website);
    setValue("profilePhone", profile.phone);
    setValue("emailPublic", profile.email_public);

    setValue("facebook", profile.facebook);
    setValue("youtube", profile.youtube);
    setValue("instagram", profile.instagram);
    setValue("twitter", profile.twitter);

    setValue("profileImage", profile.profile_image);
    setValue("coverImage", profile.cover_image);
    setValue("favoriteScripture", profile.favorite_scripture);
    setValue("languages", profile.languages);
    setValue("serviceTimes", profile.service_times);
    setValue("profileSlug", profile.slug);
    updatePublicProfileLinkPreview();

    setChecked("acceptsPrayerRequests", profile.accepts_prayer_requests);
    setChecked("allowDirectMessages", profile.allow_direct_messages);

    setValue("profileVisibility", profile.visibility || "public");
    updateVisibilityDescription?.();

    updateProfilePreview();

  } catch (err) {
    console.error("Profile page error:", err);
    showToast?.("Failed to load profile", "error");
  }
}

  // =====================================
  // SAVE PROFILE
  // =====================================
async function saveProfile() {
  try {
    const payload = {
      bio: $("profileBio")?.value || "",
      mission_statement: $("missionStatement")?.value || "",

      church_name: $("churchName")?.value || "",
      church_logo: $("churchLogo")?.value || "",
      church_size: $("churchSize")?.value || "",

      ministry_focus: $("ministryFocus")?.value || "",
      specialties: $("specialties")?.value || "",
      denomination: $("denomination")?.value || "",
      years_in_ministry: Number($("yearsInMinistry")?.value || 0),
      ordination_year: Number($("ordinationYear")?.value || 0),

      location: $("profileLocation")?.value || "",
      city: $("profileCity")?.value || "",
      state: $("profileState")?.value || "",
      country: $("profileCountry")?.value || "",
      time_zone: $("timeZone")?.value || "",

      website: $("profileWebsite")?.value || "",
      phone: $("profilePhone")?.value || "",
      email_public: $("emailPublic")?.value || "",

      facebook: $("facebook")?.value || "",
      youtube: $("youtube")?.value || "",
      instagram: $("instagram")?.value || "",
      twitter: $("twitter")?.value || "",

      profile_image: $("profileImage")?.value || "",
      cover_image: $("coverImage")?.value || "",

      favorite_scripture: $("favoriteScripture")?.value || "",
      languages: $("languages")?.value || "",
      service_times: $("serviceTimes")?.value || "",

      accepts_prayer_requests: $("acceptsPrayerRequests")?.checked ?? true,
      allow_direct_messages: $("allowDirectMessages")?.checked ?? true,
      visibility: $("profileVisibility")?.value || "public",

      slug: ($("profileSlug")?.value || "")
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9-]/g, "-")
        .replace(/-+/g, "-")
        .replace(/^-|-$/g, "")
    };

    const saveRes = await apiFetch("/api/v1/pastor-profile/me", {
      method: "PUT",
      body: JSON.stringify(payload)
    });

    const data = await saveRes.json();

    if (!saveRes.ok) {
      throw new Error(data.detail || "Save failed");
    }

    if (data.profile) {
      window.currentPastorProfile = data.profile;
    }

    showToast?.("Profile updated successfully", "success");

    return true;

  } catch (err) {
    console.error("Profile save error:", err);
    showToast?.(err.message || "Save failed", "error");

    return false;
  }
}

  // =====================================
  // UpdateProfilePreview
  // =====================================
window.updateVisibilityDescription = function () {
  const value = $("profileVisibility")?.value || "public";
  const help = $("visibilityDescription");

  if (!help) return;

  if (value === "public") {
    help.textContent = "🌍 Anyone can discover your ministry profile.";
  } else if (value === "members") {
    help.textContent = "👥 Only signed-in XynaFaith members and pastors can discover your ministry.";
  } else if (value === "private") {
    help.textContent = "🔒 Hidden from the Network. Only you and administrators can access this profile.";
  }
};



function updateProfilePreview() {
  const profileImage = $("profileImage")?.value;
  const coverImage = $("coverImage")?.value;
  const churchLogo = $("churchLogo")?.value;

  const avatarPreview = $("avatarPreview");
  const coverPreview = $("coverPreview");

  const avatarUploadPreview = $("avatarUploadPreview");
  const coverUploadPreview = $("coverUploadPreview");
  const churchLogoPreview = $("churchLogoPreview");

  // Top hero avatar preview
  if (avatarPreview) {
    if (profileImage) {
      avatarPreview.style.backgroundImage = `url('${profileImage}')`;
      avatarPreview.style.backgroundSize = "cover";
      avatarPreview.style.backgroundPosition = "center";
      avatarPreview.textContent = "";
    } else {
      avatarPreview.style.backgroundImage = "";
      avatarPreview.textContent = "P";
    }
  }

  // Top hero cover preview
  if (coverPreview) {
    if (coverImage) {
      coverPreview.style.backgroundImage = `
        linear-gradient(rgba(15,23,42,.25), rgba(15,23,42,.25)),
        url('${coverImage}')
      `;
      coverPreview.style.backgroundSize = "cover";
      coverPreview.style.backgroundPosition = "center";
    } else {
      coverPreview.style.backgroundImage = "";
    }
  }

  // Upload card avatar preview
  if (avatarUploadPreview) {
    if (profileImage) {
      avatarUploadPreview.style.backgroundImage = `url('${profileImage}')`;
      avatarUploadPreview.textContent = "";
    } else {
      avatarUploadPreview.style.backgroundImage = "";
      avatarUploadPreview.textContent = "P";
    }
  }

  // Upload card cover preview
  if (coverUploadPreview) {
    if (coverImage) {
      coverUploadPreview.style.backgroundImage = `
        linear-gradient(rgba(15,23,42,.35), rgba(15,23,42,.35)),
        url('${coverImage}')
      `;
    } else {
      coverUploadPreview.style.backgroundImage = "";
    }
  }

  // Church logo preview
  if (churchLogoPreview) {
    if (churchLogo) {
      churchLogoPreview.style.backgroundImage = `url('${churchLogo}')`;
      churchLogoPreview.textContent = "";
    } else {
      churchLogoPreview.style.backgroundImage = "";
      churchLogoPreview.textContent = "⛪";
    }
  }
}

// =====================================
// IMAGE UPLOAD
// =====================================

window.uploadPastorProfileImage = async function (type) {

  let inputId = "";

  switch (type) {
    case "profile":
      inputId = "profileImageFile";
      break;

    case "cover":
      inputId = "coverImageFile";
      break;

    case "churchLogo":
      inputId = "churchLogoFile";
      break;

    default:
      return;
  }

  const fileInput = $(inputId);

  if (!fileInput?.files?.length) {
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {

    showToast?.("Uploading image...", "info");

    const response = await fetch(
      "/sermon/pastor-image",
      {
        method: "POST",
        headers: {
          Authorization:
            `Bearer ${getToken()}`
        },
        body: formData
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail || "Upload failed"
      );
    }

    switch (type) {

      case "profile":
        $("profileImage").value = data.url;
        break;

      case "cover":
        $("coverImage").value = data.url;
        break;

      case "churchLogo":
        $("churchLogo").value = data.url;
        break;

    }

    updateProfilePreview();

    showToast?.(
      "Image uploaded successfully",
      "success"
    );

  } catch (err) {

    console.error(err);

    showToast?.(
      err.message,
      "error"
    );

  }

};

window.updateProfilePreview = updateProfilePreview;

  // =====================================
  // PASTOR PROFILE PAGE
  // =====================================
async function loadPastorProfilePage() {
  try {
    const pastorId = localStorage.getItem("selected_pastor_id");

    if (!pastorId) return;

    const res = await apiFetch(`/api/v1/pastor-profile/${pastorId}`);

    if (!res.ok) {
      throw new Error("Failed to load profile");
    }

    const profile = await res.json();

    const setText = (id, value, fallback = "—") => {
      const el = $(id);
      if (el) el.textContent = value || fallback;
    };

    const editBtn = $("editProfileBtn");
    const isOwner = window.currentUser?.id === profile.user_id;
    const isAdmin = window.currentUser?.role === "admin";

    if (editBtn) {
      editBtn.classList.toggle("hidden", !isOwner && !isAdmin);
    }

    setText("pastorName", profile.name, "Pastor");
    setText("pastorBio", profile.bio, "Ministry profile");
    setText("fullBioView", profile.bio);
    setText("missionView", profile.mission_statement);
    setText("churchNameView", profile.church_name);
    setText("ministryFocusView", profile.ministry_focus);
    setText("specialtiesView", profile.specialties);
    setText("languagesView", profile.languages);
    setText("favoriteScriptureView", profile.favorite_scripture);
    setText("serviceTimesView", profile.service_times);
    setText("followersView", profile.followers || 0, "0");
    setText("sermonCountView", profile.sermons?.length || 0, "0");
    setText("yearsView", profile.years_in_ministry || 0, "0");
    setText("countryView", profile.country);
    setText("denominationView", profile.denomination);
    setText(
      "locationView",
      profile.location ||
        [profile.city, profile.state, profile.country]
          .filter(Boolean)
          .join(", ")
    );

    const verifiedBadge = $("verifiedBadge");
    if (verifiedBadge) {
      verifiedBadge.classList.toggle("hidden", !profile.is_verified);
    }

    const visibilityBadge = $("visibilityBadge");
    if (visibilityBadge) {
      if (!isOwner && !isAdmin) {
        visibilityBadge.classList.add("hidden");
      } else {
        visibilityBadge.classList.remove("hidden");

        switch (profile.visibility) {
          case "members":
            visibilityBadge.textContent = "👥 Members Only";
            break;

          case "private":
            visibilityBadge.textContent = "🔒 Private Ministry";
            break;

          default:
            visibilityBadge.textContent = "🌍 Public Ministry";
        }
      }
    }

    const avatar = $("publicAvatar");
    if (avatar) {
      if (profile.profile_image) {
        avatar.style.backgroundImage = `url('${profile.profile_image}')`;
        avatar.style.backgroundSize = "cover";
        avatar.style.backgroundPosition = "center";
        avatar.style.backgroundRepeat = "no-repeat";
        avatar.textContent = "";
      } else {
        avatar.style.backgroundImage = "";
        avatar.textContent = (profile.name || "P").charAt(0).toUpperCase();
      }
    }

    const cover = $("publicCover");
    if (cover) {
      if (profile.cover_image) {
        cover.style.backgroundImage = `
          linear-gradient(rgba(15,23,42,.35), rgba(15,23,42,.35)),
          url('${profile.cover_image}')
        `;
        cover.style.backgroundSize = "cover";
        cover.style.backgroundPosition = "center";
        cover.style.backgroundRepeat = "no-repeat";
      } else {
        cover.style.backgroundImage = "";
      }
    }

    const churchBrandRow = $("churchBrandRow");
    const churchLogoPublic = $("churchLogoPublic");
    const churchBrandName = $("churchBrandName");
    const churchCityView = $("churchCityView");
    const churchCountryView = $("churchCountryView");

    if (churchBrandRow) {
      churchBrandRow.classList.toggle("hidden", !profile.church_name);
    }

    if (churchBrandName) {
      churchBrandName.textContent = profile.church_name || "";
    }

    if (churchCityView) {
      churchCityView.textContent = profile.city || "";
    }

    if (churchCountryView) {
      churchCountryView.textContent = profile.country || "";
    }

    if (churchLogoPublic) {
      if (profile.church_logo) {
        churchLogoPublic.style.backgroundImage = `url('${profile.church_logo}')`;
        churchLogoPublic.style.backgroundSize = "cover";
        churchLogoPublic.style.backgroundPosition = "center";
        churchLogoPublic.style.backgroundRepeat = "no-repeat";
        churchLogoPublic.textContent = "";
      } else {
        churchLogoPublic.style.backgroundImage = "";
        churchLogoPublic.textContent = "⛪";
      }
    }

    const setLink = (id, url) => {
      const el = $(id);
      if (!el) return;

      if (!url) {
        el.style.display = "none";
        return;
      }

      el.href = url.startsWith("http") ? url : `https://${url}`;
      el.style.display = "inline-flex";
    };

    setLink("websiteView", profile.website);
    setLink("facebookView", profile.facebook);
    setLink("youtubeView", profile.youtube);
    setLink("instagramView", profile.instagram);
    setLink("twitterView", profile.twitter);

    const sermonsContainer = $("pastorSermons");

    if (sermonsContainer) {
      const sermons = profile.sermons || [];

      if (!sermons.length) {
        sermonsContainer.innerHTML = `<p>No sermons yet.</p>`;
      } else {
        sermonsContainer.innerHTML = sermons.map(s => {
          const dateText = s.created_at
            ? new Date(s.created_at).toLocaleDateString()
            : "";

          return `
            <div
              class="public-sermon-card clickable"
              onclick="window.openSermon(${s.id})"
            >
              <h3>${s.title || "Untitled Sermon"}</h3>
              <small>${dateText}</small>
            </div>
          `;
        }).join("");
      }
    }

  } catch (err) {
    console.error("Pastor profile error:", err);
    showToast?.(err.message || "Failed to load profile", "error");
  }
}


window.sharePastorProfile = function () {
  const pastorId = localStorage.getItem("selected_pastor_id");
  const url = `${window.location.origin}/faith/#pastor-${pastorId || ""}`;

  if (navigator.share) {
    navigator.share({
      title: "XynaFaith Pastor Profile",
      url
    });
    return;
  }

  navigator.clipboard?.writeText(url);
  showToast?.("Profile link copied", "success");
};


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

window.previewMyPastorProfile = async function () {
  const saved = await saveProfile();

  if (!saved) return;

  if (!window.currentPastorProfile?.user_id) {
    showToast?.("Profile not loaded.", "error");
    return;
  }

  localStorage.setItem(
    "selected_pastor_id",
    window.currentPastorProfile.user_id
  );

  navigate("pastor-profile");
};

window.filterPastorDirectory = async function () {
  try {
    const searchText = ($("pastorSearchInput")?.value || "").trim();

    const filterText =
      activePastorFilter && activePastorFilter !== "all"
        ? activePastorFilter
        : "";

    const q = [searchText, filterText]
      .filter(Boolean)
      .join(" ");

    const params = new URLSearchParams({
      limit: 20,
      offset: 0
    });

    if (q) {
      params.set("q", q);
    }

    const res = await apiFetch(`/api/v1/pastors/?${params.toString()}`);

    if (!res.ok) {
      throw new Error("Search failed");
    }

    const data = await res.json();

    allPastors = data.items || [];

    window.pastorHasMore = data.has_more;
    window.pastorOffset = data.offset + data.count;
    window.pastorLimit = data.limit;
    window.currentPastorSearch = q;

    renderPastorDirectory(allPastors);

  } catch (err) {
    console.error("Pastor search error:", err);
    showToast?.("Could not search pastors", "error");
  }
};

window.setPastorDirectoryFilter = function (filter) {
  activePastorFilter = filter || "all";

  document.querySelectorAll(".network-filter-row .filter-chip").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.filter === activePastorFilter);
  });

  window.filterPastorDirectory();
};


window.loadMorePastors = async function () {
  try {
    const limit = window.pastorLimit || 20;
    const offset = window.pastorOffset || allPastors.length;
    const q = window.currentPastorSearch || "";

    const params = new URLSearchParams({
      limit,
      offset
    });

    if (q) {
      params.set("q", q);
    }

    const res = await apiFetch(`/api/v1/pastors/?${params.toString()}`);

    if (!res.ok) {
      throw new Error("Failed to load more pastors");
    }

    const data = await res.json();

  // =====================================
  // Merge without duplicates
  // =====================================
  const existingIds = new Set(
    allPastors.map(p => p.id)
  );

  const newPastors =
    (data.items || []).filter(
      pastor => !existingIds.has(pastor.id)
    );

  allPastors = [
    ...allPastors,
    ...newPastors
  ];

    window.pastorHasMore = data.has_more;
    window.pastorOffset = data.offset + data.count;
    window.pastorLimit = data.limit;

    renderPastorDirectory(allPastors);

  } catch (err) {
    console.error("Load more pastors error:", err);
    showToast?.("Could not load more pastors", "error");
  }
};


// =====================================
// LOAD NETWORK OVERVIEW
// =====================================
async function loadNetworkOverview() {

  try {

    const response =
      await apiFetch(
        "/api/v1/network/overview"
      );

    if (!response.ok) {

      let message =
        "Unable to load community overview.";

      try {

        const errorData =
          await response.json();

        message =
          errorData.detail ||
          message;

      } catch (_) {
        // Preserve the default message.
      }

      throw new Error(message);
    }

    const data =
      await response.json();

    networkOverview =
      data && typeof data === "object"
        ? data
        : {};

    const renderers = [
      {
        name: "platform stats",
        run: renderPlatformStats
      },
      {
        name: "featured pastor",
        run: renderFeaturedPastor
      },
      {
        name: "community activity",
        run: renderCommunityActivity
      },
      {
        name: "recent prayers",
        run: renderRecentPrayers
      },
      {
        name: "trending sermons",
        run: renderTrendingSermons
      }
    ];

    renderers.forEach(({ name, run }) => {
      try {
        run();
      } catch (error) {
        console.error(
          `Failed to render ${name}:`,
          error
        );
      }
    });

    return networkOverview;

  } catch (err) {

    console.error(
      "Network overview error:",
      err
    );

    networkOverview = null;

    renderNetworkOverviewError();

    throw err;
  }
}

// =====================================
// PLATFORM STATISTICS
// =====================================
function renderPlatformStats() {

  const stats =
    networkOverview?.platform || {};

  setTextSafe(
    "networkPastorCount",
    stats.pastors
  );

  setTextSafe(
    "networkMemberCount",
    stats.members
  );

  setTextSafe(
    "networkChurchCount",
    stats.churches
  );

  setTextSafe(
    "networkSermonCount",
    stats.sermons
  );

  setTextSafe(
    "networkPrayerCount",
    stats.prayers
  );

  setTextSafe(
    "networkConnectionCount",
    stats.connections
  );
}

// =====================================
// COMMUNITY ACTIVITY
// =====================================
function renderCommunityActivity() {

  const container =
    $("communityActivity");

  if (!container) return;

  const activity =
    Array.isArray(
      networkOverview?.activity
    )
      ? networkOverview.activity
      : [];

  if (!activity.length) {

    container.innerHTML = `
      <div class="feature-card">

        <h3>
          Community activity
        </h3>

        <p>
          New community activity will
          appear here.
        </p>

      </div>
    `;

    return;
  }

  container.innerHTML =
    activity.map(item => `

      <div class="activity-card">

        <div class="activity-icon">
          ${item.icon || "✨"}
        </div>

        <div class="activity-content">

          <strong>
            ${
              item.title ||
              "Community update"
            }
          </strong>

          <p>
            ${item.description || ""}
          </p>

          ${
            item.created_at
              ? `
                <small>
                  ${formatDate(
                    item.created_at
                  )}
                </small>
              `
              : ""
          }

        </div>

      </div>

    `).join("");
}

// =====================================
// RECENT PRAYERS
// =====================================
function renderRecentPrayers() {

  const container =
    $("prayerWall");

  if (!container) return;

  const prayers =
    Array.isArray(
      networkOverview?.recent_prayers
    )
      ? networkOverview.recent_prayers
      : [];

  if (!prayers.length) {

    container.innerHTML = `
      <p>
        No prayer activity yet.
      </p>
    `;

    return;
  }

  container.innerHTML =
    prayers.map(prayer => `

      <div class="prayer-item">

        <strong>
          ${
            prayer.user_name ||
            "XynaFaith Member"
          }
        </strong>

        ${
          prayer.created_at
            ? `
              <small>
                ${formatDate(
                  prayer.created_at
                )}
              </small>
            `
            : ""
        }

        <p>
          ${prayer.message || ""}
        </p>

      </div>

    `).join("");
}

// =====================================
// TRENDING SERMONS
// =====================================
function renderTrendingSermons() {

  const container =
    $("trendingSermons");

  // Some versions of the Network page may
  // still use loadTopSermons() and therefore
  // may not yet contain this container.
  if (!container) return;

  const sermons =
    Array.isArray(
      networkOverview?.trending_sermons
    )
      ? networkOverview.trending_sermons
      : [];

  if (!sermons.length) {

    container.innerHTML = `
      <div class="feature-card">

        <h3>
          No trending sermons yet
        </h3>

        <p>
          Popular sermons will appear
          here as the community engages.
        </p>

      </div>
    `;

    return;
  }

  container.innerHTML =
    sermons.map(sermon => `

      <article class="feature-card sermon-feed-card">

        <h3>
          ${
            sermon.title ||
            "Untitled Sermon"
          }
        </h3>

        <small>
          By ${
            sermon.author_name ||
            sermon.pastor_name ||
            "XynaFaith Pastor"
          }
        </small>

        ${
          sermon.scripture
            ? `
              <p>
                ${sermon.scripture}
              </p>
            `
            : ""
        }

        ${
          sermon.id
            ? `
              <button
                type="button"
                class="btn-secondary"
                onclick="
                  window.openSermon(
                    ${sermon.id}
                  )
                "
              >
                Read Sermon
              </button>
            `
            : ""
        }

      </article>

    `).join("");
}


// =====================================
// OVERVIEW ERROR STATE
// =====================================
function renderNetworkOverviewError() {

  [
    "networkPastorCount",
    "networkMemberCount",
    "networkChurchCount",
    "networkSermonCount",
    "networkPrayerCount",
    "networkConnectionCount"
  ].forEach(id => {

    const el = $(id);

    if (el) {
      el.textContent = "—";
    }
  });

  const featured =
    $("featuredPastor");

  if (featured) {

    featured.innerHTML = `
      <div class="feature-card">

        <h3>
          Community overview unavailable
        </h3>

        <p>
          The pastor directory may still
          be available below.
        </p>

        <button
          type="button"
          class="btn-secondary"
          onclick="window.loadNetworkPage()"
        >
          Try Again
        </button>

      </div>
    `;
  }

  const activity =
    $("communityActivity");

  if (activity) {

    activity.innerHTML = `
      <p>
        Community activity could not
        be loaded.
      </p>
    `;
  }
}


window.clearPastorDirectorySearch =
  function () {

    const searchInput =
      $("pastorSearchInput");

    if (searchInput) {
      searchInput.value = "";
    }

    activePastorFilter = "all";

    window.currentPastorSearch = "";

    document
      .querySelectorAll(
        ".network-filter-row .filter-chip"
      )
      .forEach(button => {

        button.classList.toggle(
          "active",
          button.dataset.filter === "all"
        );
      });

    window.filterPastorDirectory();
  };

function updatePublicProfileLinkPreview() {
  const slug = ($("profileSlug")?.value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");

  const text = $("publicProfileLinkText");

  if (!text) return;

  if (!slug) {
    text.textContent = "Your public profile link will appear after you save a slug.";
    return;
  }

  text.textContent = `${window.location.origin}/pastor/${slug}`;
}

window.updatePublicProfileLinkPreview = updatePublicProfileLinkPreview;

window.copyPublicProfileLink = function () {
  const text = $("publicProfileLinkText")?.textContent;

  if (!text || text.includes("will appear")) {
    showToast?.("Add a public slug first.", "error");
    return;
  }

  navigator.clipboard?.writeText(text);
  showToast?.("Public profile link copied.", "success");
};

  // =====================================
  // GLOBAL EXPORTS
  // =====================================
  window.loadNetworkOverview =
    loadNetworkOverview;

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


    // =====================================
// INITIALIZE NETWORK SEARCH
// =====================================
function initializeNetworkSearch() {

  const searchInput =
    $("pastorSearchInput");

  if (!searchInput)
    return;

  // Prevent duplicate listeners if the page
  // is initialized more than once.
  if (searchInput.dataset.initialized)
    return;

  searchInput.dataset.initialized = "true";

  let debounceTimer;

  searchInput.addEventListener(
    "input",
    () => {

      clearTimeout(
        debounceTimer
      );

      debounceTimer =
        setTimeout(() => {

          filterPastorDirectory();

        }, 350);

    }
  );

}

})();