function search() {
    var searchQuery = document.getElementById("search").value;

    if (searchQuery == "") {
        var newUrl = window.location.href.split("?")[0];
    } else {
        var newUrl = window.location.href.split("?")[0] + "?q=" + encodeURIComponent(searchQuery);
    }
    window.location.href = newUrl;
}

var searchInput = document.getElementById("search");
searchInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        search();
    }
});
