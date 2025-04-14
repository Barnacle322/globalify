document.addEventListener('DOMContentLoaded', () => {
    const gallery = document.getElementById('gallery');
    if (gallery) {
        let images = gallery.querySelectorAll('img');
        const numImages = images.length;
        const baseImageWidth = 500;
        const imageWidth = baseImageWidth + 32; // Base width + padding (16px each side)
        let isAdjusting = false; // Flag to prevent overlapping scroll adjustments

        // Store original image containers
        const originalContainers = Array.from(gallery.querySelectorAll('div.relative'));

        if (numImages === 1) { // Adjusted to check for 1 image explicitly
            // Single image: apply styles and exit
            images[0].classList.add('scale-110', 'z-20', 'shadow-lg');
            gallery.children[0].classList.add('px-8');
            gallery.children[0].classList.remove('px-4');
            gallery.style.scrollSnapType = 'none'; // Disable snapping
            gallery.style.overflowX = 'hidden'; // Prevent scrolling
            return; // Stop further execution
        }

        // Multiple images: proceed with infinite scrolling
        // Clone images for infinite scrolling
        const cloneImages = () => {
            // Clone five sets at the beginning (increased for smoother buffer)
            for (let set = 0; set < 5; set++) {
                for (let i = numImages - 1; i >= 0; i--) {
                    const cloneContainer = originalContainers[i].cloneNode(true);
                    gallery.insertBefore(cloneContainer, gallery.firstChild);
                }
            }
            // Clone five sets at the end
            for (let set = 0; set < 5; set++) {
                for (let i = 0; i < numImages; i++) {
                    const cloneContainer = originalContainers[i].cloneNode(true);
                    gallery.appendChild(cloneContainer);
                }
            }
            // Update images after cloning
            images = gallery.querySelectorAll('img');
        };

        // Initial cloning
        cloneImages();

        // Initial centering
        if (numImages > 0) {
            const bufferSets = 5; // Increased buffer
            const centerImageIndex = (bufferSets * numImages) + Math.floor(numImages / 2); // Middle of original set
            const scrollPosition =
                centerImageIndex * imageWidth - (gallery.offsetWidth - imageWidth) / 2;
            gallery.scrollLeft = scrollPosition;

            // Apply initial styles to center image
            images[centerImageIndex].classList.add('scale-110', 'z-20', 'shadow-lg');
            gallery.children[centerImageIndex].classList.add('px-8');
            gallery.children[centerImageIndex].classList.remove('px-4');
        }

        // Debounce function to limit scroll event frequency
        const debounce = (func, wait) => {
            let timeout;
            return (...args) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(this, args), wait);
            };
        };

        // Scroll handler for dynamic scaling and infinite scroll
        const handleScroll = () => {
            if (isAdjusting) return; // Skip if already adjusting

            const scrollLeft = gallery.scrollLeft;
            const totalWidth = numImages * imageWidth;
            const bufferSets = 5; // Match initial buffer
            // Adjusted buffer zones to start transitions earlier
            const bufferZoneStart = (bufferSets - 0.5) * totalWidth;
            const bufferZoneEnd = (bufferSets + 0.5) * totalWidth;

            // Infinite scroll logic
            if (scrollLeft <= bufferZoneStart) {
                isAdjusting = true;
                gallery.style.scrollBehavior = 'auto'; // Disable smooth scrolling temporarily

                // Move last set to start
                for (let i = 0; i < numImages; i++) {
                    const lastChild = gallery.lastChild;
                    gallery.removeChild(lastChild);
                    gallery.insertBefore(lastChild, gallery.firstChild);
                }
                // Add a new set to the end
                for (let i = 0; i < numImages; i++) {
                    const cloneContainer = originalContainers[i].cloneNode(true);
                    gallery.appendChild(cloneContainer);
                }
                // Adjust scroll position
                const newScrollLeft = scrollLeft + totalWidth;
                gallery.scrollLeft = newScrollLeft;
                images = gallery.querySelectorAll('img');

                // Use requestAnimationFrame for smoother re-enabling
                requestAnimationFrame(() => {
                    gallery.style.scrollBehavior = 'smooth';
                    isAdjusting = false;
                });
            } else if (scrollLeft >= bufferZoneEnd) {
                isAdjusting = true;
                gallery.style.scrollBehavior = 'auto'; // Disable smooth scrolling temporarily

                // Move first set to end
                for (let i = 0; i < numImages; i++) {
                    const firstChild = gallery.firstChild;
                    gallery.removeChild(firstChild);
                    gallery.appendChild(firstChild);
                }
                // Add a new set to the start
                for (let i = numImages - 1; i >= 0; i--) {
                    const cloneContainer = originalContainers[i].cloneNode(true);
                    gallery.insertBefore(cloneContainer, gallery.firstChild);
                }
                // Adjust scroll position
                const newScrollLeft = scrollLeft - totalWidth;
                gallery.scrollLeft = newScrollLeft;
                images = gallery.querySelectorAll('img');

                // Use requestAnimationFrame for smoother re-enabling
                requestAnimationFrame(() => {
                    gallery.style.scrollBehavior = 'smooth';
                    isAdjusting = false;
                });
            }

            // Update styles for all images
            const galleryRect = gallery.getBoundingClientRect();
            const viewportCenter = galleryRect.left + galleryRect.width / 2;
            images = gallery.querySelectorAll('img'); // Refresh images
            images.forEach((img, index) => {
                const imgRect = img.getBoundingClientRect();
                const imgCenter = imgRect.left + imgRect.width / 2;
                const distance = Math.abs(viewportCenter - imgCenter);

                if (distance < 250) {
                    img.classList.add('scale-110', 'z-20', 'shadow-lg');
                    img.classList.remove('shadow-md');
                    gallery.children[index].classList.add('px-8');
                    gallery.children[index].classList.remove('px-4');
                } else {
                    img.classList.remove('scale-110', 'z-20', 'shadow-lg');
                    img.classList.add('shadow-md');
                    gallery.children[index].classList.remove('px-8');
                    gallery.children[index].classList.add('px-4');
                }
            });
        };

        // Attach debounced scroll handler with slightly longer delay
        const debouncedHandleScroll = debounce(handleScroll, 100); // Increased to 100ms
        gallery.addEventListener('scroll', debouncedHandleScroll);
    }
});