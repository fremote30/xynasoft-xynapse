// =====================================
// MEMBER-PROFILE.JS
// Member profile editor
// =====================================

(() => {
  const $ = (id) => document.getElementById(id);

  function setValue(id, value) {
    const el = $(id);

    if (el) {
      el.value = value ?? "";
    }
  }

  function setChecked(id, value, fallback = true) {
    const el = $(id);

    if (!el) return;

    el.checked =
      value === null || value === undefined
        ? fallback
        : Boolean(value);
  }

  function normalizeSlug(value) {
    return String(value || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9-]/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "");
  }

  function memberInitial() {
    const name =
      window.currentUser?.name ||
      window.currentMemberProfile?.name ||
      "Member";

    return name.charAt(0).toUpperCase();
  }

  // =====================================
  // PROFILE IMAGE PREVIEW
  // =====================================
  function updateMemberProfilePreview() {
    const imageUrl = $("memberProfileImage")?.value || "";
    const initial = memberInitial();

    const previews = [
      $("memberAvatarPreview"),
      $("memberAvatarUploadPreview")
    ];

    previews.forEach(preview => {
      if (!preview) return;

      if (imageUrl) {
        preview.style.backgroundImage = `url('${imageUrl}')`;
        preview.style.backgroundSize = "cover";
        preview.style.backgroundPosition = "center";
        preview.style.backgroundRepeat = "no-repeat";
        preview.textContent = "";
      } else {
        preview.style.backgroundImage = "";
        preview.textContent = initial;
      }
    });
  }

  window.updateMemberProfilePreview =
    updateMemberProfilePreview;

  // =====================================
  // VISIBILITY DESCRIPTION
  // =====================================
  window.updateMemberVisibilityDescription = function () {
    const visibility =
      $("memberVisibility")?.value || "members";

    const help =
      $("memberVisibilityDescription");

    if (!help) return;

    switch (visibility) {
      case "public":
        help.textContent =
          "🌍 Anyone can view your member profile.";
        break;

      case "private":
        help.textContent =
          "🔒 Your profile is visible only to you and XynaFaith administrators.";
        break;

      default:
        help.textContent =
          "👥 Only signed-in XynaFaith users can view your profile.";
    }
  };

  // =====================================
  // PUBLIC LINK PREVIEW
  // =====================================
  function updateMemberProfileLinkPreview() {
    const slug = normalizeSlug(
      $("memberSlug")?.value
    );

    const text =
      $("memberProfileLinkText");

    if (!text) return;

    if (!slug) {
      text.textContent =
        "Your member profile link will appear after you add a slug.";
      return;
    }

    text.textContent =
      `${window.location.origin}/faith/#member-${slug}`;
  }

  window.updateMemberProfileLinkPreview =
    updateMemberProfileLinkPreview;

  window.copyMemberProfileLink = async function () {
    const slug = normalizeSlug(
      $("memberSlug")?.value
    );

    if (!slug) {
      showToast?.(
        "Add a member profile slug first.",
        "error"
      );
      return;
    }

    const url =
      `${window.location.origin}/faith/#member-${slug}`;

    try {
      await navigator.clipboard.writeText(url);

      showToast?.(
        "Member profile link copied.",
        "success"
      );
    } catch (err) {
      console.error(
        "Member link copy failed:",
        err
      );

      showToast?.(
        "Could not copy profile link.",
        "error"
      );
    }
  };

  // =====================================
  // LOAD MEMBER PROFILE
  // =====================================
  async function loadMemberProfilePage() {
    try {
      const res = await apiFetch(
        "/api/v1/member-profile/me"
      );

      const data = await res.json();

      if (!res.ok) {
        throw new Error(
          data.detail ||
          "Failed to load member profile"
        );
      }

      window.currentMemberProfile = data;

      setValue(
        "memberProfileImage",
        data.profile_image
      );

      setValue(
        "memberBio",
        data.bio
      );

      setValue(
        "memberFavoriteScripture",
        data.favorite_scripture
      );

      setValue(
        "memberSlug",
        data.slug
      );

      setValue(
        "memberCity",
        data.city
      );

      setValue(
        "memberState",
        data.state
      );

      setValue(
        "memberCountry",
        data.country
      );

      setValue(
        "memberLanguages",
        data.languages
      );

      setValue(
        "memberChurchName",
        data.church_name
      );

      setValue(
        "memberMinistryInterests",
        data.ministry_interests
      );

      setValue(
        "memberPrayerInterests",
        data.prayer_interests
      );

      setValue(
        "memberVisibility",
        data.visibility || "members"
      );

      setChecked(
        "memberAllowDirectMessages",
        data.allow_direct_messages,
        true
      );

      setChecked(
        "memberReceiveNotifications",
        data.receive_notifications,
        true
      );

      updateMemberProfilePreview();
      updateMemberProfileLinkPreview();
      window.updateMemberVisibilityDescription();

    } catch (err) {
      console.error(
        "Member profile load error:",
        err
      );

      showToast?.(
        err.message ||
        "Failed to load member profile",
        "error"
      );
    }
  }

  // =====================================
  // SAVE MEMBER PROFILE
  // =====================================
  async function saveMemberProfile() {
    try {
      const slug = normalizeSlug(
        $("memberSlug")?.value
      );

      const payload = {
        bio:
          $("memberBio")?.value.trim() || "",

        profile_image:
          $("memberProfileImage")?.value || "",

        favorite_scripture:
          $("memberFavoriteScripture")?.value.trim() || "",

        city:
          $("memberCity")?.value.trim() || "",

        state:
          $("memberState")?.value.trim() || "",

        country:
          $("memberCountry")?.value.trim() || "",

        languages:
          $("memberLanguages")?.value.trim() || "",

        church_name:
          $("memberChurchName")?.value.trim() || "",

        ministry_interests:
          $("memberMinistryInterests")?.value.trim() || "",

        prayer_interests:
          $("memberPrayerInterests")?.value.trim() || "",

        visibility:
          $("memberVisibility")?.value || "members",

        allow_direct_messages:
          $("memberAllowDirectMessages")?.checked ?? true,

        receive_notifications:
          $("memberReceiveNotifications")?.checked ?? true,

        slug
      };

      const saveButton =
        document.querySelector(
          "#memberProfileForm button[type='submit']"
        );

      if (saveButton) {
        saveButton.disabled = true;
        saveButton.textContent = "Saving...";
      }

      const res = await apiFetch(
        "/api/v1/member-profile/me",
        {
          method: "PUT",
          body: JSON.stringify(payload)
        }
      );

      const data = await res.json();

      if (!res.ok) {
        throw new Error(
          data.detail ||
          "Failed to save member profile"
        );
      }

      if (data.profile) {
        window.currentMemberProfile =
          data.profile;

        setValue(
          "memberSlug",
          data.profile.slug
        );
      }

      updateMemberProfileLinkPreview();

      showToast?.(
        "Member profile updated successfully.",
        "success"
      );

      return true;

    } catch (err) {
      console.error(
        "Member profile save error:",
        err
      );

      showToast?.(
        err.message ||
        "Failed to save member profile",
        "error"
      );

      return false;

    } finally {
      const saveButton =
        document.querySelector(
          "#memberProfileForm button[type='submit']"
        );

      if (saveButton) {
        saveButton.disabled = false;
        saveButton.textContent =
          "Save Member Profile";
      }
    }
  }

  // =====================================
  // MEMBER IMAGE UPLOAD
  // =====================================
  window.uploadMemberProfileImage =
    async function () {

    const fileInput =
      $("memberProfileImageFile");

    const file =
      fileInput?.files?.[0];

    if (!file) return;

    const allowedTypes = [
      "image/jpeg",
      "image/png",
      "image/webp"
    ];

    if (!allowedTypes.includes(file.type)) {
      showToast?.(
        "Please choose a JPG, PNG, or WebP image.",
        "error"
      );

      fileInput.value = "";
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      showToast?.(
        "Image must be smaller than 5 MB.",
        "error"
      );

      fileInput.value = "";
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      showToast?.(
        "Uploading profile image...",
        "info"
      );

      /*
       * This temporarily reuses the authenticated image-upload
       * endpoint already used by Pastor Profiles.
       */
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
          data.detail ||
          "Image upload failed"
        );
      }

      if (!data.url) {
        throw new Error(
          "Upload completed without an image URL"
        );
      }

      setValue(
        "memberProfileImage",
        data.url
      );

      updateMemberProfilePreview();

      showToast?.(
        "Profile image uploaded successfully.",
        "success"
      );

    } catch (err) {
      console.error(
        "Member image upload error:",
        err
      );

      showToast?.(
        err.message ||
        "Could not upload profile image",
        "error"
      );

    } finally {
      if (fileInput) {
        fileInput.value = "";
      }
    }
  };

  // =====================================
  // GLOBAL EXPORTS
  // =====================================
  window.loadMemberProfilePage =
    loadMemberProfilePage;

  window.saveMemberProfile =
    saveMemberProfile;

})();