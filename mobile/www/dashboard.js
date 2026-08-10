const API_BASE = window.location.origin

const sidebarItems = document.querySelectorAll(".sidebar li")
const view = document.getElementById("dashboard-view")


function render(page){

if(page === "sermon-studio"){

view.innerHTML = `
<h2>Sermon Studio</h2>

<p>Create and develop sermons using AI assistance.</p>

<div class="module-card">
<h3>Create Sermon</h3>
<button>Create From Bible Verses</button>
<button>Create From Topic</button>
<button>Import Sermon</button>
</div>
`
}

else if(page === "network"){

view.innerHTML = `
<h2>Pastor Network</h2>

<p>Connect with pastors worldwide.</p>

<div class="module-card">
<p>Search pastors</p>
<p>Join discussions</p>
<p>Share sermon ideas</p>
</div>
`
}

else if(page === "library"){

view.innerHTML = `
<h2>Sermon Library</h2>

<p>Your saved sermons will appear here.</p>
`
}

else if(page === "collaboration"){

view.innerHTML = `
<h2>Collaboration</h2>

<p>Work together with other pastors.</p>
`
}

else if(page === "profile"){

view.innerHTML = `
<h2>Profile</h2>

<p>Update your pastor profile.</p>
`
}

}


sidebarItems.forEach(item => {

item.addEventListener("click", () => {

sidebarItems.forEach(i => i.classList.remove("active"))

item.classList.add("active")

render(item.dataset.page)

})

})


/* Logout */

document.getElementById("logoutBtn").addEventListener("click", () => {

localStorage.removeItem("token")

window.location.href = "/faith/login.html"

})



/* Check JWT */

const token = localStorage.getItem("token")

if(!token){

window.location.href = "/faith/login.html"

}