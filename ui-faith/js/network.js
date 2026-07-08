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
    
    const res = await apiFetch("/api/v1/pastors/?limit=20&offset=0");
    if (!res.ok) {
      throw new Error("Failed to load pastors");
    }

    const data = await res.json();

    allPastors = data.items || [];

    window.pastorHasMore = data.has_more;
    window.pastorOffset = data.offset + data.count;
    window.pastorLimit = data.limit;

    updateNetworkQuickStats(allPastors);
    renderFeaturedPastor(allPastors);
    renderPastorDirectory(allPastors);

  } catch (err) {
    console.error("Pastor load error:", err);

    const container = $("pastorGrid");

    if (container) {
      container.innerHTML = `
        <div class="feature-card">
          <h3>Unable to load pastors</h3>
          <p>Please try again later.</p>
        </div>
      `;
    }
  }
}

 // =====================================
  // HELPER FUNCTIONS
  // =====================================

function updateNetworkQuickStats(pastors) {
  setTextSafe("networkPastorCount", pastors.length);

  setTextSafe(
    "networkSermonCount",
    pastors.reduce(
      (sum, p) => sum + Number(p.sermon_count || 0),
      0
    )
  );

  const memberCount =
    $("memberCount")?.textContent ||
    window.lastMemberCount ||
    "0";

  setTextSafe("networkMemberCount", memberCount);

  const prayerItems =
    document.querySelectorAll(".prayer-item").length;

  setTextSafe("networkPrayerCount", prayerItems || 0);
}

function setTextSafe(id, value) {
  const el = $(id);
  if (el) el.textContent = value ?? 0;
}

function renderFeaturedPastor(pastors) {
  const container = $("featuredPastor");

  if (!container) return;

  if (!pastors.length) {
    container.innerHTML = "";
    return;
  }

  const featured = [...pastors].sort((a, b) =>
    Number(b.followers || 0) - Number(a.followers || 0)
  )[0];

  const location =
    featured.location ||
    [featured.city, featured.state, featured.country].filter(Boolean).join(", ") ||
    "Global Ministry";

  const coverStyle = featured.cover_image
    ? `style="background-image: linear-gradient(rgba(15,23,42,.35), rgba(15,23,42,.35)), url('${featured.cover_image}')"`
    : "";

  const avatarStyle = featured.profile_image
    ? `style="background-image: url('${featured.profile_image}')"`
    : "";

  container.innerHTML = `
    <article class="featured-pastor-card">

      <div class="featured-pastor-cover" ${coverStyle}></div>

      <div class="featured-pastor-content">

        <div class="featured-pastor-avatar" ${avatarStyle}>
          ${featured.profile_image ? "" : (featured.name || "P").charAt(0).toUpperCase()}
        </div>

        <div class="featured-pastor-info">
          <span class="eyebrow">⭐ Featured Pastor</span>
          <h3>${featured.name || "Pastor"}</h3>
          <p>${featured.church_name || "XynaFaith Ministry"}</p>

          <div class="featured-pastor-meta">
            <span>📍 ${location}</span>
            ${featured.denomination ? `<span>✝ ${featured.denomination}</span>` : ""}
            ${featured.ministry_focus ? `<span>🙏 ${featured.ministry_focus}</span>` : ""}
          </div>
        </div>

        <div class="featured-pastor-actions">
          <button class="btn-primary" onclick="openPastorProfile(${featured.id})">
            View Profile
          </button>

          <button
            class="${featured.is_following ? "btn-secondary" : "btn-primary"}"
            onclick="${
              featured.is_following
                ? `unfollowPastor(${featured.id})`
                : `followPastor(${featured.id})`
            }"
          >
            ${featured.is_following ? "Following" : "Follow"}
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
    container.innerHTML = `
      <div class="feature-card">
        <h3>No pastors found</h3>
        <p>Try changing your search or filter.</p>
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
                ? `unfollowPastor(${pastor.id})`
                : `followPastor(${pastor.id})`
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

    renderFeaturedPastor(allPastors);
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

    allPastors = [
      ...allPastors,
      ...(data.items || [])
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