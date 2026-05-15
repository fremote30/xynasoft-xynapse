const pastorId = localStorage.getItem("pastor_id");

fetch(`/api/sermon/my?pastor_id=${pastorId}`)
  .then(res => res.json())
  .then(data => {

    const container = document.getElementById("sermonList");

    data.forEach(sermon => {

      const div = document.createElement("div");
      div.className = "sermon-card";

      div.innerHTML = `
        <h3>${sermon.title}</h3>
        <p>${sermon.theme || ""}</p>
        <button onclick="openSermon(${sermon.id})">Open</button>
      `;

      container.appendChild(div);
    });
  });


function openSermon(id) {
  window.location.href = `/faith/sermon-view.html?id=${id}`;
}