window.addEventListener("DOMContentLoaded", () => {
  const links = [...document.querySelectorAll('.navbar .nav-link')];
  const here = window.location.pathname.split('/').pop() || 'index.html';

  links.forEach((link) => {
    const href = link.getAttribute('href') || '';
    const target = href.split('/').pop();
    if (target === here || (here === 'index.html' && (target === '' || target === 'index.qmd'))) {
      link.classList.add('active');
    }
  });

  const sectionIds = ['focus', 'featured-work', 'latest'];
  const observer = new IntersectionObserver(
    (entries) => {
      const active = entries
        .filter((e) => e.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!active) return;
      links.forEach((l) => {
        if (l.getAttribute('href') === `#${active.target.id}`) l.classList.add('active');
      });
    },
    { threshold: [0.3, 0.5, 0.8] }
  );

  sectionIds.forEach((id) => {
    const el = document.getElementById(id);
    if (el) observer.observe(el);
  });
});
