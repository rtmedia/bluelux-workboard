(() => {
  const button = document.querySelector('#installApp');
  const standalone = matchMedia('(display-mode: standalone)');
  let installPrompt = null;
  function sync() { button.hidden = standalone.matches; }
  sync(); standalone.addEventListener('change', sync);
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault(); installPrompt = event;
  });
  window.addEventListener('appinstalled', () => { installPrompt = null; button.hidden = true; });
  button.addEventListener('click', async () => {
    if (installPrompt) {
      const prompt = installPrompt; installPrompt = null;
      await prompt.prompt(); await prompt.userChoice; return;
    }
    openDetail('DESKTOP APP', 'Install Workboard', '<p>In Chrome, use the install icon in the address bar, or open the Chrome menu → Cast, save, and share → Install page as app.</p><p>In Safari, choose File → Add to Dock.</p><p>Open Workboard from its app icon and keep its window open beside your work. The local server must also be running on this Mac.</p>');
  });
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js', {updateViaCache:'none'}).catch(() => {
      button.title = 'Installation is available; the recovery screen could not be enabled. Reload to retry.';
    });
  }
})();
