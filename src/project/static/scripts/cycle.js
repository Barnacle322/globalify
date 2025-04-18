document.addEventListener('DOMContentLoaded', () => {
  const gallery = document.getElementById('gallery');
  if (gallery) {
    const imageContainers = gallery.querySelectorAll('div.relative');
    const images = gallery.querySelectorAll('img');
    const numImages = images.length;
    const imageWidth = 500 + 16; // 500px + 16px (mx-2)

    // Initial centering and scaling
    if (numImages > 0) {
      const centerImageIndex = Math.floor(numImages / 2);
      const scrollPosition = centerImageIndex * imageWidth - (gallery.offsetWidth - imageWidth) / 2;
      gallery.scrollLeft = scrollPosition;
      images[centerImageIndex].classList.add('scale-150', 'z-20', 'shadow-lg');
      imageContainers[centerImageIndex].classList.add('min-w-[750px]', 'mx-4');
    }

    // Dynamic scaling on scroll
    gallery.addEventListener('scroll', () => {
      const galleryRect = gallery.getBoundingClientRect();
      const viewportCenter = galleryRect.left + galleryRect.width / 2;

      images.forEach((img, index) => {
        const imgRect = img.getBoundingClientRect();
        const imgCenter = imgRect.left + imgRect.width / 2;
        const distance = Math.abs(viewportCenter - imgCenter);

        // Scale and adjust container if within 200px of center
        if (distance < 200) {
          img.classList.add('scale-150', 'z-20', 'shadow-lg');
          img.classList.remove('shadow-md');
          imageContainers[index].classList.add('min-w-[750px]', 'mx-4');
          imageContainers[index].classList.remove('min-w-[500px]', 'mx-2');
        } else {
          img.classList.remove('scale-150', 'z-20', 'shadow-lg');
          img.classList.add('shadow-md');
          imageContainers[index].classList.remove('min-w-[750px]', 'mx-4');
          imageContainers[index].classList.add('min-w-[500px]', 'mx-2');
        }
      });
    });
  }
});