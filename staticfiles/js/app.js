
// Auto-dismiss alerts after a few seconds
document.addEventListener('DOMContentLoaded', function(){
  const alerts = document.querySelectorAll('.alert[data-auto-dismiss]');
  alerts.forEach(el => setTimeout(() => {
    el.classList.add('fade');
    el.addEventListener('transitionend', () => el.remove());
    el.style.opacity = 0;
  }, Number(el.dataset.autoDismiss) || 4000));
});
document.addEventListener('click', function (e) {
  const tr = e.target.closest('tr[data-href]');
  if (tr) window.location.href = tr.dataset.href;
});
