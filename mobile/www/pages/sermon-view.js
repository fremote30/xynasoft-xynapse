const urlParams = new URLSearchParams(window.location.search);
const id = urlParams.get("id");

fetch(`/api/sermon/${id}`)
  .then(res => res.json())
  .then(data => {

    document.getElementById("title").value = data.title;
    document.getElementById("content").value = data.content;
  });


document.getElementById("saveBtn").onclick = () => {

  fetch(`/api/sermon/update/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: document.getElementById("title").value,
      content: document.getElementById("content").value
    })
  })
  .then(() => alert("Saved!"));
};