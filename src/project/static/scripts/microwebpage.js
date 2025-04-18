document.addEventListener('DOMContentLoaded', () => {
    const gallery = document.getElementById('gallery');
    if (!gallery) return;

    // 1. Filter out images with None/empty src
    const validImages = Array.from(gallery.querySelectorAll('img')).filter(img => {
        const src = img.dataset.originalSrc || img.src;
        return src && src !== 'None' && src.trim() !== '';
    });

    // 2. Hide gallery if no valid images
    if (validImages.length === 0) {
        gallery.style.display = 'none';
        return;
    }

    const numImages = validImages.length;

    // 3. Store original image data (only valid images)
    const originalImageData = validImages.map(img => ({
        src: img.dataset.originalSrc || img.src,
        alt: img.alt || 'Company photo',
        container: img.closest('div.relative')
    }));

    const baseImageWidth = 500;
    const imageWidth = baseImageWidth + 32; // 500px + 32px (padding)
    let isAdjusting = false;

    // Initialize the gallery
    initializeGallery();

    function initializeGallery() {
        // Clean up any invalid elements that might exist
        Array.from(gallery.querySelectorAll('div.relative')).forEach(container => {
            const img = container.querySelector('img');
            if (!img || !img.src || img.src === 'None') {
                container.remove();
            }
        });

        // Special case for single image
        if (numImages === 1) {
            validImages[0].classList.add('scale-110', 'z-20', 'shadow-lg');
            gallery.children[0].classList.add('px-8');
            gallery.children[0].classList.remove('px-4');
            gallery.style.scrollSnapType = 'none';
            gallery.style.overflowX = 'hidden';
            return;
        }

        // Clone images for infinite scroll effect
        cloneImages();

        // Center the gallery on load
        centerGallery();

        // Add scroll event listener with debounce
        gallery.addEventListener('scroll', debounce(handleScroll, 100));
    }

    function cloneImages() {
        // Clone images in both directions (left and right)
        [1, -1].forEach(direction => {
            for (let i = 0; i < numImages; i++) {
                const index = direction === 1 ? i : numImages - 1 - i;
                const cloneContainer = originalImageData[index].container.cloneNode(true);
                const cloneImg = cloneContainer.querySelector('img');

                if (cloneImg) {
                    cloneImg.src = originalImageData[index].src;
                    cloneImg.alt = originalImageData[index].alt;
                }

                if (direction === 1) {
                    gallery.appendChild(cloneContainer);
                } else {
                    gallery.insertBefore(cloneContainer, gallery.firstChild);
                }
            }
        });
    }

    function centerGallery() {
        const bufferSets = 1;
        const centerImageIndex = (bufferSets * numImages) + Math.floor(numImages / 2);
        const scrollPosition = centerImageIndex * imageWidth - (gallery.offsetWidth - imageWidth) / 2;

        gallery.scrollLeft = scrollPosition;

        // Highlight center image
        const centerImg = gallery.querySelectorAll('img')[centerImageIndex];
        if (centerImg) {
            centerImg.classList.add('scale-110', 'z-20', 'shadow-lg');
            const centerContainer = centerImg.closest('div.relative');
            if (centerContainer) {
                centerContainer.classList.add('px-8');
                centerContainer.classList.remove('px-4');
            }
        }
    }

    function debounce(func, wait) {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    function handleScroll() {
        if (isAdjusting) return;

        const scrollLeft = gallery.scrollLeft;
        const totalWidth = numImages * imageWidth;
        const bufferSets = 1;
        const bufferZoneStart = (bufferSets - 0.5) * totalWidth;
        const bufferZoneEnd = (bufferSets + 0.5) * totalWidth;

        // Check if we need to adjust the gallery position
        if (scrollLeft <= bufferZoneStart) {
            adjustGallery('left', scrollLeft, totalWidth);
        } else if (scrollLeft >= bufferZoneEnd) {
            adjustGallery('right', scrollLeft, totalWidth);
        }

        // Update image styles based on position
        updateImageStyles();
    }

    function adjustGallery(direction, scrollLeft, totalWidth) {
        isAdjusting = true;
        gallery.style.scrollBehavior = 'auto';

        if (direction === 'left') {
            // Move images from end to beginning
            for (let i = 0; i < numImages; i++) {
                const lastChild = gallery.lastChild;
                gallery.removeChild(lastChild);
                gallery.insertBefore(lastChild, gallery.firstChild);
            }

            // Add new clones at the end
            for (let i = 0; i < numImages; i++) {
                const cloneContainer = originalImageData[i].container.cloneNode(true);
                const cloneImg = cloneContainer.querySelector('img');
                if (cloneImg) {
                    cloneImg.src = originalImageData[i].src;
                    cloneImg.alt = originalImageData[i].alt;
                }
                gallery.appendChild(cloneContainer);
            }

            gallery.scrollLeft = scrollLeft + totalWidth;
        }
        else if (direction === 'right') {
            // Move images from beginning to end
            for (let i = 0; i < numImages; i++) {
                const firstChild = gallery.firstChild;
                gallery.removeChild(firstChild);
                gallery.appendChild(firstChild);
            }

            // Add new clones at the beginning
            for (let i = numImages - 1; i >= 0; i--) {
                const cloneContainer = originalImageData[i].container.cloneNode(true);
                const cloneImg = cloneContainer.querySelector('img');
                if (cloneImg) {
                    cloneImg.src = originalImageData[i].src;
                    cloneImg.alt = originalImageData[i].alt;
                }
                gallery.insertBefore(cloneContainer, gallery.firstChild);
            }

            gallery.scrollLeft = scrollLeft - totalWidth;
        }

        // Restore smooth scrolling after adjustment
        requestAnimationFrame(() => {
            gallery.style.scrollBehavior = 'smooth';
            isAdjusting = false;
        });
    }

    function updateImageStyles() {
        const galleryRect = gallery.getBoundingClientRect();
        const viewportCenter = galleryRect.left + galleryRect.width / 2;
        const currentImages = gallery.querySelectorAll('img');

        currentImages.forEach((img, index) => {
            const imgRect = img.getBoundingClientRect();
            const imgCenter = imgRect.left + imgRect.width / 2;
            const distance = Math.abs(viewportCenter - imgCenter);

            const container = gallery.children[index];

            if (distance < 250) {
                // Highlight image near center
                img.classList.add('scale-110', 'z-20', 'shadow-lg');
                img.classList.remove('shadow-md');
                container.classList.add('px-8');
                container.classList.remove('px-4');
            } else {
                // Reset other images
                img.classList.remove('scale-110', 'z-20', 'shadow-lg');
                img.classList.add('shadow-md');
                container.classList.remove('px-8');
                container.classList.add('px-4');
            }
        });
    }
});