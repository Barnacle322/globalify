class Card {
    constructor(investor) {
        this.investor = investor;
    }

    render() {
        const card = document.createElement("div");
        card.innerHTML = `
        <article class="flex flex-col rounded-lg p-6 shadow-[rgba(13,_38,_76,_0.19)_0px_9px_20px]">
            <div class="flex flex-row items-center gap-2">
                <a href="/login?type=1&msg=Log in to see more!" class="text-xl font-bold leading-none">
                    ${this.investor.name}
                    <span class="text-base font-normal text-gray-500">@ ${this.investor.firm_name}</span>
                </a>
            </div>

            <div class="mt-2 flex flex-col gap-2">
                <p class="text-gray-500">${this.investor.location}</p>
                <p class="text-sm text-gray-500">${this.investor.industries.join(", ")}</p>
                <p class="flex flex-wrap gap-1">
                    ${this.investor.rounds
                        .map(
                            (round) =>
                                `<a class="text-nowrap rounded-lg bg-blue-600 px-2 py-1 text-sm text-white">${round}</a>`,
                        )
                        .join("")}
                </p>
            </div>
        </article>
        `;
        return card;
    }
}

class Button {
    constructor() {}
    render() {
        const button = document.createElement("a");
        button.classList.add(
            "inline-flex",
            "items-center",
            "justify-center",
            "rounded-xl",
            "bg-blue-600",
            "p-4",
            "mt-10",
            "font-semibold",
            "text-white",
        );
        button.href = "/login?type=1&msg=Log in to see more!";
        button.innerHTML = "See More Results";
        return button;
    }
}

function getSearch() {
    let searchInput = document.getElementById("search").value;
    fetch(`/demo_search?search=${searchInput}`)
        .then((response) => response.json())
        .then((data) => {
            document.getElementById("results").innerHTML = "";
            // Remove the "See More Results" button if it exists
            if (document.getElementById("results").parentElement.lastChild.tagName === "A") {
                document
                    .getElementById("results")
                    .parentElement.removeChild(document.getElementById("results").parentElement.lastChild);
            }
            console.log(data);
            data.forEach((investor) => {
                const card = new Card(investor);
                document.getElementById("results").appendChild(card.render());
            });
            document.getElementById("results").parentElement.appendChild(new Button().render());
        });
}
